"""
Error handlers for FastAPI application.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from app.models import ErrorResponse


def register_error_handlers(app):
    """Register all error handlers with the FastAPI app."""
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        """Handler for 404 errors"""
        return JSONResponse(
            status_code=404, content=ErrorResponse(error="Endpoint not found").dict()
        )

    @app.exception_handler(405)
    async def method_not_allowed_handler(request: Request, exc):
        """Handler for 405 errors"""
        return JSONResponse(
            status_code=405, content=ErrorResponse(error="Method not allowed").dict()
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        """Handler for Pydantic validation errors"""
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="Validation error", details={"validation_errors": exc.errors()}
            ).dict(),
        )