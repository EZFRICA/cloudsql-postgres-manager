"""
Base response models for consistent API responses.

This module provides standardized response models to ensure
consistent API responses across all endpoints.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """
    Base response model for all API responses.

    Attributes:
        success: Whether the operation was successful
        message: Human-readable message describing the result
        timestamp: When the response was generated
        request_id: Optional request identifier for tracing
    """

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(
        ..., description="Human-readable message describing the result"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Response timestamp"
    )
    request_id: Optional[str] = Field(
        default=None, description="Request identifier for tracing"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SuccessResponse(BaseResponse):
    """
    Standardized success response model.

    Attributes:
        data: Optional data payload
        metadata: Optional metadata about the operation
    """

    data: Optional[Union[Dict[str, Any], List[Any]]] = Field(
        default=None, description="Optional data payload"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata about the operation"
    )

    @classmethod
    def create(
        cls,
        message: str = "Operation completed successfully",
        data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> "SuccessResponse":
        """Create a success response with the given parameters."""
        return cls(
            success=True,
            message=message,
            data=data,
            metadata=metadata,
            request_id=request_id,
        )


class ErrorResponse(BaseResponse):
    """
    Standardized error response model.

    Attributes:
        error: Error type or code
        details: Optional detailed error information
        error_code: Optional error code for programmatic handling
    """

    error: str = Field(..., description="Error type or code")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional detailed error information"
    )
    error_code: Optional[str] = Field(
        default=None, description="Optional error code for programmatic handling"
    )

    @classmethod
    def create(
        cls,
        error: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> "ErrorResponse":
        """Create an error response with the given parameters."""
        return cls(
            success=False,
            message=message,
            error=error,
            details=details,
            error_code=error_code,
            request_id=request_id,
        )


class ValidationErrorResponse(ErrorResponse):
    """Specialized error response for validation errors."""

    @classmethod
    def create(
        cls,
        validation_errors: List[Dict[str, Any]],
        message: str = "Validation failed",
        request_id: Optional[str] = None,
    ) -> "ValidationErrorResponse":
        """Create a validation error response."""
        return cls(
            success=False,
            message=message,
            error="validation_error",
            details={"validation_errors": validation_errors},
            error_code="VALIDATION_FAILED",
            request_id=request_id,
        )


class DatabaseErrorResponse(ErrorResponse):
    """Specialized error response for database errors."""

    @classmethod
    def create(
        cls, operation: str, error_message: str, request_id: Optional[str] = None
    ) -> "DatabaseErrorResponse":
        """Create a database error response."""
        return cls(
            success=False,
            message=f"Database operation '{operation}' failed",
            error="database_error",
            details={"operation": operation, "database_error": error_message},
            error_code="DATABASE_ERROR",
            request_id=request_id,
        )


class NotFoundErrorResponse(ErrorResponse):
    """Specialized error response for not found errors."""

    @classmethod
    def create(
        cls, resource_type: str, resource_id: str, request_id: Optional[str] = None
    ) -> "NotFoundErrorResponse":
        """Create a not found error response."""
        return cls(
            success=False,
            message=f"{resource_type} '{resource_id}' not found",
            error="not_found",
            details={"resource_type": resource_type, "resource_id": resource_id},
            error_code="NOT_FOUND",
            request_id=request_id,
        )
