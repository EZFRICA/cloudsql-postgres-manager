"""
Main FastAPI application entry point.

This module creates and configures the FastAPI application with all routers and handlers.
"""

from fastapi import FastAPI
from .core.app_config import create_app
from .handlers.error_handlers import register_error_handlers
from .routers import health, roles, schemas, database


def create_application() -> FastAPI:
    """Create and configure the FastAPI application with all components."""

    # Create the base app
    app = create_app()

    # Register error handlers
    register_error_handlers(app)

    # Include routers
    app.include_router(health.router)
    app.include_router(roles.router)
    app.include_router(schemas.router)
    app.include_router(database.router)

    return app


# Create the application instance
app = create_application()
