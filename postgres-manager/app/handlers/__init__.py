"""
Handlers package for error handling and request processing.

This package contains error handlers and request processing logic
for the Cloud SQL PostgreSQL Manager.
"""

from .error_handlers import register_error_handlers

__all__ = ["register_error_handlers"]
