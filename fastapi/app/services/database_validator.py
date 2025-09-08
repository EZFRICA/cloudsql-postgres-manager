"""
Database validation utilities.

This module provides centralized database validation functions
to avoid duplication across different managers.
"""

from ..utils.logging_config import logger
from ..utils.role_validation import PostgreSQLValidator


class DatabaseValidator:
    """
    Centralized database validation utilities.

    This class provides common database validation functions
    to avoid duplication across different managers.
    """

    @staticmethod
    def role_exists(cursor, role_name: str) -> bool:
        """
        Check if a role exists in the database.

        Args:
            cursor: Database cursor
            role_name: Role name to check

        Returns:
            True if role exists, False otherwise
        """
        try:
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,))
            exists = cursor.fetchone() is not None
            logger.debug(f"Role '{role_name}' exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Failed to check role existence for '{role_name}': {e}")
            return False

    @staticmethod
    def schema_exists(cursor, schema_name: str) -> bool:
        """
        Check if a schema exists in the database.

        Args:
            cursor: Database cursor
            schema_name: Schema name to check

        Returns:
            True if schema exists, False otherwise
        """
        try:
            cursor.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                (schema_name,),
            )
            exists = cursor.fetchone() is not None
            logger.debug(f"Schema '{schema_name}' exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Failed to check schema existence for '{schema_name}': {e}")
            return False

    @staticmethod
    def database_exists(cursor, database_name: str) -> bool:
        """
        Check if a database exists.

        Args:
            cursor: Database cursor
            database_name: Database name to check

        Returns:
            True if database exists, False otherwise
        """
        try:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (database_name,)
            )
            exists = cursor.fetchone() is not None
            logger.debug(f"Database '{database_name}' exists: {exists}")
            return exists
        except Exception as e:
            logger.error(
                f"Failed to check database existence for '{database_name}': {e}"
            )
            return False

    @staticmethod
    def is_iam_user(cursor, username: str) -> bool:
        """
        Check if a user is a valid IAM user (not a system role).

        Args:
            cursor: Database cursor
            username: Username to check

        Returns:
            True if user is a valid IAM user, False otherwise
        """
        try:
            # Check if user exists
            cursor.execute(
                """
                SELECT 
                    rolname,
                    rolcanlogin,
                    rolsuper
                FROM pg_roles 
                WHERE rolname = %s
                """,
                (username,),
            )

            user_info = cursor.fetchone()
            if not user_info:
                return False

            rolname, can_login, is_super = user_info

            # Check if it's a system role
            if PostgreSQLValidator.is_system_role(rolname):
                return False

            # Check if user can login (required for IAM users)
            if not can_login:
                return False

            # Check if it's a PostgreSQL system user
            if rolname.startswith(("pg_", "cloudsql")):
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to check if user '{username}' is IAM user: {e}")
            return False

    @staticmethod
    def get_user_roles(cursor, username: str, schema_prefix: str = None) -> list:
        """
        Get all roles assigned to a user.

        Args:
            cursor: Database cursor
            username: Username to check
            schema_prefix: Optional prefix to filter roles (e.g., "mydb_myschema_")

        Returns:
            List of role names assigned to the user
        """
        try:
            if schema_prefix:
                cursor.execute(
                    """
                    SELECT r.rolname 
                    FROM pg_roles r
                    JOIN pg_auth_members m ON r.oid = m.roleid
                    JOIN pg_roles u ON m.member = u.oid
                    WHERE u.rolname = %s AND r.rolname LIKE %s
                    ORDER BY r.rolname
                    """,
                    (username, f"{schema_prefix}%"),
                )
            else:
                cursor.execute(
                    """
                    SELECT r.rolname 
                    FROM pg_roles r
                    JOIN pg_auth_members m ON r.oid = m.roleid
                    JOIN pg_roles u ON m.member = u.oid
                    WHERE u.rolname = %s
                    ORDER BY r.rolname
                    """,
                    (username,),
                )

            roles = [row[0] for row in cursor.fetchall()]
            logger.debug(f"User '{username}' has roles: {roles}")
            return roles

        except Exception as e:
            logger.error(f"Failed to get roles for user '{username}': {e}")
            return []

    @staticmethod
    def has_role(cursor, username: str, role_name: str) -> bool:
        """
        Check if a user has a specific role.

        Args:
            cursor: Database cursor
            username: Username to check
            role_name: Role name to check

        Returns:
            True if user has the role, False otherwise
        """
        try:
            cursor.execute(
                """
                SELECT 1 FROM pg_roles r
                JOIN pg_auth_members m ON r.oid = m.roleid
                JOIN pg_roles u ON m.member = u.oid
                WHERE u.rolname = %s AND r.rolname = %s
                """,
                (username, role_name),
            )

            has_role = cursor.fetchone() is not None
            logger.debug(f"User '{username}' has role '{role_name}': {has_role}")
            return has_role

        except Exception as e:
            logger.error(
                f"Failed to check if user '{username}' has role '{role_name}': {e}"
            )
            return False

    @staticmethod
    def normalize_service_account_name(service_account_email: str) -> str:
        """
        Convert a service account email to PostgreSQL role name.

        This method centralizes the normalization logic used across all managers.

        Args:
            service_account_email: Service account email

        Returns:
            Normalized PostgreSQL role name

        Transformation:
        my-service@project.iam.gserviceaccount.com -> my-service@project.iam
        """
        if service_account_email.endswith(".gserviceaccount.com"):
            # Remove .gserviceaccount.com suffix
            return service_account_email.replace(".gserviceaccount.com", "")
        return service_account_email
