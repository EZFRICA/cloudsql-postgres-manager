"""
Reusable error handling components.

This module provides standardized error handling utilities
to reduce code duplication and improve consistency.
"""

from typing import Any, Dict, Optional, Union, Callable
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from app.components.base_responses import (
    ErrorResponse,
    ValidationErrorResponse,
    DatabaseErrorResponse,
    NotFoundErrorResponse,
)
from app.utils.logging_config import logger


class ErrorHandler:
    """
    Reusable error handler with standardized error processing.

    This class provides consistent error handling patterns
    for different types of errors throughout the application.
    """

    @staticmethod
    def handle_validation_error(
        error: ValidationError, request: Optional[Request] = None
    ) -> JSONResponse:
        """
        Handle Pydantic validation errors.

        Args:
            error: ValidationError instance
            request: Optional FastAPI request for context

        Returns:
            JSONResponse with validation error details
        """
        request_id = (
            getattr(request, "state", {}).get("request_id") if request else None
        )

        # Extract validation errors
        validation_errors = []
        for err in error.errors():
            validation_errors.append(
                {
                    "field": ".".join(str(x) for x in err["loc"]),
                    "message": err["msg"],
                    "type": err["type"],
                    "input": err.get("input"),
                }
            )

        error_response = ValidationErrorResponse.create(
            validation_errors=validation_errors, request_id=request_id
        )

        logger.warning(
            f"Validation error: {len(validation_errors)} field(s) failed validation"
        )

        return JSONResponse(status_code=422, content=error_response.dict())

    @staticmethod
    def handle_database_error(
        operation: str, error: Union[str, Exception], request: Optional[Request] = None
    ) -> JSONResponse:
        """
        Handle database operation errors.

        Args:
            operation: Database operation that failed
            error: Error message or exception
            request: Optional FastAPI request for context

        Returns:
            JSONResponse with database error details
        """
        request_id = (
            getattr(request, "state", {}).get("request_id") if request else None
        )

        error_message = str(error) if isinstance(error, Exception) else error

        error_response = DatabaseErrorResponse.create(
            operation=operation, error_message=error_message, request_id=request_id
        )

        logger.error(f"Database error in {operation}: {error_message}")

        return JSONResponse(status_code=500, content=error_response.dict())

    @staticmethod
    def handle_not_found_error(
        resource_type: str, resource_id: str, request: Optional[Request] = None
    ) -> JSONResponse:
        """
        Handle resource not found errors.

        Args:
            resource_type: Type of resource not found
            resource_id: ID of the resource not found
            request: Optional FastAPI request for context

        Returns:
            JSONResponse with not found error details
        """
        request_id = (
            getattr(request, "state", {}).get("request_id") if request else None
        )

        error_response = NotFoundErrorResponse.create(
            resource_type=resource_type, resource_id=resource_id, request_id=request_id
        )

        logger.warning(f"Resource not found: {resource_type} '{resource_id}'")

        return JSONResponse(status_code=404, content=error_response.dict())

    @staticmethod
    def handle_permission_error(
        user: str, resource: str, action: str, request: Optional[Request] = None
    ) -> JSONResponse:
        """
        Handle permission denied errors.

        Args:
            user: User who was denied access
            resource: Resource access was denied to
            action: Action that was denied
            request: Optional FastAPI request for context

        Returns:
            JSONResponse with permission error details
        """
        request_id = (
            getattr(request, "state", {}).get("request_id") if request else None
        )

        error_response = ErrorResponse.create(
            error="permission_denied",
            message=f"Access denied to {resource} for action {action}",
            details={"user": user, "resource": resource, "action": action},
            error_code="PERMISSION_DENIED",
            request_id=request_id,
        )

        logger.warning(f"Permission denied: {user} -> {resource} ({action})")

        return JSONResponse(status_code=403, content=error_response.dict())

    @staticmethod
    def handle_business_logic_error(
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> JSONResponse:
        """
        Handle business logic errors.

        Args:
            error_code: Business logic error code
            message: Human-readable error message
            details: Optional additional error details
            request: Optional FastAPI request for context

        Returns:
            JSONResponse with business logic error details
        """
        request_id = (
            getattr(request, "state", {}).get("request_id") if request else None
        )

        error_response = ErrorResponse.create(
            error=error_code,
            message=message,
            details=details,
            error_code=error_code.upper(),
            request_id=request_id,
        )

        logger.warning(f"Business logic error: {error_code} - {message}")

        return JSONResponse(status_code=400, content=error_response.dict())

    @staticmethod
    def handle_internal_error(
        error: Union[str, Exception], request: Optional[Request] = None
    ) -> JSONResponse:
        """
        Handle internal server errors.

        Args:
            error: Error message or exception
            request: Optional FastAPI request for context

        Returns:
            JSONResponse with internal error details
        """
        request_id = (
            getattr(request, "state", {}).get("request_id") if request else None
        )

        error_message = str(error) if isinstance(error, Exception) else error

        error_response = ErrorResponse.create(
            error="internal_error",
            message="An internal server error occurred",
            details={"error": error_message},
            error_code="INTERNAL_ERROR",
            request_id=request_id,
        )

        logger.error(f"Internal server error: {error_message}")

        return JSONResponse(status_code=500, content=error_response.dict())

    @staticmethod
    def create_http_exception(
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> HTTPException:
        """
        Create a standardized HTTPException.

        Args:
            status_code: HTTP status code
            error_code: Application error code
            message: Human-readable error message
            details: Optional additional error details

        Returns:
            HTTPException with standardized format
        """
        error_data = {"error": error_code, "message": message}

        if details:
            error_data["details"] = details

        return HTTPException(status_code=status_code, detail=error_data)


def handle_errors(func: Callable) -> Callable:
    """
    Decorator to handle common errors in endpoint functions.

    Args:
        func: Function to wrap with error handling

    Returns:
        Wrapped function with error handling
    """

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValidationError as e:
            # Extract request from kwargs if available
            request = kwargs.get("request")
            return ErrorHandler.handle_validation_error(e, request)
        except HTTPException:
            # Re-raise HTTPExceptions as they are already handled
            raise
        except Exception as e:
            # Handle unexpected errors
            request = kwargs.get("request")
            return ErrorHandler.handle_internal_error(e, request)

    return wrapper


class ErrorContext:
    """
    Context manager for error handling with automatic logging.
    """

    def __init__(
        self,
        operation: str,
        request: Optional[Request] = None,
        raise_on_error: bool = True,
    ):
        self.operation = operation
        self.request = request
        self.raise_on_error = raise_on_error
        self.request_id = (
            getattr(request, "state", {}).get("request_id") if request else None
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if exc_type == ValidationError:
                logger.warning(f"Validation error in {self.operation}: {exc_val}")
            elif exc_type == HTTPException:
                logger.warning(f"HTTP error in {self.operation}: {exc_val.detail}")
            else:
                logger.error(f"Unexpected error in {self.operation}: {exc_val}")

            if self.raise_on_error:
                return False  # Re-raise the exception
            else:
                return True  # Suppress the exception

        return False
