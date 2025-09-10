"""
Core package for application configuration and setup.

This package contains core configuration classes and application setup
logic for the Cloud SQL PostgreSQL Manager.
"""

from .app_config import create_app

__all__ = ["create_app"]
