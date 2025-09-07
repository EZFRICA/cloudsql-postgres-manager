"""
Reusable validation helper components.

This module provides standardized validation utilities
to reduce code duplication and improve consistency.
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Union
from email.utils import parseaddr


class ValidationHelper:
    """
    Reusable validation helper with common validation patterns.
    
    This class provides standardized validation methods
    for common data types and patterns used throughout the application.
    """
    
    # Common regex patterns
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    SERVICE_ACCOUNT_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.iam\.gserviceaccount\.com$')
    PROJECT_ID_PATTERN = re.compile(r'^[a-z][a-z0-9-]{4,28}[a-z0-9]$')
    INSTANCE_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9-]{1,61}[a-z0-9]$')
    DATABASE_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,62}$')
    SCHEMA_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,62}$')
    ROLE_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,62}$')
    
    @classmethod
    def validate_email(cls, email: str) -> Tuple[bool, str]:
        """
        Validate email address format.
        
        Args:
            email: Email address to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email or not isinstance(email, str):
            return False, "Email is required and must be a string"
        
        email = email.strip()
        if not email:
            return False, "Email cannot be empty"
        
        if not cls.EMAIL_PATTERN.match(email):
            return False, "Invalid email format"
        
        return True, ""
    
    @classmethod
    def validate_service_account_email(cls, email: str) -> Tuple[bool, str]:
        """
        Validate Google Cloud service account email format.
        
        Args:
            email: Service account email to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email or not isinstance(email, str):
            return False, "Service account email is required and must be a string"
        
        email = email.strip()
        if not email:
            return False, "Service account email cannot be empty"
        
        if not cls.SERVICE_ACCOUNT_PATTERN.match(email):
            return False, "Invalid service account email format. Must end with .iam.gserviceaccount.com"
        
        return True, ""
    
    @classmethod
    def validate_project_id(cls, project_id: str) -> Tuple[bool, str]:
        """
        Validate Google Cloud project ID format.
        
        Args:
            project_id: Project ID to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not project_id or not isinstance(project_id, str):
            return False, "Project ID is required and must be a string"
        
        project_id = project_id.strip()
        if not project_id:
            return False, "Project ID cannot be empty"
        
        if not cls.PROJECT_ID_PATTERN.match(project_id):
            return False, "Invalid project ID format. Must be 6-30 characters, start with letter, contain only lowercase letters, numbers, and hyphens"
        
        return True, ""
    
    @classmethod
    def validate_instance_name(cls, instance_name: str) -> Tuple[bool, str]:
        """
        Validate Cloud SQL instance name format.
        
        Args:
            instance_name: Instance name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not instance_name or not isinstance(instance_name, str):
            return False, "Instance name is required and must be a string"
        
        instance_name = instance_name.strip()
        if not instance_name:
            return False, "Instance name cannot be empty"
        
        if not cls.INSTANCE_NAME_PATTERN.match(instance_name):
            return False, "Invalid instance name format. Must be 3-63 characters, start with letter, contain only lowercase letters, numbers, and hyphens"
        
        return True, ""
    
    @classmethod
    def validate_database_name(cls, database_name: str) -> Tuple[bool, str]:
        """
        Validate database name format.
        
        Args:
            database_name: Database name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not database_name or not isinstance(database_name, str):
            return False, "Database name is required and must be a string"
        
        database_name = database_name.strip()
        if not database_name:
            return False, "Database name cannot be empty"
        
        if not cls.DATABASE_NAME_PATTERN.match(database_name):
            return False, "Invalid database name format. Must start with letter or underscore, contain only letters, numbers, and underscores"
        
        return True, ""
    
    @classmethod
    def validate_schema_name(cls, schema_name: str) -> Tuple[bool, str]:
        """
        Validate schema name format.
        
        Args:
            schema_name: Schema name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not schema_name or not isinstance(schema_name, str):
            return False, "Schema name is required and must be a string"
        
        schema_name = schema_name.strip()
        if not schema_name:
            return False, "Schema name cannot be empty"
        
        if not cls.SCHEMA_NAME_PATTERN.match(schema_name):
            return False, "Invalid schema name format. Must start with letter or underscore, contain only letters, numbers, and underscores"
        
        return True, ""
    
    @classmethod
    def validate_role_name(cls, role_name: str) -> Tuple[bool, str]:
        """
        Validate role name format.
        
        Args:
            role_name: Role name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not role_name or not isinstance(role_name, str):
            return False, "Role name is required and must be a string"
        
        role_name = role_name.strip()
        if not role_name:
            return False, "Role name cannot be empty"
        
        if not cls.ROLE_NAME_PATTERN.match(role_name):
            return False, "Invalid role name format. Must start with letter or underscore, contain only letters, numbers, and underscores"
        
        return True, ""
    
    @classmethod
    def validate_permission_role(cls, permission_role: str) -> Tuple[bool, str]:
        """
        Validate permission role type.
        
        Args:
            permission_role: Role type to validate (e.g., reader, writer, admin)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not permission_role or not isinstance(permission_role, str):
            return False, "Permission role is required and must be a string"
        
        permission_role = permission_role.strip().lower()
        
        valid_role_types = ["reader", "writer", "admin", "analyst", "monitor"]
        if permission_role not in valid_role_types:
            return False, f"Invalid role type '{permission_role}'. Must be one of: {', '.join(valid_role_types)}"
        
        return True, ""
    
    @classmethod
    def validate_region(cls, region: str, allowed_regions: List[str]) -> Tuple[bool, str]:
        """
        Validate GCP region.
        
        Args:
            region: Region to validate
            allowed_regions: List of allowed regions
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not region or not isinstance(region, str):
            return False, "Region is required and must be a string"
        
        region = region.strip()
        if not region:
            return False, "Region cannot be empty"
        
        if region not in allowed_regions:
            return False, f"Region '{region}' is not allowed. Allowed regions: {', '.join(allowed_regions)}"
        
        return True, ""
    
    @classmethod
    def validate_iam_users(cls, iam_users: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        Validate list of IAM users.
        
        Args:
            iam_users: List of IAM user dictionaries
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if not isinstance(iam_users, list):
            return False, ["iam_users must be a list"]
        
        errors = []
        
        for i, user in enumerate(iam_users):
            if not isinstance(user, dict):
                errors.append(f"User at index {i} must be a dictionary")
                continue
            
            # Validate name
            name = user.get("name")
            if not name:
                errors.append(f"User at index {i} missing 'name' field")
            else:
                is_valid, error = cls.validate_service_account_email(name)
                if not is_valid:
                    errors.append(f"User at index {i}: {error}")
            
            # Validate permission role
            permission_role = user.get("permission_role", "reader")
            is_valid, error = cls.validate_permission_role(permission_role)
            if not is_valid:
                errors.append(f"User at index {i}: {error}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_request_data(
        cls,
        data: Dict[str, Any],
        required_fields: List[str],
        optional_fields: Optional[List[str]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate request data structure.
        
        Args:
            data: Data dictionary to validate
            required_fields: List of required field names
            optional_fields: List of optional field names
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if not isinstance(data, dict):
            return False, ["Data must be a dictionary"]
        
        errors = []
        
        # Check required fields
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Required field '{field}' is missing")
        
        # Check for unknown fields
        all_fields = set(required_fields)
        if optional_fields:
            all_fields.update(optional_fields)
        
        for field in data.keys():
            if field not in all_fields:
                errors.append(f"Unknown field '{field}'")
        
        return len(errors) == 0, errors
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize string input by trimming and optionally limiting length.
        
        Args:
            value: String to sanitize
            max_length: Optional maximum length
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value) if value is not None else ""
        
        sanitized = value.strip()
        
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized