import base64
import json
import os
import logging
from contextlib import contextmanager, asynccontextmanager
from typing import List, Tuple, Dict, Optional
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from google.cloud.sql.connector import Connector, IPTypes
from google.cloud import resourcemanager_v3
from google.cloud import secretmanager_v1
from google.iam.v1 import iam_policy_pb2
from google.api_core.exceptions import NotFound, PermissionDenied
import pg8000

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO')
numeric_level = getattr(logging, log_level.upper(), logging.INFO)
logging.basicConfig(
    level=numeric_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
SECRET_NAME_SUFFIX = os.environ.get('SECRET_NAME_SUFFIX', 'postgres-password')
DB_ADMIN_USER = os.environ.get('DB_POSTGRES_USER', 'postgres')

logger.info(f"Secret name suffix: {SECRET_NAME_SUFFIX}")


def access_regional_secret(project_id: str, instance_name: str, region: str, version: str = "latest") -> str:
    """
    Retrieve a secret from Secret Manager (global or regional)

    Args:
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        region: Region of the secret
        version: Secret version (default: "latest")

    Returns:
        The decoded secret value

    Raises:
        ValueError: If the secret cannot be retrieved
    """
    try:
        # Regional secret
        secret_id = f"{instance_name}-{SECRET_NAME_SUFFIX}"

        # Endpoint to call the regional secret manager server
        api_endpoint = f"secretmanager.{region}.rep.googleapis.com"

        # Create the Secret Manager client
        client = secretmanager_v1.SecretManagerServiceClient(
            client_options={"api_endpoint": api_endpoint},
        )

        # Build the resource name of the secret version
        name = f"projects/{project_id}/locations/{region}/secrets/{secret_id}/versions/{version}"

        logger.info(f"Retrieving secret: {name}")
        # Retrieve the secret
        response = client.access_secret_version(request={"name": name})
        # Decode the secret
        secret_value = response.payload.data.decode("UTF-8")
        logger.info(f"Successfully retrieved secret: {secret_id}")

        return secret_value

    except NotFound:
        error_message = (
            f"Error: Secret '{secret_id}' or its version '{version}' not found "
            f"in region '{region}' of project '{project_id}'.\n"
        )
        logger.error(error_message)
        raise ValueError(error_message) from NotFound

    except PermissionDenied:
        error_message = (
            f"Error: Permission denied when accessing secret '{secret_id}'.\n"
            f"Please verify that the account executing this code has the IAM role "
            "'roles/secretmanager.secretAccessor'."
        )
        logger.error(error_message)
        raise ValueError(error_message) from PermissionDenied

    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        logger.error(error_message)
        raise ValueError(error_message) from e


# Pydantic models for request validation
class IAMUser(BaseModel):
    name: str = Field(..., description="IAM user email (e.g., user@project.iam.gserviceaccount.com)")
    permission_level: str = Field(default="readonly", description="Permission level: readonly, readwrite, or admin")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "my-service@project.iam.gserviceaccount.com",
                "permission_level": "readonly"
            }
        }


class PubSubMessage(BaseModel):
    data: str = Field(..., description="Base64-encoded JSON data")
    attributes: Optional[Dict[str, str]] = Field(default={}, description="Message attributes")
    messageId: Optional[str] = Field(default=None, description="Pub/Sub message ID")
    publishTime: Optional[str] = Field(default=None, description="Publish timestamp")


class PubSubRequest(BaseModel):
    message: PubSubMessage


class IAMUserRequest(BaseModel):
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    region: str = Field(..., description="GCP region")
    schema_name: Optional[str] = Field(default=None, description="Schema name (defaults to {database_name}_schema)")
    iam_users: List[IAMUser] = Field(default=[], description="List of IAM users to manage")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "region": "europe-west1",
                "schema_name": "my_schema",
                "iam_users": [
                    {
                        "name": "service-account@project.iam.gserviceaccount.com",
                        "permission_level": "readonly"
                    }
                ]
            }
        }


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ErrorResponse(BaseModel):
    error: str
    details: Optional[Dict] = None


class PubSubMessageParser:
    """Parser for Pub/Sub messages with schema validation"""

    @staticmethod
    def parse_pubsub_message(request_json: dict) -> dict:
        """
        Parse a Pub/Sub message and extract data

        Args:
            request_json: The JSON payload from the request

        Returns:
            Parsed message data with metadata

        Raises:
            ValueError: If the message format is invalid

        Expected format:
        {
            "message": {
                "data": "base64_encoded_json",
                "attributes": {},
                "messageId": "...",
                "publishTime": "..."
            }
        }
        """
        if not request_json:
            raise ValueError("Empty request payload")

        # Verify Pub/Sub format
        if 'message' not in request_json:
            raise ValueError("Invalid Pub/Sub format: missing 'message' field")

        pubsub_message = request_json['message']

        # Extract and decode data
        if 'data' not in pubsub_message:
            raise ValueError("Invalid Pub/Sub format: missing 'data' field")

        try:
            # Decode base64
            encoded_data = pubsub_message['data']
            decoded_data = base64.b64decode(encoded_data).decode('utf-8')

            # Parse JSON
            message_data = json.loads(decoded_data)

            # Add Pub/Sub metadata
            message_data['_pubsub_metadata'] = {
                'messageId': pubsub_message.get('messageId'),
                'publishTime': pubsub_message.get('publishTime'),
                'attributes': pubsub_message.get('attributes', {})
            }

            return message_data

        except (base64.binascii.Error, UnicodeDecodeError) as e:
            raise ValueError(f"Failed to decode base64 data: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON data: {str(e)}")

    @staticmethod
    def validate_message_schema(message_data: dict) -> dict:
        """
        Validate message schema and return cleaned data

        Args:
            message_data: Message data to validate

        Returns:
            Validated and cleaned data

        Raises:
            ValueError: If required fields are missing or invalid

        Expected format:
        {
            "project_id": "my-project",
            "instance_name": "my-instance",
            "database_name": "my-db",
            "region": "europe-west1",
            "schema_name": "my-schema",  # optional, default: {database_name}_schema
            "iam_users": [
                {
                    "name": "user@project.iam.gserviceaccount.com",
                    "permission_level": "readonly|readwrite|admin"  # optional, default: readonly
                }
            ]
        }
        """
        required_fields = ['project_id', 'instance_name', 'database_name', 'region', 'iam_users']
        missing_fields = [field for field in required_fields if not message_data.get(field)]

        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        # Clean and validate data
        cleaned_data = {
            'project_id': str(message_data['project_id']).strip(),
            'instance_name': str(message_data['instance_name']).strip(),
            'database_name': str(message_data['database_name']).strip(),
            'region': str(message_data['region']).strip(),
            'schema_name': str(message_data.get('schema_name', f"{message_data['database_name']}_schema")).strip(),
            'iam_users': message_data.get('iam_users', [])
        }

        # Validate schema name
        if not cleaned_data['schema_name']:
            raise ValueError("Schema name cannot be empty")

        # Validate IAM users
        if not isinstance(cleaned_data['iam_users'], list):
            raise ValueError("iam_users must be a list")

        validated_users = []
        for i, user in enumerate(cleaned_data['iam_users']):
            if not isinstance(user, dict):
                logger.warning(f"Skipping invalid user at index {i}: not a dict")
                continue

            user_name = user.get('name')
            if not user_name or not isinstance(user_name, str):
                logger.warning(f"Skipping user at index {i}: missing or invalid name")
                continue

            permission_level = user.get('permission_level', 'readonly')
            if permission_level not in ['readonly', 'readwrite', 'admin']:
                logger.warning(f"Invalid permission_level '{permission_level}' for user {user_name}, using 'readonly'")
                permission_level = 'readonly'

            validated_users.append({
                'name': user_name.strip(),
                'permission_level': permission_level
            })

        cleaned_data['iam_users'] = validated_users

        # Preserve Pub/Sub metadata
        if '_pubsub_metadata' in message_data:
            cleaned_data['_pubsub_metadata'] = message_data['_pubsub_metadata']

        return cleaned_data


class CloudSQLUserManager:
    """Manager for IAM user permissions in Cloud SQL"""

    def __init__(self):
        self.connector = Connector()

    def normalize_service_account_name(self, service_account_email: str) -> str:
        """
        Convert a service account email to PostgreSQL role name

        Args:
            service_account_email: Service account email

        Returns:
            Normalized PostgreSQL role name

        Transformation:
        my-service@project.iam.gserviceaccount.com -> my-service@project
        """
        if service_account_email.endswith('.gserviceaccount.com'):
            return service_account_email.replace('.gserviceaccount.com', '')
        return service_account_email

    @contextmanager
    def get_connection(self, project_id: str, region: str, instance_name: str, database_name: str):
        """
        Context manager for Cloud SQL connections with robust error handling

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name

        Yields:
            Database connection

        Raises:
            Exception: If connection fails
        """
        instance_connection_name = f"{project_id}:{region}:{instance_name}"
        conn = None

        try:
            logger.info(f"Connecting to {instance_connection_name}/{database_name}")

            # Retrieve admin password from Secret Manager
            admin_password = access_regional_secret(project_id, instance_name, region)

            conn = self.connector.connect(
                instance_connection_name,
                "pg8000",
                user=DB_ADMIN_USER,
                password=admin_password,
                db=database_name,
                ip_type=IPTypes.PRIVATE
            )
            conn.autocommit = False
            yield conn

        except Exception as e:
            logger.error(f"Connection failed to {instance_connection_name}: {str(e)}")
            if conn:
                try:
                    conn.rollback()
                except Exception as rollback_err:
                    logger.warning(f"Rollback failed: {rollback_err}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as close_err:
                    logger.warning(f"Connection close failed: {close_err}")

    def validate_iam_permissions(self, project_id: str, iam_users: List[Dict]) -> Tuple[bool, List[str]]:
        """
        Validate that users have required IAM permissions

        Args:
            project_id: GCP project ID
            iam_users: List of IAM users to validate

        Returns:
            Tuple (all_valid, invalid_users_list)
        """
        if not iam_users:
            return True, []

        client = resourcemanager_v3.ProjectsClient()
        required_role = "roles/cloudsql.instanceUser"

        try:
            request = iam_policy_pb2.GetIamPolicyRequest(resource=f"projects/{project_id}")
            policy = client.get_iam_policy(request=request)

            # Extract all members with the required role
            members_with_role = set()
            for binding in policy.bindings:
                if binding.role == required_role:
                    for member in binding.members:
                        if member.startswith("user:"):
                            members_with_role.add(member[5:])  # Remove "user:"
                        elif member.startswith("serviceAccount:"):
                            members_with_role.add(member[15:])  # Remove "serviceAccount:"

            logger.info(f"Found {len(members_with_role)} members with role {required_role} in project {project_id}")

            # Check each user
            all_usernames = {user.get('name') for user in iam_users if user.get('name')}
            invalid_users = list(all_usernames - members_with_role)

            if invalid_users:
                logger.warning(f"Users missing required IAM role '{required_role}': {invalid_users}")

            return not invalid_users, invalid_users

        except Exception as e:
            logger.error(f"Failed to validate IAM permissions for project {project_id}: {e}")
            # In case of error, consider all users as invalid (security)
            all_usernames = [user.get('name') for user in iam_users if user.get('name')]
            return False, all_usernames

    def execute_sql_safely(self, cursor, sql: str, params: Tuple = None) -> bool:
        """
        Execute SQL query with error handling

        Args:
            cursor: Database cursor
            sql: SQL query to execute
            params: Query parameters (optional)

        Returns:
            True if execution succeeds, False otherwise
        """
        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return True
        except Exception as e:
            logger.error(f"SQL execution failed: {sql[:100]}... Error: {str(e)}")
            return False

    def schema_exists(self, cursor, schema_name: str) -> bool:
        """
        Check if a schema exists in the database

        Args:
            cursor: Database cursor
            schema_name: Schema name to check

        Returns:
            True if schema exists, False otherwise
        """
        try:
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.schemata 
                    WHERE schema_name = %s
                )
            """, (schema_name,))

            result = cursor.fetchone()
            exists = result[0] if result else False

            logger.debug(f"Schema '{schema_name}' exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Failed to check schema existence for '{schema_name}': {e}")
            return False

    def create_schema_if_not_exists(self, cursor, schema_name: str) -> bool:
        """
        Create schema if it doesn't exist

        Args:
            cursor: Database cursor
            schema_name: Schema name to create

        Returns:
            True if schema exists or was created successfully, False otherwise
        """
        try:
            if self.schema_exists(cursor, schema_name):
                logger.info(f"Schema '{schema_name}' already exists")
                return True

            # Create schema with quotes to avoid naming issues
            create_sql = f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'
            if self.execute_sql_safely(cursor, create_sql):
                logger.info(f"Successfully created schema '{schema_name}'")
                return True
            else:
                logger.error(f"Failed to create schema '{schema_name}'")
                return False

        except Exception as e:
            logger.error(f"Error creating schema '{schema_name}': {e}")
            return False

    def get_existing_iam_users(self, cursor) -> List[str]:
        """
        Retrieve list of existing IAM users in the database

        Args:
            cursor: Database cursor

        Returns:
            List of existing IAM usernames

        Note: IAM Database Authentication users appear as normal PostgreSQL roles
        once created via Terraform/gcloud/Cloud SQL API.
        This code only reads their presence, never creates/deletes them.

        Service accounts appear without the .gserviceaccount.com suffix
        """
        try:
            # Build list of roles to exclude (system + connection service account)
            excluded_roles = [
                'postgres', 'cloudsqlsuperuser', 'cloudsqladmin', 'cloudsqlreplica'
            ]

            # Create placeholders for the query
            placeholders = ','.join(['%s'] * len(excluded_roles))

            cursor.execute(f"""
                SELECT rolname FROM pg_roles 
                WHERE rolname NOT IN ({placeholders})
                AND rolname NOT LIKE 'cloudsql%%'
                AND rolname NOT LIKE 'pg_%%'
                AND rolname NOT LIKE 'information_schema%%'
                AND NOT rolsuper  -- Exclude superusers
                AND rolcanlogin = true  -- Include only login roles
            """, excluded_roles)

            existing_users = [row[0] for row in cursor.fetchall()]
            logger.info(f"Found {len(existing_users)} existing IAM users")
            logger.debug(f"IAM users found: {existing_users}")
            return existing_users

        except Exception as e:
            logger.error(f"Failed to get existing IAM users: {e}")
            return []

    def revoke_all_permissions(self, cursor, username: str, database_name: str, schema_name: str) -> bool:
        """
        Revoke all permissions from an IAM user
        """
        try:
            logger.debug(f"Revoking all permissions for user {username} on schema {schema_name}")

            # Check if schema exists before operations
            if not self.schema_exists(cursor, schema_name):
                logger.warning(f"Schema '{schema_name}' does not exist, skipping revocation for user {username}")
                return True

            # Transfer ownership if necessary
            cursor.execute("""
                SELECT pg_catalog.pg_get_userbyid(d.datdba) as owner 
                FROM pg_catalog.pg_database d 
                WHERE d.datname = %s
            """, (database_name,))

            current_owner = cursor.fetchone()
            if current_owner and current_owner[0] == username:
                logger.info(
                    f"User {username} is owner of database {database_name}, transferring ownership back to postgres")
                if not self.execute_sql_safely(cursor, f'ALTER DATABASE "{database_name}" OWNER TO postgres'):
                    logger.warning(f"Failed to transfer database ownership from {username}")

            cursor.execute("""
                SELECT pg_catalog.pg_get_userbyid(n.nspowner) as owner 
                FROM pg_catalog.pg_namespace n 
                WHERE n.nspname = %s
            """, (schema_name,))

            schema_owner = cursor.fetchone()
            if schema_owner and schema_owner[0] == username:
                logger.info(
                    f"User {username} is owner of schema {schema_name}, transferring ownership back to postgres")
                if not self.execute_sql_safely(cursor, f'ALTER SCHEMA "{schema_name}" OWNER TO postgres'):
                    logger.warning(f"Failed to transfer schema ownership from {username}")

            # Revoke existing permissions
            revoke_commands = [
                f'REVOKE ALL PRIVILEGES ON DATABASE "{database_name}" FROM "{username}"',
                f'REVOKE ALL PRIVILEGES ON SCHEMA "{schema_name}" FROM "{username}"',
                f'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{schema_name}" FROM "{username}"',
                f'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA "{schema_name}" FROM "{username}"',
                f'REVOKE ALL PRIVILEGES ON ALL ROUTINES IN SCHEMA "{schema_name}" FROM "{username}"'
            ]

            success = True
            for cmd in revoke_commands:
                if not self.execute_sql_safely(cursor, cmd):
                    success = False

            # Clean up default privileges
            default_privilege_commands = [
                f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" REVOKE ALL PRIVILEGES ON TABLES FROM "{username}"',
                f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" REVOKE ALL PRIVILEGES ON SEQUENCES FROM "{username}"',
                f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" REVOKE ALL PRIVILEGES ON ROUTINES FROM "{username}"'
            ]

            for cmd in default_privilege_commands:
                if not self.execute_sql_safely(cursor, cmd):
                    success = False

            if success:
                logger.info(f"Successfully revoked all permissions for user {username}")
            else:
                logger.warning(f"Some permission revocations failed for user {username}")

            return success

        except Exception as e:
            logger.error(f"Error revoking permissions for user {username}: {e}")
            return False

    def grant_permissions(self, cursor, username: str, permission_level: str, database_name: str,
                          schema_name: str) -> bool:
        """
        Grant permissions according to specified level to an existing IAM user
        """
        try:
            logger.debug(f"Granting {permission_level} permissions to user {username} on schema {schema_name}")

            # Check if schema exists before granting permissions
            if not self.schema_exists(cursor, schema_name):
                logger.error(f"Cannot grant permissions: schema '{schema_name}' does not exist")
                return False

            # Base permissions
            base_commands = [
                f'GRANT CONNECT ON DATABASE "{database_name}" TO "{username}"',
                f'GRANT USAGE ON SCHEMA "{schema_name}" TO "{username}"'
            ]

            # Permissions based on level
            if permission_level == 'admin':
                # For admin, make owner of database and schema
                permission_commands = [
                    f'GRANT ALL PRIVILEGES ON DATABASE "{database_name}" TO "{username}"',
                    f'GRANT ALL PRIVILEGES ON SCHEMA "{schema_name}" TO "{username}"',
                    f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{schema_name}" TO "{username}"',
                    f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA "{schema_name}" TO "{username}"',
                    f'GRANT EXECUTE ON ALL ROUTINES IN SCHEMA "{schema_name}" TO "{username}"'
                ]
                default_privilege_commands = [
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT ALL PRIVILEGES ON TABLES TO "{username}"',
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT ALL PRIVILEGES ON SEQUENCES TO "{username}"',
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT EXECUTE ON ROUTINES TO "{username}"'
                ]

            elif permission_level == 'readwrite':
                permission_commands = base_commands + [
                    f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "{schema_name}" TO "{username}"',
                    f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA "{schema_name}" TO "{username}"',
                    f'GRANT EXECUTE ON ALL ROUTINES IN SCHEMA "{schema_name}" TO "{username}"'
                ]
                default_privilege_commands = [
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{username}"',
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT USAGE, SELECT ON SEQUENCES TO "{username}"',
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT EXECUTE ON ROUTINES TO "{username}"'
                ]

            else:  # readonly
                permission_commands = base_commands + [
                    f'GRANT SELECT ON ALL TABLES IN SCHEMA "{schema_name}" TO "{username}"',
                    f'GRANT SELECT ON ALL SEQUENCES IN SCHEMA "{schema_name}" TO "{username}"',
                    f'GRANT EXECUTE ON ALL ROUTINES IN SCHEMA "{schema_name}" TO "{username}"'
                ]
                default_privilege_commands = [
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT SELECT ON TABLES TO "{username}"',
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT SELECT ON SEQUENCES TO "{username}"',
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT EXECUTE ON ROUTINES TO "{username}"'
                ]

            # Apply current permissions
            success = True
            for cmd in permission_commands:
                if not self.execute_sql_safely(cursor, cmd):
                    success = False

            # Apply default privileges
            for cmd in default_privilege_commands:
                if not self.execute_sql_safely(cursor, cmd):
                    success = False

            if success:
                logger.info(
                    f"Successfully granted {permission_level} permissions to user {username} on schema {schema_name}")
            else:
                logger.error(f"Failed to grant some permissions to user {username}")

            return success

        except Exception as e:
            logger.error(f"Error granting permissions to user {username}: {e}")
            return False

    def update_user_permissions(self, cursor, username: str, permission_level: str, database_name: str,
                                schema_name: str) -> bool:
        """
        Update permissions for an existing IAM user

        Args:
            cursor: Database cursor
            username: PostgreSQL username
            permission_level: Desired permission level
            database_name: Database name
            schema_name: Schema name

        Returns:
            True if update succeeds, False otherwise

        IMPORTANT: This method assumes the IAM user already exists in the database
        (created via Terraform/gcloud/Cloud SQL API). It only manages permissions.

        The username must be in PostgreSQL format (without .gserviceaccount.com)
        """
        try:
            # Normalize username (in case it contains .gserviceaccount.com)
            normalized_username = self.normalize_service_account_name(username)

            # Check if user exists
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (normalized_username,))
            if cursor.fetchone() is None:
                logger.error(
                    f"IAM user {normalized_username} does not exist in database. Must be created via Terraform/gcloud first.")
                return False

            logger.debug(f"Updating permissions for existing IAM user {normalized_username}")

            # Check/create schema before any operation
            if not self.create_schema_if_not_exists(cursor, schema_name):
                logger.error(f"Failed to create or verify schema '{schema_name}'")
                return False

            # 1. Clean existing permissions
            if not self.revoke_all_permissions(cursor, normalized_username, database_name, schema_name):
                logger.warning(f"Failed to fully revoke existing permissions for {normalized_username}, continuing...")

            # 2. Grant new permissions
            return self.grant_permissions(cursor, normalized_username, permission_level, database_name, schema_name)

        except Exception as e:
            logger.error(f"Error updating permissions for user {username}: {e}")
            return False

    def process_users(self, message_data: dict) -> dict:
        """
        Process IAM user permissions with complete schema verification

        Args:
            message_data: Validated message data

        Returns:
            Dictionary with processing result

        IMPORTANT:
        - IAM users must already exist (created via Terraform/gcloud)
        - This function only manages SQL permissions (GRANT/REVOKE)
        - It does not create or delete IAM users
        - Schema will be created automatically if it doesn't exist
        """

        project_id = message_data['project_id']
        region = message_data['region']
        instance_name = message_data['instance_name']
        database_name = message_data['database_name']
        schema_name = message_data['schema_name']
        iam_users = message_data['iam_users']

        try:
            with self.get_connection(project_id, region, instance_name, database_name) as conn:
                cursor = conn.cursor()

                try:
                    # Check/create schema first
                    logger.info(f"Verifying schema '{schema_name}' existence")
                    if not self.create_schema_if_not_exists(cursor, schema_name):
                        return {
                            "success": False,
                            "project_id": project_id,
                            "instance_name": instance_name,
                            "database_name": database_name,
                            "schema_name": schema_name,
                            "error": f"Failed to create or verify schema '{schema_name}'",
                            "message_id": message_data.get('_pubsub_metadata', {}).get('messageId')
                        }

                    # Commit after schema creation
                    conn.commit()

                    # Get existing IAM users in the database
                    existing_iam_users = set(self.get_existing_iam_users(cursor))

                    # Normalize requested usernames (remove .gserviceaccount.com)
                    normalized_requested_users = {
                        self.normalize_service_account_name(user['name']): user['name']
                        for user in iam_users
                    }
                    requested_users_normalized = set(normalized_requested_users.keys())

                    # Requested users that don't exist in the database
                    missing_users = requested_users_normalized - existing_iam_users
                    if missing_users:
                        # Convert to original emails for logging
                        missing_emails = [normalized_requested_users[norm_user] for norm_user in missing_users]
                        logger.warning(
                            f"The following IAM users are missing from database (must be created via Terraform/gcloud first): {missing_emails}")
                        # Filter out missing users
                        iam_users = [user for user in iam_users
                                     if self.normalize_service_account_name(user['name']) not in missing_users]

                    # Existing users that are no longer requested (permissions to revoke)
                    users_to_revoke = existing_iam_users - requested_users_normalized

                    logger.info(f"Processing permissions for {len(iam_users)} IAM users, "
                                f"revoking permissions for {len(users_to_revoke)} users, "
                                f"skipping {len(missing_users)} missing users")

                    success_count = 0
                    error_count = 0
                    revoke_success_count = 0
                    revoke_error_count = 0

                    # Process requested users (update permissions)
                    for user in iam_users:
                        username = user['name']
                        permission_level = user['permission_level']

                        try:
                            # Intermediate commit for each user
                            conn.commit()

                            if self.update_user_permissions(cursor, username, permission_level, database_name,
                                                            schema_name):
                                success_count += 1
                                conn.commit()
                                logger.info(f"Successfully updated permissions for user {username}")
                            else:
                                error_count += 1
                                conn.rollback()
                                logger.error(f"Failed to update permissions for user {username}")

                        except Exception as e:
                            logger.error(f"Error processing permissions for user {username}: {e}")
                            error_count += 1
                            try:
                                conn.rollback()
                            except Exception as rollback_err:
                                logger.warning(f"Rollback failed for user {username}: {rollback_err}")

                    # Revoke permissions for users that are no longer requested
                    for normalized_username in users_to_revoke:
                        try:
                            conn.commit()
                            if self.revoke_all_permissions(cursor, normalized_username, database_name, schema_name):
                                revoke_success_count += 1
                                logger.info(f"Revoked all permissions for user {normalized_username}")
                                conn.commit()
                            else:
                                revoke_error_count += 1
                                conn.rollback()
                                logger.error(f"Failed to revoke permissions for user {normalized_username}")

                        except Exception as e:
                            logger.error(f"Error revoking permissions for user {normalized_username}: {e}")
                            revoke_error_count += 1
                            try:
                                conn.rollback()
                            except Exception as rollback_err:
                                logger.warning(
                                    f"Rollback failed for user revocation {normalized_username}: {rollback_err}")

                    # Final commit
                    conn.commit()

                    # Prepare result
                    result = {
                        "success": True,
                        "project_id": project_id,
                        "instance_name": instance_name,
                        "database_name": database_name,
                        "schema_name": schema_name,
                        "users_processed": success_count,
                        "permissions_revoked": revoke_success_count,
                        "missing_users_count": len(missing_users),
                        "missing_users": [normalized_requested_users.get(user, user) for user in missing_users],
                        "permission_errors": error_count,
                        "revoke_errors": revoke_error_count,
                        "total_errors": error_count + revoke_error_count,
                        "message_id": message_data.get('_pubsub_metadata', {}).get('messageId')
                    }

                    # Add warnings if necessary
                    warnings = []
                    if missing_users:
                        missing_emails = [normalized_requested_users.get(user, user) for user in missing_users]
                        warning_msg = f"Some IAM users were missing from database: {missing_emails}"
                        warnings.append(warning_msg)
                        logger.warning(warning_msg)

                    if error_count > 0:
                        warning_msg = f"Failed to update permissions for {error_count} users"
                        warnings.append(warning_msg)

                    if revoke_error_count > 0:
                        warning_msg = f"Failed to revoke permissions for {revoke_error_count} users"
                        warnings.append(warning_msg)

                    if warnings:
                        result["warnings"] = warnings

                    logger.info(f"Successfully processed IAM user permissions: {result}")
                    return result

                except Exception as e:
                    # Final rollback in case of critical error
                    try:
                        conn.rollback()
                    except Exception as rollback_err:
                        logger.warning(f"Final rollback failed: {rollback_err}")
                    raise e

        except Exception as e:
            logger.error(f"Failed to process IAM user permissions for {project_id}/{instance_name}: {e}")
            return {
                "success": False,
                "project_id": project_id,
                "instance_name": instance_name,
                "database_name": database_name,
                "schema_name": schema_name,
                "error": str(e),
                "message_id": message_data.get('_pubsub_metadata', {}).get('messageId')
            }

    def close(self):
        """Close the connector properly"""
        try:
            self.connector.close()
            logger.info("Cloud SQL connector closed successfully")
        except Exception as e:
            logger.warning(f"Error closing connector: {e}")


# Global instances
user_manager = CloudSQLUserManager()
message_parser = PubSubMessageParser()


# FastAPI lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting Cloud SQL IAM User Permission Manager")
    yield
    logger.info("Shutting down Cloud SQL IAM User Permission Manager")
    user_manager.close()


# Initialize FastAPI app
app = FastAPI(
    title="Cloud SQL IAM User Permission Manager",
    description="""
    A service to manage IAM user permissions for Cloud SQL PostgreSQL databases.

    **IMPORTANT**: This service only manages SQL permissions (GRANT/REVOKE).
    IAM users must be created separately via Terraform, gcloud, or Cloud SQL API.

    Features:
    - Automatic schema creation if it doesn't exist
    - Permission levels: readonly, readwrite, admin
    - Pub/Sub message processing
    - Comprehensive error handling and logging
    - Automatic cleanup of permissions for removed users
    """,
    version="4.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint for service monitoring

    Returns service status and version information.
    """
    return HealthResponse(
        status="healthy",
        service="Cloud SQL IAM User Permission Manager",
        version="4.0.0"
    )


@app.post("/", status_code=204, tags=["Pub/Sub"])
@app.post("/pubsub", status_code=204, tags=["Pub/Sub"])
async def handle_pubsub(request: Request):
    """
    Main endpoint for processing Pub/Sub messages

    **IMPORTANT**: This service only manages permissions for IAM Database Authentication users.
    The IAM users themselves must be created/deleted via Terraform, gcloud, or Cloud SQL API.

    Expected message format:
    ```json
    {
        "project_id": "my-project",
        "instance_name": "my-instance",
        "database_name": "my-db",
        "region": "europe-west1",
        "schema_name": "my-schema",
        "iam_users": [
            {
                "name": "user@project.iam.gserviceaccount.com",
                "permission_level": "readonly|readwrite|admin"
            }
        ]
    }
    ```

    Returns HTTP 204 on success, HTTP 400/500 on error.
    """
    try:
        # Parse Pub/Sub message
        request_json = await request.json()
        logger.info("Received Pub/Sub message for IAM user permission management")

        # Basic JSON validation
        if not request_json:
            logger.error("Empty request payload")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty request payload"
            )

        try:
            message_data = message_parser.parse_pubsub_message(request_json)
        except ValueError as e:
            logger.error(f"Invalid Pub/Sub message format: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid message format: {str(e)}"
            )

        # Validate message schema
        try:
            validated_data = message_parser.validate_message_schema(message_data)
        except ValueError as e:
            logger.error(f"Invalid message schema: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid message schema: {str(e)}"
            )

        # Log processing information (without sensitive data)
        logger.info(f"Processing IAM user permissions for project: {validated_data['project_id']}, "
                    f"instance: {validated_data['instance_name']}, "
                    f"database: {validated_data['database_name']}, "
                    f"schema: {validated_data['schema_name']}, "
                    f"region: {validated_data['region']}, "
                    f"users: {len(validated_data['iam_users'])}")

        # Check if there are users to process or revocations to perform
        if not validated_data['iam_users']:
            logger.info("No IAM users specified in message - will revoke permissions for all existing users")

        # Validate IAM permissions for specified users
        if validated_data['iam_users']:
            permissions_valid, invalid_users = user_manager.validate_iam_permissions(
                validated_data['project_id'],
                validated_data['iam_users']
            )

            if not permissions_valid:
                # Filter out invalid users
                original_count = len(validated_data['iam_users'])
                validated_data['iam_users'] = [
                    user for user in validated_data['iam_users']
                    if user['name'] not in invalid_users
                ]

                logger.warning(
                    f"Proceeding with {len(validated_data['iam_users'])} valid users out of {original_count}, "
                    f"skipping {len(invalid_users)} users with invalid IAM permissions")

        # Process IAM user permissions
        result = user_manager.process_users(validated_data)

        if result["success"]:
            # Success even with partial errors
            total_errors = result.get("total_errors", 0)
            message_id = result.get('message_id', 'unknown')

            if total_errors > 0:
                logger.warning(f"Processed Pub/Sub message {message_id} with {total_errors} errors")
            else:
                logger.info(f"Successfully processed Pub/Sub message: {message_id}")

            # Return 204 No Content to indicate success to Pub/Sub
            return None
        else:
            logger.error(f"Failed to process IAM user permissions: {result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error=result.get("error", "Unknown processing error"),
                    details={
                        "project_id": result.get("project_id"),
                        "instance_name": result.get("instance_name"),
                        "database_name": result.get("database_name"),
                        "schema_name": result.get("schema_name")
                    }
                ).dict()
            )

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON format"
        )
    except Exception as e:
        logger.error(f"Unexpected error processing Pub/Sub message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/manage-users", response_model=dict, tags=["Direct API"])
async def manage_users_direct(request: IAMUserRequest):
    """
    Direct API endpoint for managing IAM user permissions (not via Pub/Sub)

    This endpoint allows direct management of IAM user permissions without going through Pub/Sub.
    Useful for testing or direct integration.

    **IMPORTANT**: IAM users must already exist in the database (created via Terraform/gcloud).
    """
    try:
        # Convert Pydantic model to dict format expected by process_users
        message_data = {
            'project_id': request.project_id,
            'instance_name': request.instance_name,
            'database_name': request.database_name,
            'region': request.region,
            'schema_name': request.schema_name or f"{request.database_name}_schema",
            'iam_users': [user.dict() for user in request.iam_users]
        }

        logger.info(f"Direct API request for IAM user permissions - project: {request.project_id}, "
                    f"instance: {request.instance_name}, users: {len(request.iam_users)}")

        # Validate IAM permissions for specified users
        if message_data['iam_users']:
            permissions_valid, invalid_users = user_manager.validate_iam_permissions(
                message_data['project_id'],
                message_data['iam_users']
            )

            if not permissions_valid:
                # Filter out invalid users
                original_count = len(message_data['iam_users'])
                message_data['iam_users'] = [
                    user for user in message_data['iam_users']
                    if user['name'] not in invalid_users
                ]

                logger.warning(
                    f"Proceeding with {len(message_data['iam_users'])} valid users out of {original_count}, "
                    f"skipping {len(invalid_users)} users with invalid IAM permissions")

        # Process IAM user permissions
        result = user_manager.process_users(message_data)

        if result["success"]:
            logger.info(f"Successfully processed direct API request for {request.project_id}/{request.instance_name}")
            return result
        else:
            logger.error(f"Failed to process IAM user permissions: {result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error=result.get("error", "Unknown processing error"),
                    details={
                        "project_id": result.get("project_id"),
                        "instance_name": result.get("instance_name"),
                        "database_name": result.get("database_name"),
                        "schema_name": result.get("schema_name")
                    }
                ).dict()
            )

    except Exception as e:
        logger.error(f"Unexpected error in direct API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handler for 404 errors"""
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(error="Endpoint not found").dict()
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc):
    """Handler for 405 errors"""
    return JSONResponse(
        status_code=405,
        content=ErrorResponse(error="Method not allowed").dict()
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handler for Pydantic validation errors"""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="Validation error",
            details={"validation_errors": exc.errors()}
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level=log_level.lower(),
        reload=False
    )