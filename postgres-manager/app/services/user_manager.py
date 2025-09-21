import time
from typing import List, Dict
from ..utils.logging_config import logger
from ..utils.role_validation import PostgreSQLValidator
from .connection_manager import ConnectionManager
from .database_validator import DatabaseValidator


class UserManager:
    """Manager for IAM user operations"""

    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    def user_exists(self, cursor, username: str) -> bool:
        """
        Check if a user exists in the database and is a valid IAM user

        Args:
            cursor: Database cursor
            username: Username to check

        Returns:
            True if user exists and is a valid IAM user, False otherwise
        """
        return DatabaseValidator.is_iam_user(cursor, username)

    def is_valid_iam_user(self, cursor, username: str) -> Dict[str, any]:
        """
        Validate if a user is a valid IAM user for this application

        Args:
            cursor: Database cursor
            username: Username to validate

        Returns:
            Dictionary with validation results
        """
        try:
            normalized_username = DatabaseValidator.normalize_service_account_name(
                username
            )

            # Check if user exists
            cursor.execute(
                """
                SELECT 
                    rolname,
                    rolcanlogin,
                    rolsuper,
                    rolcreatedb,
                    rolcreaterole,
                    rolinherit,
                    rolreplication
                FROM pg_roles 
                WHERE rolname = %s
                """,
                (normalized_username,),
            )

            user_info = cursor.fetchone()
            if not user_info:
                return {
                    "valid": False,
                    "reason": "User does not exist in database",
                    "username": normalized_username,
                }

            (
                rolname,
                can_login,
                is_super,
                can_create_db,
                can_create_role,
                can_inherit,
                can_replicate,
            ) = user_info

            # Check if it's a system role that should be excluded
            if PostgreSQLValidator.is_system_role(rolname):
                return {
                    "valid": False,
                    "reason": f"User '{rolname}' is a system role and cannot be managed",
                    "username": normalized_username,
                    "user_type": "system",
                }

            # Check if user can login (required for IAM users)
            if not can_login:
                return {
                    "valid": False,
                    "reason": f"User '{rolname}' cannot login (rolcanlogin=false)",
                    "username": normalized_username,
                    "user_type": "non_login",
                }

            # Check if it's a PostgreSQL system user
            if rolname.startswith(("pg_", "cloudsql")):
                return {
                    "valid": False,
                    "reason": f"User '{rolname}' is a PostgreSQL system user",
                    "username": normalized_username,
                    "user_type": "pg_system",
                }

            return {
                "valid": True,
                "reason": "Valid IAM user",
                "username": normalized_username,
                "user_type": "iam_user",
                "privileges": {
                    "can_login": can_login,
                    "is_superuser": is_super,
                    "can_create_db": can_create_db,
                    "can_create_role": can_create_role,
                    "can_inherit": can_inherit,
                    "can_replicate": can_replicate,
                },
            }

        except Exception as e:
            logger.error(f"Failed to validate IAM user '{username}': {e}")
            return {
                "valid": False,
                "reason": f"Validation failed: {str(e)}",
                "username": username,
                "error": str(e),
            }

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
            # Utiliser les rôles système centralisés
            all_excluded_roles = list(PostgreSQLValidator.get_all_system_roles())
            placeholders = ",".join(["%s"] * len(all_excluded_roles))

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
                all_excluded_roles,
            )

            existing_users = [row[0] for row in cursor.fetchall()]
            logger.info(
                f"Found {len(existing_users)} existing IAM users (excluding system and group roles)"
            )
            logger.debug(f"IAM users found: {existing_users}")
            return existing_users

        except Exception as e:
            logger.error(f"Failed to get existing IAM users: {e}")
            return []

    def get_users_and_roles(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        schema_name: str,
    ) -> dict:
        """
        Get all IAM users and their assigned roles for a schema.
        Filters out system and group roles that cannot be managed.

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            schema_name: Schema name

        Returns:
            Dictionary with IAM users and their roles
        """
        start_time = time.time()

        try:
            with self.connection_manager.get_connection(
                project_id, region, instance_name, database_name
            ) as conn:
                cursor = conn.cursor()

                try:
                    # Utiliser les rôles système centralisés
                    system_roles = list(PostgreSQLValidator.get_all_system_roles())
                    placeholders = ",".join(["%s"] * len(system_roles))

                    # Get all users with their roles for this schema
                    cursor.execute(
                        f"""
                        SELECT 
                            u.rolname as username,
                            COALESCE(
                                array_agg(r.rolname ORDER BY r.rolname) 
                                FILTER (WHERE r.rolname IS NOT NULL), 
                                ARRAY[]::text[]
                            ) as roles,
                            u.rolcanlogin as can_login,
                            u.rolsuper as is_superuser,
                            u.rolcreatedb as can_create_db,
                            u.rolcreaterole as can_create_role
                        FROM pg_roles u
                        LEFT JOIN pg_auth_members m ON u.oid = m.member
                        LEFT JOIN pg_roles r ON m.roleid = r.oid AND r.rolname LIKE %s
                        WHERE u.rolcanlogin = true
                        AND u.rolname NOT IN ({placeholders})
                        AND u.rolname NOT LIKE 'cloudsql%%'
                        AND u.rolname NOT LIKE 'pg_%%'
                        GROUP BY u.rolname, u.rolcanlogin, u.rolsuper, u.rolcreatedb, u.rolcreaterole
                        ORDER BY u.rolname
                        """,
                        [f"{database_name}_{schema_name}_%"] + system_roles,
                    )

                    users = []
                    for row in cursor.fetchall():
                        (
                            username,
                            roles,
                            can_login,
                            is_superuser,
                            can_create_db,
                            can_create_role,
                        ) = row

                        # Valider que c'est bien un utilisateur IAM gérable
                        validation = self.is_valid_iam_user(cursor, username)

                        user_data = {
                            "username": username,
                            "roles": roles,
                            "is_iam_user": validation["valid"],
                            "user_type": validation.get("user_type", "unknown"),
                            "privileges": {
                                "can_login": can_login,
                                "is_superuser": is_superuser,
                                "can_create_db": can_create_db,
                                "can_create_role": can_create_role,
                            },
                        }

                        # Ajouter des informations de validation si non valide
                        if not validation["valid"]:
                            user_data["validation_reason"] = validation["reason"]

                        users.append(user_data)

                    # Séparer les utilisateurs valides des non-valides pour le rapport
                    valid_users = [u for u in users if u["is_iam_user"]]
                    invalid_users = [u for u in users if not u["is_iam_user"]]

                    logger.info(
                        f"Found {len(valid_users)} valid IAM users and {len(invalid_users)} system/invalid users for schema {schema_name}"
                    )

                    return {
                        "success": True,
                        "message": f"Retrieved {len(valid_users)} manageable IAM users ({len(invalid_users)} system users excluded)",
                        "users": valid_users,
                        "system_users_excluded": invalid_users,
                        "project_id": project_id,
                        "instance_name": instance_name,
                        "database_name": database_name,
                        "schema_name": schema_name,
                        "execution_time_seconds": time.time() - start_time,
                    }

                except Exception as e:
                    raise e
                finally:
                    cursor.close()

        except Exception as e:
            logger.error(f"Failed to get users and roles: {e}")
            return {
                "success": False,
                "message": f"Failed to get users and roles: {str(e)}",
                "users": [],
                "system_users_excluded": [],
                "project_id": project_id,
                "instance_name": instance_name,
                "database_name": database_name,
                "schema_name": schema_name,
                "execution_time_seconds": time.time() - start_time,
            }

    def get_system_roles_info(self, cursor) -> Dict[str, any]:
        """
        Get information about all system roles in the database
        Useful for debugging and understanding the IAM setup

        Args:
            cursor: Database cursor

        Returns:
            Dictionary with system roles information
        """
        try:
            # Préparer les listes de rôles pour la catégorisation
            admin_roles = list(PostgreSQLValidator.get_cloud_sql_admin_roles())
            iam_group_roles = list(PostgreSQLValidator.get_cloud_sql_iam_group_roles())

            cursor.execute(
                """
                SELECT 
                    rolname,
                    rolcanlogin,
                    rolsuper,
                    rolcreatedb,
                    rolcreaterole,
                    rolinherit,
                    rolreplication,
                    CASE 
                        WHEN rolname = ANY(%s)
                        THEN 'database_admin'
                        WHEN rolname = ANY(%s)
                        THEN 'iam_group_role'
                        WHEN rolname LIKE 'pg_%' 
                        THEN 'postgresql_system'
                        WHEN rolname LIKE 'cloudsql%' 
                        THEN 'cloudsql_system'
                        ELSE 'iam_user'
                    END as role_category
                FROM pg_roles
                ORDER BY role_category, rolname
                """,
                (admin_roles, iam_group_roles),
            )

            roles_info = {
                "database_admin": [],
                "iam_group_role": [],
                "postgresql_system": [],
                "cloudsql_system": [],
                "iam_user": [],
            }

            for row in cursor.fetchall():
                (
                    rolname,
                    can_login,
                    is_super,
                    can_create_db,
                    can_create_role,
                    can_inherit,
                    can_replicate,
                    category,
                ) = row

                role_info = {
                    "name": rolname,
                    "can_login": can_login,
                    "is_superuser": is_super,
                    "can_create_db": can_create_db,
                    "can_create_role": can_create_role,
                    "can_inherit": can_inherit,
                    "can_replicate": can_replicate,
                }

                roles_info[category].append(role_info)

            # Statistiques
            stats = {
                "total_roles": sum(len(roles) for roles in roles_info.values()),
                "manageable_iam_users": len(roles_info["iam_user"]),
                "system_roles": len(roles_info["database_admin"])
                + len(roles_info["postgresql_system"])
                + len(roles_info["cloudsql_system"]),
                "iam_group_roles": len(roles_info["iam_group_role"]),
            }

            return {
                "success": True,
                "roles_by_category": roles_info,
                "statistics": stats,
                "message": f"Found {stats['manageable_iam_users']} manageable IAM users out of {stats['total_roles']} total roles",
            }

        except Exception as e:
            logger.error(f"Failed to get system roles info: {e}")
            return {"success": False, "error": str(e)}

    def grant_user_to_postgres(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        username: str,
    ) -> dict:
        """
        Grant an IAM user to postgres to allow postgres to manage this user.

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            username: IAM username

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
                    # Validate that this is a manageable IAM user
                    validation = self.is_valid_iam_user(cursor, username)
                    if not validation["valid"]:
                        return {
                            "success": False,
                            "message": f"Cannot manage user {username}: {validation['reason']}",
                            "username": username,
                            "validation_reason": validation["reason"],
                            "user_type": validation.get("user_type", "unknown"),
                            "execution_time_seconds": time.time() - start_time,
                        }

                    normalized_username = validation["username"]

                    # Check if postgres already inherits permissions from this user
                    cursor.execute(
                        """
                        SELECT 1 FROM pg_roles r1
                        JOIN pg_auth_members m ON r1.oid = m.member
                        JOIN pg_roles r2 ON m.roleid = r2.oid
                        WHERE r1.rolname = 'postgres' 
                        AND r2.rolname = %s
                        """,
                        (normalized_username,),
                    )

                    if cursor.fetchone():
                        return {
                            "success": True,
                            "message": f"postgres already has inheritance from user {normalized_username}",
                            "username": username,
                            "already_granted": True,
                            "execution_time_seconds": time.time() - start_time,
                        }

                    # Grant the IAM user TO postgres
                    grant_command = f'GRANT "{normalized_username}" TO postgres'
                    if not self.connection_manager.execute_sql_safely(
                        cursor, grant_command
                    ):
                        return {
                            "success": False,
                            "message": f"Failed to grant user {normalized_username} to postgres",
                            "username": username,
                            "execution_time_seconds": time.time() - start_time,
                        }

                    conn.commit()
                    logger.info(
                        f"Successfully granted {normalized_username} TO postgres"
                    )

                    return {
                        "success": True,
                        "message": f"User {normalized_username} granted to postgres successfully",
                        "username": username,
                        "normalized_username": normalized_username,
                        "execution_time_seconds": time.time() - start_time,
                    }

                except Exception as e:
                    conn.rollback()
                    raise e
                finally:
                    cursor.close()

        except Exception as e:
            logger.error(f"Failed to grant user {username} to postgres: {e}")
            return {
                "success": False,
                "message": f"Failed to grant user to postgres: {str(e)}",
                "username": username,
                "execution_time_seconds": time.time() - start_time,
            }

    def revoke_user_from_postgres(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        username: str,
    ) -> dict:
        """
        Revoke an IAM user from postgres (remove inheritance).

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            username: IAM username

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
                    normalized_username = (
                        DatabaseValidator.normalize_service_account_name(username)
                    )

                    # Check if postgres currently has this inheritance
                    cursor.execute(
                        """
                        SELECT 1 FROM pg_roles r1
                        JOIN pg_auth_members m ON r1.oid = m.member
                        JOIN pg_roles r2 ON m.roleid = r2.oid
                        WHERE r1.rolname = 'postgres' 
                        AND r2.rolname = %s
                        """,
                        (normalized_username,),
                    )

                    if not cursor.fetchone():
                        return {
                            "success": True,
                            "message": f"postgres does not have inheritance from user {normalized_username}",
                            "username": username,
                            "already_revoked": True,
                            "execution_time_seconds": time.time() - start_time,
                        }

                    # Revoke the IAM user FROM postgres
                    revoke_command = f'REVOKE "{normalized_username}" FROM postgres'
                    if not self.connection_manager.execute_sql_safely(
                        cursor, revoke_command
                    ):
                        return {
                            "success": False,
                            "message": f"Failed to revoke user {normalized_username} from postgres",
                            "username": username,
                            "execution_time_seconds": time.time() - start_time,
                        }

                    conn.commit()
                    logger.info(
                        f"Successfully revoked {normalized_username} FROM postgres"
                    )

                    return {
                        "success": True,
                        "message": f"User {normalized_username} revoked from postgres successfully",
                        "username": username,
                        "normalized_username": normalized_username,
                        "execution_time_seconds": time.time() - start_time,
                    }

                except Exception as e:
                    conn.rollback()
                    raise e
                finally:
                    cursor.close()

        except Exception as e:
            logger.error(f"Failed to revoke user {username} from postgres: {e}")
            return {
                "success": False,
                "message": f"Failed to revoke user from postgres: {str(e)}",
                "username": username,
                "execution_time_seconds": time.time() - start_time,
            }

    def cleanup_user_before_deletion(
        self,
        cursor,
        username: str,
        database_name: str,
        schema_name: str = None,
    ) -> bool:
        """
        Clean up user ownership before permanent deletion.

        This method should be called BEFORE deleting an IAM user to:
        1. Transfer ownership of all objects to postgres
        2. Revoke all permissions
        3. Ensure no orphaned objects remain

        Args:
            cursor: Database cursor
            username: Username being deleted
            database_name: Database name
            schema_name: Optional specific schema (if None, affects all schemas)

        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            normalized_username = DatabaseValidator.normalize_service_account_name(
                username
            )

            logger.info(
                f"Starting cleanup for user {normalized_username} before deletion"
            )

            # 1. Transfer ownership of all objects to postgres
            reassign_cmd = f'REASSIGN OWNED BY "{normalized_username}" TO postgres'

            if not self.connection_manager.execute_sql_safely(cursor, reassign_cmd):
                logger.error(
                    f"Failed to reassign owned objects for {normalized_username}"
                )
                return False

            # 2. Revoke all permissions (existing method)
            if schema_name:
                success = self._revoke_all_schemas_permissions(
                    cursor, normalized_username, database_name, [schema_name]
                )
            else:
                # Revoke from all schemas if none specified
                success = self._revoke_all_schemas_permissions(
                    cursor, normalized_username, database_name
                )

            if not success:
                logger.warning(
                    f"Some permission revocations failed for {normalized_username}"
                )

            # 3. Drop objects owned by user (after reassignment, this should be minimal)
            drop_cmd = f'DROP OWNED BY "{normalized_username}"'

            if not self.connection_manager.execute_sql_safely(cursor, drop_cmd):
                logger.warning(
                    f"Failed to drop remaining owned objects for {normalized_username}"
                )

            logger.info(f"Cleanup completed for user {normalized_username}")
            return True

        except Exception as e:
            logger.error(f"Error during cleanup for user {username}: {e}")
            return False

    def _revoke_all_schemas_permissions(
        self,
        cursor,
        username: str,
        database_name: str,
        specific_schemas: List[str] = None,
    ) -> bool:
        """
        Helper method to revoke permissions from all schemas or specific schemas.

        Args:
            cursor: Database cursor
            username: Username to revoke permissions from
            database_name: Database name
            specific_schemas: Optional list of specific schemas to target

        Returns:
            True if all revocations successful, False otherwise
        """
        try:
            if specific_schemas:
                schemas = specific_schemas
            else:
                # Get all schemas in database
                cursor.execute(
                    """
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                    AND catalog_name = %s
                """,
                    (database_name,),
                )

                schemas = [row[0] for row in cursor.fetchall()]

            overall_success = True
            for schema in schemas:
                # Import here to avoid circular imports
                from .role_permission_manager import RolePermissionManager
                from .schema_manager import SchemaManager

                # Create temporary instances for the cleanup operation
                schema_manager = SchemaManager(self.connection_manager)
                role_permission_manager = RolePermissionManager(
                    self.connection_manager, schema_manager, self
                )

                success = role_permission_manager.revoke_all_permissions(
                    cursor, username, database_name, schema
                )
                if not success:
                    overall_success = False

            return overall_success

        except Exception as e:
            logger.error(f"Error revoking permissions from schemas: {e}")
            return False
