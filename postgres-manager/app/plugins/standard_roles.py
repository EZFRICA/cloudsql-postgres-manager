"""
Standard role definitions plugin.

This module provides the standard role definitions for the CloudSQL PostgreSQL Manager,
using the naming convention {db}_{schema}_{role_type} for schema-specific roles
and {db}_{role_type} for database-wide roles.
"""

from typing import List
from .base import RolePlugin, RoleDefinition


class StandardRolePlugin(RolePlugin):
    """
    Plugin providing standard role definitions.

    This plugin defines the standard roles used by the CloudSQL PostgreSQL Manager:
    - {db}_{schema}_reader: Read-only access to specific schema
    - {db}_{schema}_writer: Write access (inherits from reader)
    - {db}_{schema}_admin: Administrative access (inherits from writer)
    - {db}_{schema}_analyst: Analytics access to specific schema (inherits from reader + monitoring)
    - {db}_monitor: Monitoring access with PostgreSQL native roles
    - {db}_dba_agent: DBA agent monitoring role with comprehensive monitoring access

        All roles are created with postgres as the owner for better security
    and proper permission management.

    Where:
    - db: Database name
    - schema: Schema name
    """

    @property
    def plugin_name(self) -> str:
        """Return the plugin name."""
        return "standard_roles"

    @property
    def plugin_version(self) -> str:
        """Return the plugin version."""
        return "1.0.0"

    def get_role_definitions(
        self, db_name: str, schema_name: str
    ) -> List[RoleDefinition]:
        """
        Return the list of standard role definitions.

        Args:
            db_name: Database name
            schema_name: Schema name

        Returns:
            List of RoleDefinition objects for standard roles
        """
        return [
            self._create_reader_role(db_name, schema_name),
            self._create_writer_role(db_name, schema_name),
            self._create_admin_role(db_name, schema_name),
            self._create_monitor_role(db_name),
            self._create_analyst_role(db_name, schema_name),
            self._create_dba_agent_role(db_name),
        ]

    def _create_reader_role(self, db_name: str, schema_name: str) -> RoleDefinition:
        """Create reader role definition."""
        role_name = f"{db_name}_{schema_name}_reader"
        sql_commands = [
            f"CREATE ROLE {role_name} NOLOGIN;",
            f"GRANT USAGE ON SCHEMA {schema_name} TO {role_name};",
            f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema_name} TO {role_name};",
            f"GRANT SELECT ON ALL SEQUENCES IN SCHEMA {schema_name} TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT SELECT ON TABLES TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT SELECT ON SEQUENCES TO {role_name};",
        ]

        return RoleDefinition(
            name=role_name,
            version="1.0.0",
            checksum=self._calculate_checksum(sql_commands),
            sql_commands=sql_commands,
            inherits=[],
            native_roles=[],
            description=f"Read-only access to {schema_name} schema in {db_name} database",
            status="active",
        )

    def _create_writer_role(self, db_name: str, schema_name: str) -> RoleDefinition:
        """Create writer role definition."""
        role_name = f"{db_name}_{schema_name}_writer"
        reader_role = f"{db_name}_{schema_name}_reader"
        sql_commands = [
            f"CREATE ROLE {role_name} NOLOGIN;",
            f"GRANT {reader_role} TO {role_name};",
            f"GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {schema_name} TO {role_name};",
            f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA {schema_name} TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT INSERT, UPDATE, DELETE ON TABLES TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT USAGE ON SEQUENCES TO {role_name};",
        ]

        return RoleDefinition(
            name=role_name,
            version="1.0.0",
            checksum=self._calculate_checksum(sql_commands),
            sql_commands=sql_commands,
            inherits=[reader_role],
            native_roles=[],
            description=f"Write access to {schema_name} schema in {db_name} database (inherits {reader_role})",
            status="active",
        )

    def _create_admin_role(self, db_name: str, schema_name: str) -> RoleDefinition:
        """Create admin role definition."""
        role_name = f"{db_name}_{schema_name}_admin"
        writer_role = f"{db_name}_{schema_name}_writer"
        sql_commands = [
            f"CREATE ROLE {role_name} NOLOGIN;",
            f"GRANT {writer_role} TO {role_name};",
            f"GRANT CREATE ON SCHEMA {schema_name} TO {role_name};",
            f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {schema_name} TO {role_name};",
            f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {schema_name} TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT ALL PRIVILEGES ON TABLES TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT ALL PRIVILEGES ON SEQUENCES TO {role_name};",
        ]

        return RoleDefinition(
            name=role_name,
            version="1.0.0",
            checksum=self._calculate_checksum(sql_commands),
            sql_commands=sql_commands,
            inherits=[writer_role],
            native_roles=[],
            description=f"Administrative access to {schema_name} schema in {db_name} database (inherits {writer_role})",
            status="active",
        )

    def _create_monitor_role(self, db_name: str) -> RoleDefinition:
        """Create monitor role definition."""
        role_name = f"{db_name}_monitor"
        sql_commands = [
            f"CREATE ROLE {role_name} NOLOGIN;",
            f"GRANT pg_monitor TO {role_name};",
            f"GRANT pg_read_all_stats TO {role_name};",
            f"GRANT pg_read_all_settings TO {role_name};",
        ]

        return RoleDefinition(
            name=role_name,
            version="1.0.0",
            checksum=self._calculate_checksum(sql_commands),
            sql_commands=sql_commands,
            inherits=[],
            native_roles=["pg_monitor", "pg_read_all_stats", "pg_read_all_settings"],
            description=f"Monitoring access with PostgreSQL native monitoring roles for {db_name} database",
            status="active",
        )

    def _create_analyst_role(self, db_name: str, schema_name: str) -> RoleDefinition:
        """Create analyst role definition."""
        role_name = f"{db_name}_{schema_name}_analyst"
        reader_role = f"{db_name}_{schema_name}_reader"
        sql_commands = [
            f"CREATE ROLE {role_name} NOLOGIN;",
            f"GRANT {reader_role} TO {role_name};",
            f"GRANT pg_read_all_stats TO {role_name};",
        ]

        return RoleDefinition(
            name=role_name,
            version="1.0.0",
            checksum=self._calculate_checksum(sql_commands),
            sql_commands=sql_commands,
            inherits=[reader_role],
            native_roles=["pg_read_all_stats"],
            description=f"Analytics access to {schema_name} schema in {db_name} database (inherits {reader_role} + monitoring stats)",
            status="active",
        )

    def _create_dba_agent_role(self, db_name: str) -> RoleDefinition:
        """Create DBA agent monitoring role definition."""
        role_name = f"{db_name}_dba_agent"
        sql_commands = [
            f"CREATE ROLE {role_name} NOLOGIN;",
            # Essential monitoring permissions
            f"GRANT pg_monitor TO {role_name};",
            f"GRANT pg_read_all_stats TO {role_name};",
            f"GRANT pg_read_all_settings TO {role_name};",
            # Monitoring extensions permissions
            f"GRANT SELECT ON pg_stat_statements TO {role_name};",
            # System schema permissions
            f"GRANT USAGE ON SCHEMA information_schema TO {role_name};",
            f"GRANT SELECT ON information_schema.tables TO {role_name};",
            f"GRANT SELECT ON information_schema.columns TO {role_name};",
            f"GRANT SELECT ON information_schema.table_constraints TO {role_name};",
        ]

        return RoleDefinition(
            name=role_name,
            version="1.0.0",
            checksum=self._calculate_checksum(sql_commands),
            sql_commands=sql_commands,
            inherits=[],
            native_roles=["pg_monitor", "pg_read_all_stats", "pg_read_all_settings"],
            description=f"DBA agent monitoring role for {db_name} database with comprehensive monitoring access",
            status="active",
        )

    def _calculate_checksum(self, sql_commands: List[str]) -> str:
        """Calculate SHA256 checksum for SQL commands."""
        import hashlib

        content = "\n".join(sorted(sql_commands))
        return hashlib.sha256(content.encode()).hexdigest()
