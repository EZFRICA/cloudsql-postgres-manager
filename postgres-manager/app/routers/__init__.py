"""
Routers package for API endpoints.

This package contains all FastAPI router modules that define
the REST API endpoints.
"""

from .database import router as database_router
from .health import router as health_router
from .roles import router as roles_router
from .schemas import router as schemas_router

__all__ = ["database_router", "health_router", "roles_router", "schemas_router"]
