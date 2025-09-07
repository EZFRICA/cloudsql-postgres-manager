"""
Role validation utilities.

This module provides validation functions for role definitions
to ensure security and prevent dangerous permissions.
"""

import re
from typing import List, Dict, Any
from ..plugins.base import RoleDefinition
from ..utils.logging_config import logger


class PostgreSQLValidator:
    """
    Helper class for PostgreSQL identifier validation.
    
    Provides utilities for validating PostgreSQL identifiers according to
    PostgreSQL naming conventions and reserved keywords.
    """
    
    # Regex pattern for valid PostgreSQL identifiers
    POSTGRES_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,62}$')
    
    # Reserved PostgreSQL keywords to avoid
    RESERVED_KEYWORDS = {
        'user', 'group', 'order', 'table', 'column', 'index', 'view', 'schema',
        'database', 'role', 'grant', 'revoke', 'create', 'drop', 'alter',
        'select', 'insert', 'update', 'delete', 'from', 'where', 'and', 'or',
        'not', 'null', 'true', 'false', 'public', 'private', 'protected',
        'all', 'any', 'as', 'asc', 'desc', 'distinct', 'exists', 'in', 'is',
        'like', 'between', 'case', 'when', 'then', 'else', 'end', 'if', 'for',
        'while', 'do', 'begin', 'commit', 'rollback', 'savepoint', 'release',
        'transaction', 'isolation', 'level', 'read', 'write', 'only', 'repeatable',
        'serializable', 'uncommitted', 'committed', 'snapshot', 'deferrable',
        'not', 'deferrable', 'initially', 'immediate', 'deferred', 'constraint',
        'check', 'unique', 'primary', 'key', 'foreign', 'references', 'match',
        'full', 'partial', 'simple', 'on', 'action', 'cascade', 'restrict',
        'set', 'default', 'no', 'null', 'initially', 'immediate', 'deferred'
    }
    
    @staticmethod
    def validate_identifier(name: str, field_name: str = "identifier") -> str:
        """
        Validate PostgreSQL identifier format.
        
        Args:
            name: Identifier to validate
            field_name: Field name for error messages
            
        Returns:
            Validated identifier
            
        Raises:
            ValueError: If identifier is invalid
        """
        if not name or not isinstance(name, str):
            raise ValueError(f"{field_name} must be a non-empty string")
        
        # Check length
        if len(name) > 63:
            raise ValueError(f"{field_name} must be 63 characters or less")
        
        # Check pattern
        if not PostgreSQLValidator.POSTGRES_IDENTIFIER_PATTERN.match(name):
            raise ValueError(
                f"{field_name} must start with a letter or underscore, "
                f"followed by letters, digits, or underscores only"
            )
        
        # Check reserved keywords
        if name.lower() in PostgreSQLValidator.RESERVED_KEYWORDS:
            raise ValueError(f"{field_name} cannot be a reserved PostgreSQL keyword: {name}")
        
        return name
    
    @staticmethod
    def validate_schema_name(schema_name: str) -> str:
        """
        Validate schema name specifically.
        
        Args:
            schema_name: Schema name to validate
            
        Returns:
            Validated schema name
            
        Raises:
            ValueError: If schema name is invalid
        """
        # Basic validation
        validated = PostgreSQLValidator.validate_identifier(schema_name, "schema_name")
        
        # Additional schema-specific validations
        if schema_name.lower() in ['information_schema', 'pg_catalog', 'pg_toast']:
            raise ValueError(f"Schema name '{schema_name}' is reserved by PostgreSQL")
        
        return validated

    # Cloud SQL system roles that should be excluded from IAM user management
    CLOUD_SQL_SYSTEM_ROLES = {
        # Database admin roles (can login, have privileges)
        'postgres',  # Default superuser
        'cloudsqlsuperuser', 
        'cloudsqladmin',
        'cloudsqlreplica',
        'cloudsqlagent',
        'cloudsqlconnpooladmin',
        'cloudsqlimportexport',
        'cloudsqllogical',
        'cloudsqlobservability',
        
        # IAM group roles (cannot login directly)
        'cloudsqliamgroup',
        'cloudsqliamgroupserviceaccount', 
        'cloudsqliamgroupuser',
        'cloudsqliamserviceaccount',
        'cloudsqliamuser',
        'cloudsqlinactiveuser'
    }
    
    # PostgreSQL system roles that always exist
    POSTGRES_SYSTEM_ROLES = {
        'pg_database_owner',
        'pg_monitor',
        'pg_read_all_data',
        'pg_read_all_settings', 
        'pg_read_all_stats',
        'pg_read_server_files',
        'pg_write_all_data',
        'pg_write_server_files',
        'pg_execute_server_program',
        'pg_signal_backend',
        'pg_stat_scan_tables',
        'pg_checkpoint'
    }
    
    @classmethod
    def get_all_system_roles(cls) -> set:
        """
        Get all system roles (Cloud SQL + PostgreSQL).
        
        Returns:
            Set of all system role names
        """
        return cls.CLOUD_SQL_SYSTEM_ROLES | cls.POSTGRES_SYSTEM_ROLES
    
    @classmethod
    def get_cloud_sql_admin_roles(cls) -> set:
        """
        Get Cloud SQL admin roles (can login, have privileges).
        
        Returns:
            Set of Cloud SQL admin role names
        """
        return {
            'postgres', 'cloudsqlsuperuser', 'cloudsqladmin', 'cloudsqlreplica',
            'cloudsqlagent', 'cloudsqlconnpooladmin', 'cloudsqlimportexport',
            'cloudsqllogical', 'cloudsqlobservability'
        }
    
    @classmethod
    def get_cloud_sql_iam_group_roles(cls) -> set:
        """
        Get Cloud SQL IAM group roles (cannot login directly).
        
        Returns:
            Set of Cloud SQL IAM group role names
        """
        return {
            'cloudsqliamgroup', 'cloudsqliamgroupserviceaccount', 
            'cloudsqliamgroupuser', 'cloudsqliamserviceaccount',
            'cloudsqliamuser', 'cloudsqlinactiveuser'
        }
    
    @staticmethod
    def is_system_role(role_name: str) -> bool:
        """
        Check if a role is a system role that should be excluded from management.
        
        Args:
            role_name: Role name to check
            
        Returns:
            True if it's a system role that doesn't need validation
        """
        return role_name in PostgreSQLValidator.get_all_system_roles()
    
    @staticmethod
    def is_cloud_sql_system_role(role_name: str) -> bool:
        """
        Check if a role is a Cloud SQL system role.
        
        Args:
            role_name: Role name to check
            
        Returns:
            True if it's a Cloud SQL system role
        """
        return role_name in PostgreSQLValidator.CLOUD_SQL_SYSTEM_ROLES
    
    @staticmethod
    def is_postgres_system_role(role_name: str) -> bool:
        """
        Check if a role is a PostgreSQL system role.
        
        Args:
            role_name: Role name to check
            
        Returns:
            True if it's a PostgreSQL system role
        """
        return role_name in PostgreSQLValidator.POSTGRES_SYSTEM_ROLES


class RoleValidator:
    """
    Validator for role definitions with security checks.
    
    This class provides comprehensive validation for role definitions
    to prevent creation of roles with dangerous permissions.
    """
    
    # Dangerous permissions that should be blocked
    DANGEROUS_PERMISSIONS = [
        "SUPERUSER",
        "CREATEDB",
        "CREATEROLE", 
        "REPLICATION",
        "BYPASSRLS",
        "LOGIN"
    ]
    
    # Dangerous SQL patterns
    DANGEROUS_PATTERNS = [
        "ALTER SYSTEM",
        "CREATE EXTENSION",
        "DROP EXTENSION",
        "CREATE SCHEMA",
        "DROP SCHEMA",
        "CREATE DATABASE",
        "DROP DATABASE"
    ]
    
    @classmethod
    def validate_role_definition(cls, role_def: RoleDefinition) -> Dict[str, Any]:
        """
        Validate a role definition for security and safety.
        
        Args:
            role_def: Role definition to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "security_checks": {
                "dangerous_permissions": False,
                "dangerous_patterns": False,
                "superuser_attempt": False
            }
        }
        
        try:
            # Check for dangerous permissions
            for command in role_def.sql_commands:
                command_upper = command.upper()
                
                # Check for dangerous permissions (but allow NOLOGIN)
                for perm in cls.DANGEROUS_PERMISSIONS:
                    if perm in command_upper and not (perm == "LOGIN" and "NOLOGIN" in command_upper):
                        validation_result["errors"].append(
                            f"Role {role_def.name} contains dangerous permission: {perm}"
                        )
                        validation_result["security_checks"]["dangerous_permissions"] = True
                        validation_result["valid"] = False
                
                # Check for dangerous SQL patterns
                for pattern in cls.DANGEROUS_PATTERNS:
                    if pattern in command_upper:
                        validation_result["errors"].append(
                            f"Role {role_def.name} contains dangerous SQL pattern: {pattern}"
                        )
                        validation_result["security_checks"]["dangerous_patterns"] = True
                        validation_result["valid"] = False
                
                # Check for SUPERUSER attempts
                if "SUPERUSER" in command_upper:
                    validation_result["security_checks"]["superuser_attempt"] = True
                    validation_result["errors"].append(
                        f"Role {role_def.name} attempts to create SUPERUSER - BLOCKED"
                    )
                    validation_result["valid"] = False
            
            # Check role name patterns
            if not cls._is_valid_role_name(role_def.name):
                validation_result["warnings"].append(
                    f"Role name {role_def.name} doesn't follow recommended naming conventions"
                )
            
            # Check for empty SQL commands
            if not role_def.sql_commands:
                validation_result["errors"].append(
                    f"Role {role_def.name} has no SQL commands"
                )
                validation_result["valid"] = False
            
            # Check for duplicate SQL commands
            if len(role_def.sql_commands) != len(set(role_def.sql_commands)):
                validation_result["warnings"].append(
                    f"Role {role_def.name} has duplicate SQL commands"
                )
            
            # Check version format
            if not cls._is_valid_version(role_def.version):
                validation_result["warnings"].append(
                    f"Role {role_def.name} version {role_def.version} doesn't follow semantic versioning"
                )
            
            logger.info(f"Role validation completed for {role_def.name}: {'PASS' if validation_result['valid'] else 'FAIL'}")
            
        except Exception as e:
            logger.error(f"Error validating role {role_def.name}: {e}")
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    @classmethod
    def _is_valid_role_name(cls, role_name: str) -> bool:
        """
        Check if role name follows recommended conventions.
        
        Args:
            role_name: Role name to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic checks
        if not role_name or len(role_name) < 3:
            return False
        
        # Check for valid characters (alphanumeric and underscore)
        if not role_name.replace('_', '').isalnum():
            return False
        
        # Check for recommended naming convention: {db}_{schema}_{role_type}
        # Allow various prefixes that follow the new convention
        recommended_patterns = [
            r'^[a-z]+_[a-z]+_(reader|writer|admin|monitor|analyst|data_scientist|audit|backup|analytics_readonly)$',
            r'^[a-z]+_monitor$',  # Database-wide monitor roles
            r'^[a-z]+_[a-z]+_[a-z_]+$'  # General pattern for custom roles
        ]
        
        import re
        if not any(re.match(pattern, role_name) for pattern in recommended_patterns):
            return False
        
        return True
    
    @classmethod
    def _is_valid_version(cls, version: str) -> bool:
        """
        Check if version follows semantic versioning.
        
        Args:
            version: Version string to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            parts = version.split('.')
            if len(parts) != 3:
                return False
            
            for part in parts:
                int(part)
            
            return True
        except (ValueError, AttributeError):
            return False
    
    @classmethod
    def validate_multiple_roles(cls, role_definitions: List[RoleDefinition]) -> Dict[str, Any]:
        """
        Validate multiple role definitions.
        
        Args:
            role_definitions: List of role definitions to validate
            
        Returns:
            Dictionary with overall validation results
        """
        overall_result = {
            "valid": True,
            "total_roles": len(role_definitions),
            "valid_roles": 0,
            "invalid_roles": 0,
            "role_results": {},
            "summary": {
                "errors": [],
                "warnings": []
            }
        }
        
        for role_def in role_definitions:
            role_result = cls.validate_role_definition(role_def)
            overall_result["role_results"][role_def.name] = role_result
            
            if role_result["valid"]:
                overall_result["valid_roles"] += 1
            else:
                overall_result["invalid_roles"] += 1
                overall_result["valid"] = False
            
            # Collect all errors and warnings
            overall_result["summary"]["errors"].extend(role_result["errors"])
            overall_result["summary"]["warnings"].extend(role_result["warnings"])
        
        logger.info(f"Multiple role validation completed: {overall_result['valid_roles']}/{overall_result['total_roles']} valid")
        
        return overall_result
    
    @classmethod
    def get_validation_summary(cls, validation_result: Dict[str, Any]) -> str:
        """
        Get a human-readable validation summary.
        
        Args:
            validation_result: Validation result dictionary
            
        Returns:
            Human-readable summary string
        """
        if validation_result["valid"]:
            return f"✅ Validation PASSED - {len(validation_result.get('warnings', []))} warnings"
        else:
            error_count = len(validation_result.get('errors', []))
            warning_count = len(validation_result.get('warnings', []))
            return f"❌ Validation FAILED - {error_count} errors, {warning_count} warnings"