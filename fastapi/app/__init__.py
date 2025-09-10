# FastAPI application package
"""
Cloud SQL PostgreSQL Manager - FastAPI Application

A comprehensive solution for automating Google Cloud SQL PostgreSQL database
management and IAM user permissions across multiple databases in an organization.

This package provides:
- Automated IAM user permission management
- Role-based access control with plugin system
- Schema and database operations
- Integration with Google Cloud services
- RESTful API for database operations
- Pub/Sub event handling

Author: Your Organization
Version: 1.0.0
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Your Organization"
__email__ = "contact@yourorg.com"
__license__ = "MIT"

# Package metadata
__title__ = "cloudsql-postgres-manager"
__description__ = "Comprehensive Cloud SQL PostgreSQL management with IAM integration"
__url__ = "https://github.com/yourorg/cloudsql-postgres-manager"

# Version info tuple
__version_info__ = tuple(int(i) for i in __version__.split("."))

# Import key components for easy access
from .config import get_database_config, get_firestore_config
from .main import app

# Core services
from .services.connection_manager import ConnectionManager
from .services.user_manager import UserManager
from .services.schema_manager import SchemaManager
from .services.role_permission_manager import RolePermissionManager
from .services.role_manager import RoleManager
from .services.firebase import FirestoreRoleRegistryManager

# Models
from .models import (
    RoleInitializeRequest,
    RoleInitializeResponse,
    HealthResponse,
    ErrorResponse,
)

# Utilities
from .utils.logging_config import logger
from .utils.role_validation import PostgreSQLValidator

# Plugin system
from .plugins.registry import PluginRegistry
from .plugins.base import RoleDefinition, RolePlugin

# Export all public components
__all__ = [
    # Metadata
    "__version__",
    "__author__",
    "__title__",
    "__description__",
    # Core application
    "app",
    # Configuration
    "get_database_config",
    "get_firestore_config",
    # Services
    "ConnectionManager",
    "UserManager",
    "SchemaManager",
    "RolePermissionManager",
    "RoleManager",
    "FirestoreRoleRegistryManager",
    # Models
    "RoleInitializeRequest",
    "RoleInitializeResponse",
    "HealthResponse",
    "ErrorResponse",
    # Utilities
    "logger",
    "PostgreSQLValidator",
    # Plugin system
    "PluginRegistry",
    "RoleDefinition",
    "RolePlugin",
]


# Package initialization
def get_version():
    """Get the current version of the package."""
    return __version__


def get_package_info():
    """Get comprehensive package information."""
    return {
        "name": __title__,
        "version": __version__,
        "description": __description__,
        "author": __author__,
        "license": __license__,
        "url": __url__,
    }


# Initialize logging on package import
logger.info(f"Initializing {__title__} v{__version__}")
