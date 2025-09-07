"""
Example custom role definitions plugin.

This module demonstrates how to create custom role definitions
using the plugin architecture.
"""

from typing import List
from ..base import RolePlugin, RoleDefinition


class CustomRolePlugin(RolePlugin):
    """
    Example plugin providing custom role definitions.
    
    This plugin demonstrates how developers can create custom role definitions
    for specific application needs with clear naming convention:
    - {db}_{schema}_{role_type}: Schema-specific roles
    - {db}_{role_type}: Database-wide roles
    
    Where:
    - db: Database name (default: "app")
    - schema: Schema name (default: "public")
    - role_type: Type of role (data_scientist, audit, backup, etc.)
    """
    
    @property
    def plugin_name(self) -> str:
        """Return the plugin name."""
        return "custom_roles"
    
    @property
    def plugin_version(self) -> str:
        """Return the plugin version."""
        return "1.0.0"
    
    def get_role_definitions(self, db_name: str = "app", schema_name: str = "public") -> List[RoleDefinition]:
        """
        Return the list of custom role definitions.
        
        Args:
            db_name: Database name (default: "app")
            schema_name: Schema name (default: "public")
        
        Returns:
            List of RoleDefinition objects for custom roles
        """
        return [
            self._create_data_scientist_role(db_name, schema_name),
            self._create_audit_role(db_name, schema_name),
            self._create_backup_role(db_name, schema_name),
            self._create_analytics_readonly_role(db_name, schema_name)
        ]
    
    def _create_data_scientist_role(self, db_name: str, schema_name: str) -> RoleDefinition:
        """Create data_scientist role definition."""
        role_name = f"{db_name}_{schema_name}_data_scientist"
        reader_role = f"{db_name}_{schema_name}_reader"
        sql_commands = [
            f"CREATE ROLE {role_name} NOLOGIN;",
            f"GRANT {reader_role} TO {role_name};",
            f"GRANT pg_read_all_stats TO {role_name};",
            f"GRANT USAGE ON SCHEMA {schema_name} TO {role_name};",
            f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema_name} TO {role_name};",
            f"GRANT SELECT ON ALL SEQUENCES IN SCHEMA {schema_name} TO {role_name};",
            f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {schema_name} TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT SELECT ON TABLES TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT SELECT ON SEQUENCES TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT EXECUTE ON FUNCTIONS TO {role_name};"
        ]
        
        return RoleDefinition(
            name=role_name,
            version="1.0.0",
            checksum=self._calculate_checksum(sql_commands),
            sql_commands=sql_commands,
            inherits=[reader_role],
            native_roles=["pg_read_all_stats"],
            description=f"Data scientist role with read access and statistics monitoring for {schema_name} schema in {db_name} database",
            status="active"
        )
    
    def _create_audit_role(self, db_name: str, schema_name: str) -> RoleDefinition:
        """Create audit role definition."""
        role_name = f"{db_name}_{schema_name}_audit"
        sql_commands = [
            f"CREATE ROLE {role_name} NOLOGIN;",
            f"GRANT USAGE ON SCHEMA {schema_name} TO {role_name};",
            f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema_name} TO {role_name};",
            f"GRANT SELECT ON ALL SEQUENCES IN SCHEMA {schema_name} TO {role_name};",
            f"GRANT SELECT ON ALL FUNCTIONS IN SCHEMA {schema_name} TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT SELECT ON TABLES TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT SELECT ON SEQUENCES TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT SELECT ON FUNCTIONS TO {role_name};"
        ]
        
        return RoleDefinition(
            name=role_name,
            version="1.0.0",
            checksum=self._calculate_checksum(sql_commands),
            sql_commands=sql_commands,
            inherits=[],
            native_roles=[],
            description=f"Audit role with read-only access for compliance monitoring of {schema_name} schema in {db_name} database",
            status="active"
        )
    
    def _create_backup_role(self, db_name: str, schema_name: str) -> RoleDefinition:
        """Create backup role definition."""
        role_name = f"{db_name}_{schema_name}_backup"
        sql_commands = [
            f"CREATE ROLE {role_name} NOLOGIN;",
            f"GRANT USAGE ON SCHEMA {schema_name} TO {role_name};",
            f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema_name} TO {role_name};",
            f"GRANT SELECT ON ALL SEQUENCES IN SCHEMA {schema_name} TO {role_name};",
            f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {schema_name} TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT SELECT ON TABLES TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT SELECT ON SEQUENCES TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT EXECUTE ON FUNCTIONS TO {role_name};"
        ]
        
        return RoleDefinition(
            name=role_name,
            version="1.0.0",
            checksum=self._calculate_checksum(sql_commands),
            sql_commands=sql_commands,
            inherits=[],
            native_roles=[],
            description=f"Backup role with read access for backup operations of {schema_name} schema in {db_name} database",
            status="active"
        )
    
    def _create_analytics_readonly_role(self, db_name: str, schema_name: str) -> RoleDefinition:
        """Create analytics_readonly role definition."""
        role_name = f"{db_name}_{schema_name}_analytics_readonly"
        reader_role = f"{db_name}_{schema_name}_reader"
        sql_commands = [
            f"CREATE ROLE {role_name} NOLOGIN;",
            f"GRANT {reader_role} TO {role_name};",
            f"GRANT pg_read_all_stats TO {role_name};",
            f"GRANT USAGE ON SCHEMA {schema_name} TO {role_name};",
            f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema_name} TO {role_name};",
            f"GRANT SELECT ON ALL SEQUENCES IN SCHEMA {schema_name} TO {role_name};",
            f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {schema_name} TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT SELECT ON TABLES TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT SELECT ON SEQUENCES TO {role_name};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT EXECUTE ON FUNCTIONS TO {role_name};"
        ]
        
        return RoleDefinition(
            name=role_name,
            version="1.0.0",
            checksum=self._calculate_checksum(sql_commands),
            sql_commands=sql_commands,
            inherits=[reader_role],
            native_roles=["pg_read_all_stats"],
            description=f"Analytics read-only role with statistics access for {schema_name} schema in {db_name} database",
            status="active"
        )
    
    def _calculate_checksum(self, sql_commands: List[str]) -> str:
        """Calculate SHA256 checksum for SQL commands."""
        import hashlib
        content = "\n".join(sorted(sql_commands))
        return hashlib.sha256(content.encode()).hexdigest()
    
    def validate_role_definition(self, role_def: RoleDefinition) -> bool:
        """
        Custom validation for role definitions.
        
        This example shows how to add custom validation logic
        beyond the basic dangerous permissions check.
        """
        # Call parent validation first
        if not super().validate_role_definition(role_def):
            return False
        
        # Custom validation: Check for specific patterns
        for command in role_def.sql_commands:
            command_upper = command.upper()
            
            # Prevent roles from being granted SUPERUSER or CREATEDB
            if any(perm in command_upper for perm in ["SUPERUSER", "CREATEDB", "CREATEROLE"]):
                return False
            
            # Prevent roles from being granted REPLICATION
            if "REPLICATION" in command_upper:
                return False
        
        return True