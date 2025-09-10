"""
Error handlers for FastAPI application.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, NotFound
from ..models import ErrorResponse


def register_error_handlers(app):
    """Register all error handlers with the FastAPI app."""

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        """Handler for 404 errors"""
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(error="Endpoint not found").model_dump(),
        )

    @app.exception_handler(405)
    async def method_not_allowed_handler(request: Request, exc):
        """Handler for 405 errors"""
        return JSONResponse(
            status_code=405,
            content=ErrorResponse(error="Method not allowed").model_dump(),
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        """Handler for Pydantic validation errors"""
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="Validation error", details={"validation_errors": exc.errors()}
            ).model_dump(),
        )

    @app.exception_handler(GoogleAPICallError)
    async def google_api_error_handler(request: Request, exc: GoogleAPICallError):
        """Handler for Google API errors"""
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Google API error", details={"message": str(exc)}
            ).model_dump(),
        )

    @app.exception_handler(PermissionDenied)
    async def permission_denied_handler(request: Request, exc: PermissionDenied):
        """Handler for permission denied errors"""
        return JSONResponse(
            status_code=403,
            content=ErrorResponse(
                error="Permission denied", details={"message": str(exc)}
            ).model_dump(),
        )

    @app.exception_handler(NotFound)
    async def resource_not_found_handler(request: Request, exc: NotFound):
        """Handler for resource not found errors"""
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="Resource not found", details={"message": str(exc)}
            ).model_dump(),
        )
