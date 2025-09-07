"""
Base classes for role plugin system.

This module defines the abstract base classes and interfaces
for creating customizable role definitions.
"""

import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class RoleDefinition(BaseModel):
    """
    Model representing a role definition with versioning and checksum.
    
    Attributes:
        name: Role name
        version: Semantic version (e.g., "1.0.0")
        checksum: SHA256 hash of SQL commands for integrity verification
        sql_commands: List of SQL commands to create/configure the role
        inherits: List of roles this role inherits from
        native_roles: List of PostgreSQL native roles granted
        description: Human-readable description of the role
        created_at: Timestamp when definition was created
        status: Current status (active, deprecated, etc.)
    """
    
    name: str = Field(..., description="Role name")
    version: str = Field(..., description="Semantic version (e.g., 1.0.0)")
    checksum: str = Field(..., description="SHA256 hash of SQL commands")
    sql_commands: List[str] = Field(..., description="SQL commands to execute")
    inherits: List[str] = Field(default=[], description="Roles this role inherits from")
    native_roles: List[str] = Field(default=[], description="PostgreSQL native roles granted")
    description: str = Field(default="", description="Role description")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    status: str = Field(default="active", description="Role status")
    
    def calculate_checksum(self) -> str:
        """Calculate SHA256 checksum of SQL commands."""
        content = "\n".join(sorted(self.sql_commands))
        return hashlib.sha256(content.encode()).hexdigest()
    
    def is_outdated(self, other: "RoleDefinition") -> bool:
        """Check if this definition is outdated compared to another."""
        return (self.version != other.version or 
                self.checksum != other.checksum)


class RolePlugin(ABC):
    """
    Abstract base class for role definition plugins.
    
    Plugins allow developers to define custom role configurations
    that can be loaded dynamically by the role management system.
    """
    
    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Return the plugin name."""
        pass
    
    @property
    @abstractmethod
    def plugin_version(self) -> str:
        """Return the plugin version."""
        pass
    
    @abstractmethod
    def get_role_definitions(self) -> List[RoleDefinition]:
        """
        Return the list of role definitions provided by this plugin.
        
        Returns:
            List of RoleDefinition objects
        """
        pass
    
    def validate_role_definition(self, role_def: RoleDefinition) -> bool:
        """
        Validate a role definition for dangerous permissions.
        
        This method provides basic validation to prevent creation of
        roles with dangerous permissions. Can be overridden for custom validation.
        
        Args:
            role_def: Role definition to validate
            
        Returns:
            True if valid, False if dangerous permissions detected
        """
        dangerous_permissions = [
            "SUPERUSER",
            "CREATEDB", 
            "CREATEROLE",
            "REPLICATION"
        ]
        
        for command in role_def.sql_commands:
            command_upper = command.upper()
            for perm in dangerous_permissions:
                if perm in command_upper:
                    return False
        return True
    
    def get_plugin_metadata(self) -> Dict[str, Any]:
        """
        Return plugin metadata.
        
        Returns:
            Dictionary containing plugin information
        """
        return {
            "name": self.plugin_name,
            "version": self.plugin_version,
            "role_count": len(self.get_role_definitions())
        }
