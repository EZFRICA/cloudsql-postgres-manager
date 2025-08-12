import os
from contextlib import contextmanager
from typing import List, Tuple, Dict
from google.cloud.sql.connector import Connector, IPTypes
from google.cloud import resourcemanager_v3
from google.iam.v1 import iam_policy_pb2
from ..utils.logging_config import logger
from ..utils.secret_manager import access_regional_secret

DB_ADMIN_USER = os.environ.get("DB_ADMIN_USER", "postgres")


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
        if service_account_email.endswith(".gserviceaccount.com"):
            return service_account_email.replace(".gserviceaccount.com", "")
        return service_account_email

    @contextmanager
    def get_connection(
        self, project_id: str, region: str, instance_name: str, database_name: str
    ):
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
                ip_type=IPTypes.PRIVATE,
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

    def validate_iam_permissions(
        self, project_id: str, iam_users: List[Dict]
    ) -> Tuple[bool, List[str]]:
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
            request = iam_policy_pb2.GetIamPolicyRequest(
                resource=f"projects/{project_id}"
            )
            policy = client.get_iam_policy(request=request)

            # Extract all members with the required role
            members_with_role = set()
            for binding in policy.bindings:
                if binding.role == required_role:
                    for member in binding.members:
                        if member.startswith("user:"):
                            members_with_role.add(member[5:])  # Remove "user:"
                        elif member.startswith("serviceAccount:"):
                            members_with_role.add(
                                member[15:]
                            )  # Remove "serviceAccount:"

            logger.info(
                f"Found {len(members_with_role)} members with role {required_role} in project {project_id}"
            )

            # Check each user
            all_usernames = {user.get("name") for user in iam_users if user.get("name")}
            invalid_users = list(all_usernames - members_with_role)

            if invalid_users:
                logger.warning(
                    f"Users missing required IAM role '{required_role}': {invalid_users}"
                )

            return not invalid_users, invalid_users

        except Exception as e:
            logger.error(
                f"Failed to validate IAM permissions for project {project_id}: {e}"
            )
            # In case of error, consider all users as invalid (security)
            all_usernames = [user.get("name") for user in iam_users if user.get("name")]
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
            cursor.execute(
                """
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.schemata 
                    WHERE schema_name = %s
                )
            """,
                (schema_name,),
            )

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
            # Build list of roles to exclude (system)
            excluded_roles = [
                "postgres",
                "cloudsqlsuperuser",
                "cloudsqladmin",
                "cloudsqlreplica",
            ]

            # Create placeholders for the query
            placeholders = ",".join(["%s"] * len(excluded_roles))

            cursor.execute(
                f"""
                SELECT rolname FROM pg_roles 
                WHERE rolname NOT IN ({placeholders})
                AND rolname NOT LIKE 'cloudsql%%'
                AND rolname NOT LIKE 'pg_%%'
                AND rolname NOT LIKE 'information_schema%%'
                AND NOT rolsuper  -- Exclude superusers
                AND rolcanlogin = true  -- Include only login roles
            """,
                excluded_roles,
            )

            existing_users = [row[0] for row in cursor.fetchall()]
            logger.info(f"Found {len(existing_users)} existing IAM users")
            logger.debug(f"IAM users found: {existing_users}")
            return existing_users

        except Exception as e:
            logger.error(f"Failed to get existing IAM users: {e}")
            return []

    def revoke_all_permissions(
        self, cursor, username: str, database_name: str, schema_name: str
    ) -> bool:
        """
        Revoke all permissions from an IAM user
        """
        try:
            logger.debug(
                f"Revoking all permissions for user {username} on schema {schema_name}"
            )

            # Check if schema exists before operations
            if not self.schema_exists(cursor, schema_name):
                logger.warning(
                    f"Schema '{schema_name}' does not exist, skipping revocation for user {username}"
                )
                return True

            # Transfer ownership if necessary
            cursor.execute(
                """
                SELECT pg_catalog.pg_get_userbyid(d.datdba) as owner 
                FROM pg_catalog.pg_database d 
                WHERE d.datname = %s
            """,
                (database_name,),
            )

            current_owner = cursor.fetchone()
            if current_owner and current_owner[0] == username:
                logger.info(
                    f"User {username} is owner of database {database_name}, transferring ownership back to postgres"
                )
                if not self.execute_sql_safely(
                    cursor, f'ALTER DATABASE "{database_name}" OWNER TO postgres'
                ):
                    logger.warning(
                        f"Failed to transfer database ownership from {username}"
                    )

            cursor.execute(
                """
                SELECT pg_catalog.pg_get_userbyid(n.nspowner) as owner 
                FROM pg_catalog.pg_namespace n 
                WHERE n.nspname = %s
            """,
                (schema_name,),
            )

            schema_owner = cursor.fetchone()
            if schema_owner and schema_owner[0] == username:
                logger.info(
                    f"User {username} is owner of schema {schema_name}, transferring ownership back to postgres"
                )
                if not self.execute_sql_safely(
                    cursor, f'ALTER SCHEMA "{schema_name}" OWNER TO postgres'
                ):
                    logger.warning(
                        f"Failed to transfer schema ownership from {username}"
                    )

            # Revoke existing permissions
            revoke_commands = [
                f'REVOKE ALL PRIVILEGES ON DATABASE "{database_name}" FROM "{username}"',
                f'REVOKE ALL PRIVILEGES ON SCHEMA "{schema_name}" FROM "{username}"',
                f'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{schema_name}" FROM "{username}"',
                f'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA "{schema_name}" FROM "{username}"',
                f'REVOKE ALL PRIVILEGES ON ALL ROUTINES IN SCHEMA "{schema_name}" FROM "{username}"',
            ]

            success = True
            for cmd in revoke_commands:
                if not self.execute_sql_safely(cursor, cmd):
                    success = False

            # Clean up default privileges
            default_privilege_commands = [
                f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" REVOKE ALL PRIVILEGES ON TABLES FROM "{username}"',
                f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" REVOKE ALL PRIVILEGES ON SEQUENCES FROM "{username}"',
                f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" REVOKE ALL PRIVILEGES ON ROUTINES FROM "{username}"',
            ]

            for cmd in default_privilege_commands:
                if not self.execute_sql_safely(cursor, cmd):
                    success = False

            if success:
                logger.info(f"Successfully revoked all permissions for user {username}")
            else:
                logger.warning(
                    f"Some permission revocations failed for user {username}"
                )

            return success

        except Exception as e:
            logger.error(f"Error revoking permissions for user {username}: {e}")
            return False

    def grant_permissions(
        self,
        cursor,
        username: str,
        permission_level: str,
        database_name: str,
        schema_name: str,
    ) -> bool:
        """
        Grant permissions according to specified level to an existing IAM user
        """
        try:
            logger.debug(
                f"Granting {permission_level} permissions to user {username} on schema {schema_name}"
            )

            # Check if schema exists before granting permissions
            if not self.schema_exists(cursor, schema_name):
                logger.error(
                    f"Cannot grant permissions: schema '{schema_name}' does not exist"
                )
                return False

            # Base permissions
            base_commands = [
                f'GRANT CONNECT ON DATABASE "{database_name}" TO "{username}"',
                f'GRANT USAGE ON SCHEMA "{schema_name}" TO "{username}"',
            ]

            # Permissions based on level
            if permission_level == "admin":
                # For admin, make owner of database and schema
                permission_commands = [
                    f'GRANT ALL PRIVILEGES ON DATABASE "{database_name}" TO "{username}"',
                    f'GRANT ALL PRIVILEGES ON SCHEMA "{schema_name}" TO "{username}"',
                    f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{schema_name}" TO "{username}"',
                    f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA "{schema_name}" TO "{username}"',
                    f'GRANT EXECUTE ON ALL ROUTINES IN SCHEMA "{schema_name}" TO "{username}"',
                ]
                default_privilege_commands = [
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT ALL PRIVILEGES ON TABLES TO "{username}"',
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT ALL PRIVILEGES ON SEQUENCES TO "{username}"',
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT EXECUTE ON ROUTINES TO "{username}"',
                ]

            elif permission_level == "readwrite":
                permission_commands = base_commands + [
                    f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "{schema_name}" TO "{username}"',
                    f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA "{schema_name}" TO "{username}"',
                    f'GRANT EXECUTE ON ALL ROUTINES IN SCHEMA "{schema_name}" TO "{username}"',
                ]
                default_privilege_commands = [
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{username}"',
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT USAGE, SELECT ON SEQUENCES TO "{username}"',
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT EXECUTE ON ROUTINES TO "{username}"',
                ]

            else:  # readonly
                permission_commands = base_commands + [
                    f'GRANT SELECT ON ALL TABLES IN SCHEMA "{schema_name}" TO "{username}"',
                    f'GRANT SELECT ON ALL SEQUENCES IN SCHEMA "{schema_name}" TO "{username}"',
                    f'GRANT EXECUTE ON ALL ROUTINES IN SCHEMA "{schema_name}" TO "{username}"',
                ]
                default_privilege_commands = [
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT SELECT ON TABLES TO "{username}"',
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT SELECT ON SEQUENCES TO "{username}"',
                    f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT EXECUTE ON ROUTINES TO "{username}"',
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
                    f"Successfully granted {permission_level} permissions to user {username} on schema {schema_name}"
                )
            else:
                logger.error(f"Failed to grant some permissions to user {username}")

            return success

        except Exception as e:
            logger.error(f"Error granting permissions to user {username}: {e}")
            return False

    def update_user_permissions(
        self,
        cursor,
        username: str,
        permission_level: str,
        database_name: str,
        schema_name: str,
    ) -> bool:
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
            cursor.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s", (normalized_username,)
            )
            if cursor.fetchone() is None:
                logger.error(
                    f"IAM user {normalized_username} does not exist in database. Must be created via Terraform/gcloud first."
                )
                return False

            logger.debug(
                f"Updating permissions for existing IAM user {normalized_username}"
            )

            # Check/create schema before any operation
            if not self.create_schema_if_not_exists(cursor, schema_name):
                logger.error(f"Failed to create or verify schema '{schema_name}'")
                return False

            # 1. Clean existing permissions
            if not self.revoke_all_permissions(
                cursor, normalized_username, database_name, schema_name
            ):
                logger.warning(
                    f"Failed to fully revoke existing permissions for {normalized_username}, continuing..."
                )

            # 2. Grant new permissions
            return self.grant_permissions(
                cursor,
                normalized_username,
                permission_level,
                database_name,
                schema_name,
            )

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

        project_id = message_data["project_id"]
        region = message_data["region"]
        instance_name = message_data["instance_name"]
        database_name = message_data["database_name"]
        schema_name = message_data["schema_name"]
        iam_users = message_data["iam_users"]

        try:
            with self.get_connection(
                project_id, region, instance_name, database_name
            ) as conn:
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
                            "message_id": message_data.get("_pubsub_metadata", {}).get(
                                "messageId"
                            ),
                        }

                    # Commit after schema creation
                    conn.commit()

                    # Get existing IAM users in the database
                    existing_iam_users = set(self.get_existing_iam_users(cursor))

                    # Normalize requested usernames (remove .gserviceaccount.com)
                    normalized_requested_users = {
                        self.normalize_service_account_name(user["name"]): user["name"]
                        for user in iam_users
                    }
                    requested_users_normalized = set(normalized_requested_users.keys())

                    # Requested users that don't exist in the database
                    missing_users = requested_users_normalized - existing_iam_users
                    if missing_users:
                        # Convert to original emails for logging
                        missing_emails = [
                            normalized_requested_users[norm_user]
                            for norm_user in missing_users
                        ]
                        logger.warning(
                            f"The following IAM users are missing from database (must be created via Terraform/gcloud first): {missing_emails}"
                        )
                        # Filter out missing users
                        iam_users = [
                            user
                            for user in iam_users
                            if self.normalize_service_account_name(user["name"])
                            not in missing_users
                        ]

                    # Existing users that are no longer requested (permissions to revoke)
                    users_to_revoke = existing_iam_users - requested_users_normalized

                    logger.info(
                        f"Processing permissions for {len(iam_users)} IAM users, "
                        f"revoking permissions for {len(users_to_revoke)} users, "
                        f"skipping {len(missing_users)} missing users"
                    )

                    success_count = 0
                    error_count = 0
                    revoke_success_count = 0
                    revoke_error_count = 0

                    # Process requested users (update permissions)
                    for user in iam_users:
                        username = user["name"]
                        permission_level = user["permission_level"]

                        try:
                            # Intermediate commit for each user
                            conn.commit()

                            if self.update_user_permissions(
                                cursor,
                                username,
                                permission_level,
                                database_name,
                                schema_name,
                            ):
                                success_count += 1
                                conn.commit()
                                logger.info(
                                    f"Successfully updated permissions for user {username}"
                                )
                            else:
                                error_count += 1
                                conn.rollback()
                                logger.error(
                                    f"Failed to update permissions for user {username}"
                                )

                        except Exception as e:
                            logger.error(
                                f"Error processing permissions for user {username}: {e}"
                            )
                            error_count += 1
                            try:
                                conn.rollback()
                            except Exception as rollback_err:
                                logger.warning(
                                    f"Rollback failed for user {username}: {rollback_err}"
                                )

                    # Revoke permissions for users that are no longer requested
                    for normalized_username in users_to_revoke:
                        try:
                            conn.commit()
                            if self.revoke_all_permissions(
                                cursor, normalized_username, database_name, schema_name
                            ):
                                revoke_success_count += 1
                                logger.info(
                                    f"Revoked all permissions for user {normalized_username}"
                                )
                                conn.commit()
                            else:
                                revoke_error_count += 1
                                conn.rollback()
                                logger.error(
                                    f"Failed to revoke permissions for user {normalized_username}"
                                )

                        except Exception as e:
                            logger.error(
                                f"Error revoking permissions for user {normalized_username}: {e}"
                            )
                            revoke_error_count += 1
                            try:
                                conn.rollback()
                            except Exception as rollback_err:
                                logger.warning(
                                    f"Rollback failed for user revocation {normalized_username}: {rollback_err}"
                                )

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
                        "missing_users": [
                            normalized_requested_users.get(user, user)
                            for user in missing_users
                        ],
                        "permission_errors": error_count,
                        "revoke_errors": revoke_error_count,
                        "total_errors": error_count + revoke_error_count,
                        "message_id": message_data.get("_pubsub_metadata", {}).get(
                            "messageId"
                        ),
                    }

                    # Add warnings if necessary
                    warnings = []
                    if missing_users:
                        missing_emails = [
                            normalized_requested_users.get(user, user)
                            for user in missing_users
                        ]
                        warning_msg = f"Some IAM users were missing from database: {missing_emails}"
                        warnings.append(warning_msg)
                        logger.warning(warning_msg)

                    if error_count > 0:
                        warning_msg = (
                            f"Failed to update permissions for {error_count} users"
                        )
                        warnings.append(warning_msg)

                    if revoke_error_count > 0:
                        warning_msg = f"Failed to revoke permissions for {revoke_error_count} users"
                        warnings.append(warning_msg)

                    if warnings:
                        result["warnings"] = warnings

                    logger.info(
                        f"Successfully processed IAM user permissions: {result}"
                    )
                    return result

                except Exception as e:
                    # Final rollback in case of critical error
                    try:
                        conn.rollback()
                    except Exception as rollback_err:
                        logger.warning(f"Final rollback failed: {rollback_err}")
                    raise e

        except Exception as e:
            logger.error(
                f"Failed to process IAM user permissions for {project_id}/{instance_name}: {e}"
            )
            return {
                "success": False,
                "project_id": project_id,
                "instance_name": instance_name,
                "database_name": database_name,
                "schema_name": schema_name,
                "error": str(e),
                "message_id": message_data.get("_pubsub_metadata", {}).get("messageId"),
            }

    def close(self):
        """Close the connector properly"""
        try:
            self.connector.close()
            logger.info("Cloud SQL connector closed successfully")
        except Exception as e:
            logger.warning(f"Error closing connector: {e}")
