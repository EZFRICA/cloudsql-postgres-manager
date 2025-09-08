import time
from typing import Dict
from ..utils.logging_config import logger
from .connection_manager import ConnectionManager
from .schema_manager import SchemaManager
from .user_manager import UserManager
from .database_validator import DatabaseValidator


class RolePermissionManager:
    """Manager for role and permission operations"""

    def __init__(
        self,
        connection_manager: ConnectionManager,
        schema_manager: SchemaManager,
        user_manager: UserManager,
    ):
        self.connection_manager = connection_manager
        self.schema_manager = schema_manager
        self.user_manager = user_manager

    def verify_schema_roles_initialized(
        self, cursor, database_name: str, schema_name: str
    ) -> bool:
        """
        Verify that standard system roles are initialized for the given schema.

        This method checks if all the standard system roles exist, which indicates that the schema
        was created through the role initialization process and has the proper
        standard roles (reader, writer, admin, monitor, analyst) set up.

        Args:
            cursor: Database cursor
            database_name: Database name
            schema_name: Schema name

        Returns:
            True if all system roles are properly initialized, False otherwise
        """
        try:
            # Define all expected system roles for this schema
            expected_roles = [
                f"{database_name}_{schema_name}_reader",
                f"{database_name}_{schema_name}_writer",
                f"{database_name}_{schema_name}_admin",
                f"{database_name}_{schema_name}_analyst",
                f"{database_name}_monitor",  # Database-wide role
            ]

            # Check if schema exists
            if not DatabaseValidator.schema_exists(cursor, schema_name):
                logger.warning(f"Schema '{schema_name}' does not exist.")
                return False

            # Check if all expected system roles exist
            missing_roles = []
            for role in expected_roles:
                if not DatabaseValidator.role_exists(cursor, role):
                    missing_roles.append(role)

            if missing_roles:
                logger.warning(
                    f"Missing system roles for schema '{schema_name}': {missing_roles}"
                )
                return False

            logger.info(
                f"All system roles are properly initialized for schema '{schema_name}'"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error verifying roles initialization for schema '{schema_name}': {e}"
            )
            return False

    def is_system_role(
        self, role_name: str, database_name: str, schema_name: str
    ) -> bool:
        """
        Check if a role is a system role created by our role initialization process.

        Args:
            role_name: Role name to check
            database_name: Database name
            schema_name: Schema name

        Returns:
            True if it's a system role, False otherwise
        """
        system_role_patterns = [
            f"{database_name}_{schema_name}_reader",
            f"{database_name}_{schema_name}_writer",
            f"{database_name}_{schema_name}_admin",
            f"{database_name}_{schema_name}_analyst",
            f"{database_name}_monitor",
        ]

        return role_name in system_role_patterns

    def validate_role_assignment(
        self,
        cursor,
        username: str,
        role_name: str,
        database_name: str,
        schema_name: str,
    ) -> Dict[str, any]:
        """
        Validate if a role can be assigned to a user

        Args:
            cursor: Database cursor
            username: Username to validate
            role_name: Role name to validate
            database_name: Database name
            schema_name: Schema name

        Returns:
            Dictionary with validation results
        """
        try:
            normalized_username = DatabaseValidator.normalize_service_account_name(
                username
            )

            # Check if user is a valid IAM user
            user_validation = self.user_manager.is_valid_iam_user(cursor, username)
            if not user_validation["valid"]:
                return {
                    "valid": False,
                    "reason": f"User validation failed: {user_validation['reason']}",
                    "user_type": user_validation.get("user_type", "unknown"),
                }

            # Check if schema exists
            if not DatabaseValidator.schema_exists(cursor, schema_name):
                return {
                    "valid": False,
                    "reason": f"Schema '{schema_name}' does not exist",
                    "schema_status": "missing",
                }

            # Check if this is a system role (before database queries)
            is_system_role = self.is_system_role(role_name, database_name, schema_name)

            # Check if roles are initialized for the schema
            if not self.verify_schema_roles_initialized(
                cursor, database_name, schema_name
            ):
                return {
                    "valid": False,
                    "reason": f"System roles not initialized for schema '{schema_name}'",
                    "schema_status": "not_initialized",
                }

            # Check if role exists
            if not DatabaseValidator.role_exists(cursor, role_name):
                return {
                    "valid": False,
                    "reason": f"Role '{role_name}' does not exist",
                    "role_type": "missing",
                }

            return {
                "valid": True,
                "reason": "All validations passed",
                "normalized_username": normalized_username,
                "user_type": user_validation["user_type"],
                "role_type": "system_role" if is_system_role else "custom_role",
                "is_system_role": is_system_role,
            }

        except Exception as e:
            logger.error(
                f"Error validating role assignment for user {username}, role {role_name}: {e}"
            )
            return {
                "valid": False,
                "reason": f"Validation error: {str(e)}",
                "error": str(e),
            }

    def revoke_all_permissions(
        self, cursor, username: str, database_name: str, schema_name: str
    ) -> bool:
        """
        Revoke all permissions from an IAM user by removing all assigned roles.

        This method now uses the role-based system instead of executing complex SQL queries.
        The actual permissions are managed by the plugin system through role definitions.

        Args:
            cursor: Database cursor
            username: Username to revoke permissions from
            database_name: Database name
            schema_name: Schema name
        """
        try:
            logger.debug(
                f"Revoking all permissions for user {username} on schema {schema_name}"
            )

            # Check if schema exists before operations
            if not DatabaseValidator.schema_exists(cursor, schema_name):
                logger.warning(
                    f"Schema '{schema_name}' does not exist, skipping revocation for user {username}"
                )
                return True

            # Get all roles that the user currently has
            cursor.execute(
                """
                SELECT r.rolname 
                FROM pg_roles r
                JOIN pg_auth_members m ON r.oid = m.roleid
                JOIN pg_roles u ON m.member = u.oid
                WHERE u.rolname = %s
                AND r.rolname LIKE %s
                """,
                (username, f"{database_name}_{schema_name}_%"),
            )

            assigned_roles = [row[0] for row in cursor.fetchall()]

            if not assigned_roles:
                logger.info(f"User {username} has no roles to revoke")
                return True

            # Revoke all assigned roles
            revoke_commands = []
            for role in assigned_roles:
                revoke_commands.append(f'REVOKE "{role}" FROM "{username}"')

            success = True
            for cmd in revoke_commands:
                if not self.connection_manager.execute_sql_safely(cursor, cmd):
                    logger.warning(f"Failed to revoke: {cmd}")
                    success = False

            if success:
                logger.info(
                    f"Successfully revoked all roles and permissions for user {username}"
                )
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
        permission_role: str,
        database_name: str,
        schema_name: str,
    ) -> bool:
        """
        Grant permissions by assigning the appropriate role to an existing IAM user.

        This method now uses the role-based system instead of executing complex SQL queries.
        The actual permissions are managed by the plugin system through role definitions.
        """
        try:
            logger.debug(
                f"Granting {permission_role} permissions to user {username} on schema {schema_name}"
            )

            # Check if schema exists before granting permissions
            if not DatabaseValidator.schema_exists(cursor, schema_name):
                logger.error(
                    f"Cannot grant permissions: schema '{schema_name}' does not exist"
                )
                return False

            # Compose the full role name from permission_role type
            target_role = f"{database_name}_{schema_name}_{permission_role}"

            # Verify that this is a system role (created by our role initialization)
            if not self.is_system_role(target_role, database_name, schema_name):
                logger.error(
                    f"Role '{target_role}' is not a system role. Only system roles can be assigned through this method."
                )
                return False

            # Check if the target role exists
            if not DatabaseValidator.role_exists(cursor, target_role):
                logger.error(
                    f"Target role '{target_role}' does not exist. Please initialize roles first."
                )
                return False

            # Check if user already has this role (idempotency)
            if DatabaseValidator.has_role(cursor, username, target_role):
                logger.info(f"User {username} already has role {target_role}")
                return True

            # Grant the appropriate role
            grant_command = f'GRANT "{target_role}" TO "{username}"'

            success = self.connection_manager.execute_sql_safely(cursor, grant_command)

            if success:
                logger.info(
                    f"Successfully granted {permission_role} permissions to user {username} by assigning role {target_role}"
                )
            else:
                logger.error(f"Failed to grant permissions to user {username}")

            return success

        except Exception as e:
            logger.error(f"Error granting permissions to user {username}: {e}")
            return False

    def update_user_permissions(
        self,
        cursor,
        username: str,
        permission_role: str,
        database_name: str,
        schema_name: str,
    ) -> bool:
        """
        Update permissions for an existing IAM user

        Args:
            cursor: Database cursor
            username: PostgreSQL username
            permission_role: Desired role name
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
            normalized_username = DatabaseValidator.normalize_service_account_name(
                username
            )

            # Validate that this is a manageable IAM user
            validation = self.user_manager.is_valid_iam_user(cursor, username)
            if not validation["valid"]:
                logger.error(
                    f"Cannot manage user {normalized_username}: {validation['reason']}"
                )
                return False

            logger.debug(
                f"Updating permissions for existing IAM user {normalized_username}"
            )

            # Verify that standard roles are initialized for this schema
            if not self.verify_schema_roles_initialized(
                cursor, database_name, schema_name
            ):
                logger.error(
                    f"Roles not initialized for schema '{schema_name}'. Please run role initialization first."
                )
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
                permission_role,
                database_name,
                schema_name,
            )

        except Exception as e:
            logger.error(f"Error updating permissions for user {username}: {e}")
            return False

    def assign_role(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        schema_name: str,
        username: str,
        role_name: str,
    ) -> dict:
        """
        Assign a role to a user.

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            schema_name: Schema name
            username: Username to assign role to
            role_name: Role name to assign

        Returns:
            Dictionary with operation result
        """
        start_time = time.time()

        try:
            with self.connection_manager.get_connection(
                project_id, region, instance_name, database_name
            ) as conn:
                cursor = conn.cursor()

                try:
                    # Normalize username
                    normalized_username = (
                        DatabaseValidator.normalize_service_account_name(username)
                    )

                    # Validate that this is a manageable IAM user
                    validation = self.user_manager.is_valid_iam_user(cursor, username)
                    if not validation["valid"]:
                        return {
                            "success": False,
                            "message": f"Cannot manage user {normalized_username}: {validation['reason']}",
                            "username": username,
                            "role_name": role_name,
                            "project_id": project_id,
                            "instance_name": instance_name,
                            "database_name": database_name,
                            "schema_name": schema_name,
                            "validation_reason": validation["reason"],
                            "user_type": validation.get("user_type", "unknown"),
                            "execution_time_seconds": time.time() - start_time,
                        }

                    # Check if role exists
                    if not DatabaseValidator.role_exists(cursor, role_name):
                        return {
                            "success": False,
                            "message": f"Role {role_name} does not exist",
                            "username": username,
                            "role_name": role_name,
                            "project_id": project_id,
                            "instance_name": instance_name,
                            "database_name": database_name,
                            "schema_name": schema_name,
                            "execution_time_seconds": time.time() - start_time,
                        }

                    # Check if user already has this role
                    if DatabaseValidator.has_role(
                        cursor, normalized_username, role_name
                    ):
                        logger.info(
                            f"User {normalized_username} already has role {role_name}"
                        )
                        return {
                            "success": True,
                            "message": f"User {normalized_username} already has role {role_name}",
                            "username": username,
                            "role_name": role_name,
                            "project_id": project_id,
                            "instance_name": instance_name,
                            "database_name": database_name,
                            "schema_name": schema_name,
                            "already_assigned": True,
                            "execution_time_seconds": time.time() - start_time,
                        }

                    # Assign role
                    grant_command = f'GRANT "{role_name}" TO "{normalized_username}"'
                    if not self.connection_manager.execute_sql_safely(
                        cursor, grant_command
                    ):
                        return {
                            "success": False,
                            "message": f"Failed to assign role {role_name} to user {normalized_username}",
                            "username": username,
                            "role_name": role_name,
                            "project_id": project_id,
                            "instance_name": instance_name,
                            "database_name": database_name,
                            "schema_name": schema_name,
                            "execution_time_seconds": time.time() - start_time,
                        }

                    conn.commit()
                    logger.info(
                        f"Successfully assigned role {role_name} to user {normalized_username}"
                    )

                    return {
                        "success": True,
                        "message": f"Role {role_name} assigned to user {normalized_username}",
                        "username": username,
                        "role_name": role_name,
                        "project_id": project_id,
                        "instance_name": instance_name,
                        "database_name": database_name,
                        "schema_name": schema_name,
                        "execution_time_seconds": time.time() - start_time,
                    }

                except Exception as e:
                    conn.rollback()
                    raise e
                finally:
                    cursor.close()

        except Exception as e:
            logger.error(f"Failed to assign role {role_name} to user {username}: {e}")
            return {
                "success": False,
                "message": f"Failed to assign role: {str(e)}",
                "username": username,
                "role_name": role_name,
                "project_id": project_id,
                "instance_name": instance_name,
                "database_name": database_name,
                "schema_name": schema_name,
                "execution_time_seconds": time.time() - start_time,
            }

    def revoke_role(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        schema_name: str,
        username: str,
        role_name: str,
    ) -> dict:
        """
        Revoke a role from a user.

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            schema_name: Schema name
            username: Username to revoke role from
            role_name: Role name to revoke

        Returns:
            Dictionary with operation result
        """
        start_time = time.time()

        try:
            with self.connection_manager.get_connection(
                project_id, region, instance_name, database_name
            ) as conn:
                cursor = conn.cursor()

                try:
                    # Normalize username
                    normalized_username = (
                        DatabaseValidator.normalize_service_account_name(username)
                    )

                    # Check if user exists
                    if not self.user_manager.user_exists(cursor, normalized_username):
                        return {
                            "success": False,
                            "message": f"User {normalized_username} does not exist",
                            "username": username,
                            "role_name": role_name,
                            "project_id": project_id,
                            "instance_name": instance_name,
                            "database_name": database_name,
                            "schema_name": schema_name,
                            "execution_time_seconds": time.time() - start_time,
                        }

                    # Check if role exists
                    if not DatabaseValidator.role_exists(cursor, role_name):
                        return {
                            "success": False,
                            "message": f"Role {role_name} does not exist",
                            "username": username,
                            "role_name": role_name,
                            "project_id": project_id,
                            "instance_name": instance_name,
                            "database_name": database_name,
                            "schema_name": schema_name,
                            "execution_time_seconds": time.time() - start_time,
                        }

                    # Revoke role
                    revoke_command = (
                        f'REVOKE "{role_name}" FROM "{normalized_username}"'
                    )
                    if not self.connection_manager.execute_sql_safely(
                        cursor, revoke_command
                    ):
                        return {
                            "success": False,
                            "message": f"Failed to revoke role {role_name} from user {normalized_username}",
                            "username": username,
                            "role_name": role_name,
                            "project_id": project_id,
                            "instance_name": instance_name,
                            "database_name": database_name,
                            "schema_name": schema_name,
                            "execution_time_seconds": time.time() - start_time,
                        }

                    conn.commit()
                    logger.info(
                        f"Successfully revoked role {role_name} from user {normalized_username}"
                    )

                    return {
                        "success": True,
                        "message": f"Role {role_name} revoked from user {normalized_username}",
                        "username": username,
                        "role_name": role_name,
                        "project_id": project_id,
                        "instance_name": instance_name,
                        "database_name": database_name,
                        "schema_name": schema_name,
                        "execution_time_seconds": time.time() - start_time,
                    }

                except Exception as e:
                    conn.rollback()
                    raise e
                finally:
                    cursor.close()

        except Exception as e:
            logger.error(f"Failed to revoke role {role_name} from user {username}: {e}")
            return {
                "success": False,
                "message": f"Failed to revoke role: {str(e)}",
                "username": username,
                "role_name": role_name,
                "project_id": project_id,
                "instance_name": instance_name,
                "database_name": database_name,
                "schema_name": schema_name,
                "execution_time_seconds": time.time() - start_time,
            }
