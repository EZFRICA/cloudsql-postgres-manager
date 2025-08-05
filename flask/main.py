import base64
import json
import os
import logging
from contextlib import contextmanager
from typing import List, Tuple, Dict, Optional
from flask import Flask, request, jsonify
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

app = Flask(__name__)

# Configuration from environment
SECRET_NAME_SUFFIXE = os.environ.get('SECRET_NAME_SUFFIXE', 'admin-password')
DB_ADMIN_USER = os.environ.get('DB_ADMIN_USER', 'postgres')

logger.info(f"Secret name prefix: {SECRET_NAME_SUFFIXE}")

def access_regional_secret(project_id: str, instance_name: str, region: str, version: str = "latest") -> str:
    """
      Retrieve a secret from Secret Manager (global or regional)

      Args:
          project_id: GCP project ID
          secret_name: Secret name (without project prefix)
          version: Secret version (default: "latest")
          region: Secret region (optional, uses self.region if defined)

      Returns:
          The decoded secret value

      Raises:
          ValueError: If the secret cannot be retrieved
      """
    try:
        # Regional secret
        secret_id = f"{instance_name}-{SECRET_NAME_SUFFIXE}"

        # Endpoint to call the regional secret manager sever.
        api_endpoint = f"secretmanager.{region}.rep.googleapis.com"

        # Create the Secret Manager client.
        client = secretmanager_v1.SecretManagerServiceClient(
            client_options={"api_endpoint": api_endpoint},
        )

        # Build the resource name of the secret version.
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

class PubSubMessageParser:
    """Parser for Pub/Sub messages with schema validation"""

    @staticmethod
    def parse_pubsub_message(request_json: dict) -> dict:
        """
        Parse a Pub/Sub message and extract the data

        Args:
            request_json: The JSON payload of the request

        Returns:
            The parsed message data with metadata

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
        Validate the message schema and return cleaned data

        Args:
            message_data: The message data to validate

        Returns:
            The validated and cleaned data

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
        Validate that users have the required IAM permissions

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
        Exécute une requête SQL avec gestion d'erreurs

        Args:
            cursor: Curseur de base de données
            sql: Requête SQL à exécuter
            params: Paramètres de la requête (optionnel)

        Returns:
            True si l'exécution réussit, False sinon
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
        Vérifie si un schéma existe dans la base de données

        Args:
            cursor: Curseur de base de données
            schema_name: Nom du schéma à vérifier

        Returns:
            True si le schéma existe, False sinon
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
        Crée un schéma s'il n'existe pas déjà

        Args:
            cursor: Curseur de base de données
            schema_name: Nom du schéma à créer

        Returns:
            True si le schéma existe ou a été créé avec succès, False sinon
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
        Récupère la liste des utilisateurs IAM existants dans la base

        Args:
            cursor: Curseur de base de données

        Returns:
            Liste des noms d'utilisateurs IAM existants

        Note: Les utilisateurs IAM Database Authentication apparaissent comme des rôles
        PostgreSQL normaux une fois créés via Terraform/gcloud/API Cloud SQL.
        Ce code ne fait que lire leur présence, jamais les créer/supprimer.

        Les service accounts apparaissent sans le suffixe .gserviceaccount.com
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
                AND NOT rolsuper  -- Exclure les superutilisateurs
                AND rolcanlogin = true  -- Inclure seulement les rôles de connexion
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
        Révoque toutes les permissions d'un utilisateur IAM
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

            # Revoke existing permissions (without ROUTINES)
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

            # Clean up default privileges (without ROUTINES)
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
        Accorde les permissions selon le niveau spécifié à un utilisateur IAM existant
        """
        try:
            logger.debug(f"Granting {permission_level} permissions to user {username} on schema {schema_name}")

            # Check if schema exists before granting permissions
            if not self.schema_exists(cursor, schema_name):
                logger.error(f"Cannot grant permissions: schema '{schema_name}' does not exist")
                return False

            # Basic permissions
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

            # Appliquer les permissions actuelles
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
        Met à jour les permissions d'un utilisateur IAM existant

        Args:
            cursor: Curseur de base de données
            username: Nom d'utilisateur PostgreSQL
            permission_level: Niveau de permission souhaité
            database_name: Nom de la base de données
            schema_name: Nom du schéma

        Returns:
            True si la mise à jour réussit, False sinon

        IMPORTANT: Cette méthode assume que l'utilisateur IAM existe déjà dans la base
        (créé via Terraform/gcloud/API Cloud SQL). Elle ne fait que gérer les permissions.

        Le username doit être au format PostgreSQL (sans .gserviceaccount.com)
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

            # 1. Nettoyer les permissions existantes
            if not self.revoke_all_permissions(cursor, normalized_username, database_name, schema_name):
                logger.warning(f"Failed to fully revoke existing permissions for {normalized_username}, continuing...")

            # 2. Accorder les nouvelles permissions
            return self.grant_permissions(cursor, normalized_username, permission_level, database_name, schema_name)

        except Exception as e:
            logger.error(f"Error updating permissions for user {username}: {e}")
            return False

    def process_users(self, message_data: dict) -> dict:
        """
        Traite les permissions des utilisateurs IAM avec vérification complète du schéma

        Args:
            message_data: Données du message validées

        Returns:
            Dictionnaire avec le résultat du traitement

        IMPORTANT:
        - Les utilisateurs IAM doivent déjà exister (créés via Terraform/gcloud)
        - Cette fonction gère uniquement les permissions SQL (GRANT/REVOKE)
        - Elle ne crée ni ne supprime d'utilisateurs IAM
        - Le schéma sera créé automatiquement s'il n'existe pas
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
                        # Convertir en emails originaux pour le log
                        missing_emails = [normalized_requested_users[norm_user] for norm_user in missing_users]
                        logger.warning(
                            f"The following IAM users are missing from database (must be created via Terraform/gcloud first): {missing_emails}")
                        # Filtrer les utilisateurs manquants
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

                    # Commit final
                    conn.commit()

                    # Prepare the result
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
                    # Rollback final en cas d'erreur critique
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
        """Ferme le connector proprement"""
        try:
            self.connector.close()
            logger.info("Cloud SQL connector closed successfully")
        except Exception as e:
            logger.warning(f"Error closing connector: {e}")


# Instance globale
user_manager = CloudSQLUserManager()
message_parser = PubSubMessageParser()


@app.route('/health', methods=['GET'])
def health_check():
    """
    Endpoint de vérification de santé du service

    Returns:
        JSON response avec le statut du service
    """
    return jsonify({
        "status": "healthy",
        "service": "Cloud SQL IAM User Permission Manager",
        "version": "3.1"
    }), 200


@app.route('/manage-users', methods=['POST'])
def manage_users_direct():
    """
    Direct endpoint for managing IAM user permissions
    
    Expected format in body:
    {
        "project_id": "my-project",
        "instance_name": "my-instance",
        "database_name": "my-db",
        "region": "europe-west1",
        "schema_name": "my-schema",  # optional, default: {database_name}_schema
        "iam_users": [
            {
                "name": "user@project.iam.gserviceaccount.com",
                "permission_level": "readonly|readwrite|admin"
            }
        ]
    }

    Returns:
        JSON response with operation status
    """
    try:
        # 1. Retrieve and validate JSON data
        request_json = request.get_json()
        logger.info("Received direct API request for IAM user permission management")

        if not request_json:
            logger.error("Empty request payload")
            return jsonify({"error": "Empty request payload"}), 400

        # 2. Validate data schema
        try:
            validated_data = message_parser.validate_message_schema(request_json)
        except ValueError as e:
            logger.error(f"Invalid request schema: {e}")
            return jsonify({"error": f"Invalid request schema: {str(e)}"}), 400

        # 3. Log processing information (without sensitive data)
        logger.info(f"Processing IAM user permissions for project: {validated_data['project_id']}, "
                    f"instance: {validated_data['instance_name']}, "
                    f"database: {validated_data['database_name']}, "
                    f"schema: {validated_data['schema_name']}, "
                    f"region: {validated_data['region']}, "
                    f"users: {len(validated_data['iam_users'])}")

        # 4. Check if there are users to process or revocations to make
        if not validated_data['iam_users']:
            logger.info("No IAM users specified in request - will revoke permissions for all existing users")

        # 5. Validate IAM permissions for specified users
        if validated_data['iam_users']:
            permissions_valid, invalid_users = user_manager.validate_iam_permissions(
                validated_data['project_id'],
                validated_data['iam_users']
            )

            if not permissions_valid:
                # Filtrer les utilisateurs invalides
                original_count = len(validated_data['iam_users'])
                validated_data['iam_users'] = [
                    user for user in validated_data['iam_users']
                    if user['name'] not in invalid_users
                ]

                logger.warning(
                    f"Proceeding with {len(validated_data['iam_users'])} valid users out of {original_count}, "
                    f"skipping {len(invalid_users)} users with invalid IAM permissions")

        # 6. Traiter les permissions des utilisateurs IAM
        result = user_manager.process_users(validated_data)

        if result["success"]:
            # Succès même avec des erreurs partielles
            total_errors = result.get("total_errors", 0)
            
            if total_errors > 0:
                logger.warning(f"Processed direct API request with {total_errors} errors")
                return jsonify({
                    "success": True,
                    "message": f"User permissions processed with {total_errors} errors",
                    "details": result
                }), 200
            else:
                logger.info("Successfully processed direct API request")
                return jsonify({
                    "success": True,
                    "message": "User permissions processed successfully",
                    "details": result
                }), 200
        else:
            logger.error(f"Failed to process direct API request: {result.get('error', 'Unknown error')}")
            return jsonify({
                "success": False,
                "error": result.get('error', 'Unknown error'),
                "details": result
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error in direct API request: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@app.route('/', methods=['POST'])
@app.route('/pubsub', methods=['POST'])
def handle_pubsub():
    """
    Main endpoint for processing Pub/Sub messages

    IMPORTANT: This service only manages IAM Database Authentication user permissions.
    IAM users themselves must be created/deleted via Terraform, gcloud, or Cloud SQL API.

    Expected format in message:
    {
        "project_id": "my-project",
        "instance_name": "my-instance",
        "database_name": "my-db",
        "region": "europe-west1",
        "schema_name": "my-schema",  # optional, default: {database_name}_schema
        "iam_users": [
            {
                "name": "user@project.iam.gserviceaccount.com",
                "permission_level": "readonly|readwrite|admin"
            }
        ]
    }

    Returns:
        HTTP 204 on success, HTTP 400/500 on error
    """
    try:
        # 1. Parse Pub/Sub message
        request_json = request.get_json()
        logger.info("Received Pub/Sub message for IAM user permission management")

        # Basic JSON format validation
        if not request_json:
            logger.error("Empty request payload")
            return jsonify({"error": "Empty request payload"}), 400

        try:
            message_data = message_parser.parse_pubsub_message(request_json)
        except ValueError as e:
            logger.error(f"Invalid Pub/Sub message format: {e}")
            return jsonify({"error": f"Invalid message format: {str(e)}"}), 400

        # 2. Validate data schema
        try:
            validated_data = message_parser.validate_message_schema(message_data)
        except ValueError as e:
            logger.error(f"Invalid message schema: {e}")
            return jsonify({"error": f"Invalid message schema: {str(e)}"}), 400

        # 3. Log processing information (without sensitive data)
        logger.info(f"Processing IAM user permissions for project: {validated_data['project_id']}, "
                    f"instance: {validated_data['instance_name']}, "
                    f"database: {validated_data['database_name']}, "
                    f"schema: {validated_data['schema_name']}, "
                    f"region: {validated_data['region']}, "
                    f"users: {len(validated_data['iam_users'])}")

        # 4. Check if there are users to process or revocations to make
        if not validated_data['iam_users']:
            logger.info("No IAM users specified in message - will revoke permissions for all existing users")

        # 5. Validate IAM permissions for specified users
        if validated_data['iam_users']:
            permissions_valid, invalid_users = user_manager.validate_iam_permissions(
                validated_data['project_id'],
                validated_data['iam_users']
            )

            if not permissions_valid:
                # Filtrer les utilisateurs invalides
                original_count = len(validated_data['iam_users'])
                validated_data['iam_users'] = [
                    user for user in validated_data['iam_users']
                    if user['name'] not in invalid_users
                ]

                logger.warning(
                    f"Proceeding with {len(validated_data['iam_users'])} valid users out of {original_count}, "
                    f"skipping {len(invalid_users)} users with invalid IAM permissions")

        # 6. Traiter les permissions des utilisateurs IAM
        result = user_manager.process_users(validated_data)

        if result["success"]:
            # Succès même avec des erreurs partielles
            total_errors = result.get("total_errors", 0)
            message_id = result.get('message_id', 'unknown')

            if total_errors > 0:
                logger.warning(f"Processed Pub/Sub message {message_id} with {total_errors} errors")
            else:
                logger.info(f"Successfully processed Pub/Sub message: {message_id}")

            # Return 204 No Content to indicate success to Pub/Sub
            return '', 204
        else:
            logger.error(f"Failed to process IAM user permissions: {result.get('error', 'Unknown error')}")
            return jsonify({
                "error": result.get("error", "Unknown processing error"),
                "details": {
                    "project_id": result.get("project_id"),
                    "instance_name": result.get("instance_name"),
                    "database_name": result.get("database_name"),
                    "schema_name": result.get("schema_name")
                }
            }), 500

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        logger.error(f"Unexpected error processing Pub/Sub message: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.errorhandler(404)
def not_found(error):
    """Handler for endpoints not found"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handler for unauthorized methods"""
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_server_error(error):
    """Handler for internal server errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


    # Cleanup when application closes
import atexit


def cleanup():
    """Cleanup function called at shutdown"""
    logger.info("Application shutting down, cleaning up resources")
    user_manager.close()


atexit.register(cleanup)

