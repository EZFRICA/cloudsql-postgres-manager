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

Author: Bokove Ezekias
Version: 1.0.0
License: MIT
"""

__version__ = "0.1.0"
__author__ = "bokove@ezekias.dev"
__email__ = "bokove@ezekias.dev"
__license__ = "MIT"

# Package metadata
__title__ = "cloudsql-postgres-manager"
__description__ = "Comprehensive Cloud SQL PostgreSQL management with IAM integration"
__url__ = "https://github.com/EZFRICA/cloudsql-postgres-manager"

# Version info tuple
__version_info__ = tuple(int(i) for i in __version__.split("."))

# Import key components for easy access
from .config import get_database_config, get_firestore_config
from .main import app

# Core services
from .services import (
    ConnectionManager,
    UserManager,
    SchemaManager,
    RolePermissionManager,
    RoleManager,
    FirestoreRoleRegistryManager,
    HealthManager,
    DatabaseValidator,
)

# Models
from .models import (
    RoleInitializeRequest,
    RoleInitializeResponse,
    HealthResponse,
    ErrorResponse,
)

# Utilities
from .utils import logger, PostgreSQLValidator

# Plugin system
from .plugins import PluginRegistry, RoleDefinition, RolePlugin

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
    "HealthManager",
    "DatabaseValidator",
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
