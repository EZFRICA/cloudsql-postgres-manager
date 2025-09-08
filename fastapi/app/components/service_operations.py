"""
Reusable service operation components.

This module provides standardized service operation patterns
to reduce code duplication and improve consistency.
"""

import time
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass
from app.components.base_responses import BaseResponse, SuccessResponse, ErrorResponse
from app.components.logging_helpers import LoggingHelper
from app.components.error_handlers import ErrorHandler


@dataclass
class ServiceOperationResult:
    """
    Standardized result for service operations.

    Attributes:
        success: Whether the operation was successful
        data: Result data from the operation
        message: Human-readable message
        execution_time: Time taken to execute the operation
        error: Error message if operation failed
        metadata: Optional metadata about the operation
    """

    success: bool
    data: Optional[Any] = None
    message: str = ""
    execution_time: float = 0.0
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "execution_time": self.execution_time,
            "error": self.error,
            "metadata": self.metadata,
        }

    def to_response(self, request_id: Optional[str] = None) -> BaseResponse:
        """Convert to API response model."""
        if self.success:
            return SuccessResponse.create(
                message=self.message,
                data=self.data,
                metadata=self.metadata,
                request_id=request_id,
            )
        else:
            return ErrorResponse.create(
                error="service_error",
                message=self.message or "Service operation failed",
                details={"error": self.error} if self.error else None,
                request_id=request_id,
            )


class ServiceOperation:
    """
    Reusable service operation component with standardized patterns.

    This class provides a consistent interface for service operations
    with automatic error handling, logging, and performance monitoring.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name

    def execute(
        self,
        operation: str,
        func: Callable,
        *args,
        request_id: Optional[str] = None,
        **kwargs,
    ) -> ServiceOperationResult:
        """
        Execute a service operation with standardized error handling.

        Args:
            operation: Name of the operation
            func: Function to execute
            *args: Positional arguments for the function
            request_id: Optional request ID for tracing
            **kwargs: Keyword arguments for the function

        Returns:
            ServiceOperationResult with operation details
        """
        start_time = time.time()

        # Generate request ID if not provided
        if not request_id:
            request_id = LoggingHelper.log_operation_start(
                f"{self.service_name}.{operation}", request_id=request_id
            )

        try:
            # Execute the function
            result = func(*args, **kwargs)

            execution_time = time.time() - start_time

            # Log success
            LoggingHelper.log_operation_success(
                f"{self.service_name}.{operation}", request_id, execution_time
            )

            return ServiceOperationResult(
                success=True,
                data=result,
                message=f"{operation} completed successfully",
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)

            # Log error
            LoggingHelper.log_operation_error(
                f"{self.service_name}.{operation}", request_id, e, execution_time
            )

            return ServiceOperationResult(
                success=False,
                message=f"{operation} failed",
                execution_time=execution_time,
                error=error_message,
            )

    def execute_with_validation(
        self,
        operation: str,
        func: Callable,
        validator: Callable,
        *args,
        request_id: Optional[str] = None,
        **kwargs,
    ) -> ServiceOperationResult:
        """
        Execute a service operation with input validation.

        Args:
            operation: Name of the operation
            func: Function to execute
            validator: Validation function
            *args: Positional arguments for the function
            request_id: Optional request ID for tracing
            **kwargs: Keyword arguments for the function

        Returns:
            ServiceOperationResult with operation details
        """
        start_time = time.time()

        if not request_id:
            request_id = LoggingHelper.log_operation_start(
                f"{self.service_name}.{operation}", request_id=request_id
            )

        try:
            # Validate inputs
            validation_result = validator(*args, **kwargs)
            if not validation_result[
                0
            ]:  # Assuming validator returns (is_valid, error_message)
                return ServiceOperationResult(
                    success=False,
                    message="Validation failed",
                    execution_time=time.time() - start_time,
                    error=validation_result[1],
                )

            # Execute the function
            result = func(*args, **kwargs)

            execution_time = time.time() - start_time

            LoggingHelper.log_operation_success(
                f"{self.service_name}.{operation}", request_id, execution_time
            )

            return ServiceOperationResult(
                success=True,
                data=result,
                message=f"{operation} completed successfully",
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)

            LoggingHelper.log_operation_error(
                f"{self.service_name}.{operation}", request_id, e, execution_time
            )

            return ServiceOperationResult(
                success=False,
                message=f"{operation} failed",
                execution_time=execution_time,
                error=error_message,
            )

    def execute_batch(
        self,
        operation: str,
        operations: List[Callable],
        *args,
        request_id: Optional[str] = None,
        **kwargs,
    ) -> ServiceOperationResult:
        """
        Execute multiple operations in batch.

        Args:
            operation: Name of the batch operation
            operations: List of functions to execute
            *args: Positional arguments for the functions
            request_id: Optional request ID for tracing
            **kwargs: Keyword arguments for the functions

        Returns:
            ServiceOperationResult with batch operation details
        """
        start_time = time.time()

        if not request_id:
            request_id = LoggingHelper.log_operation_start(
                f"{self.service_name}.{operation}", request_id=request_id
            )

        results = []
        errors = []

        try:
            for i, func in enumerate(operations):
                try:
                    result = func(*args, **kwargs)
                    results.append({"index": i, "success": True, "result": result})
                except Exception as e:
                    error_msg = str(e)
                    errors.append({"index": i, "error": error_msg})
                    results.append({"index": i, "success": False, "error": error_msg})

            execution_time = time.time() - start_time

            # Determine overall success
            success_count = sum(1 for r in results if r["success"])
            total_count = len(results)

            if success_count == total_count:
                LoggingHelper.log_operation_success(
                    f"{self.service_name}.{operation}",
                    request_id,
                    execution_time,
                    {"operations_completed": total_count},
                )

                return ServiceOperationResult(
                    success=True,
                    data=results,
                    message=f"Batch {operation} completed successfully ({success_count}/{total_count})",
                    execution_time=execution_time,
                    metadata={
                        "total_operations": total_count,
                        "successful_operations": success_count,
                        "failed_operations": total_count - success_count,
                    },
                )
            else:
                LoggingHelper.log_operation_error(
                    f"{self.service_name}.{operation}",
                    request_id,
                    f"Batch operation failed: {len(errors)} errors out of {total_count} operations",
                    execution_time,
                )

                return ServiceOperationResult(
                    success=False,
                    data=results,
                    message=f"Batch {operation} completed with errors ({success_count}/{total_count})",
                    execution_time=execution_time,
                    error=f"{len(errors)} operations failed",
                    metadata={
                        "total_operations": total_count,
                        "successful_operations": success_count,
                        "failed_operations": total_count - success_count,
                        "errors": errors,
                    },
                )

        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)

            LoggingHelper.log_operation_error(
                f"{self.service_name}.{operation}", request_id, e, execution_time
            )

            return ServiceOperationResult(
                success=False,
                message=f"Batch {operation} failed",
                execution_time=execution_time,
                error=error_message,
            )


class ServiceManager:
    """
    Base class for service managers with common patterns.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.operation_handler = ServiceOperation(service_name)

    def _execute_operation(
        self,
        operation: str,
        func: Callable,
        *args,
        request_id: Optional[str] = None,
        **kwargs,
    ) -> ServiceOperationResult:
        """Execute an operation using the service operation handler."""
        return self.operation_handler.execute(
            operation, func, *args, request_id=request_id, **kwargs
        )

    def _execute_with_validation(
        self,
        operation: str,
        func: Callable,
        validator: Callable,
        *args,
        request_id: Optional[str] = None,
        **kwargs,
    ) -> ServiceOperationResult:
        """Execute an operation with validation using the service operation handler."""
        return self.operation_handler.execute_with_validation(
            operation, func, validator, *args, request_id=request_id, **kwargs
        )

    def _execute_batch(
        self,
        operation: str,
        operations: List[Callable],
        *args,
        request_id: Optional[str] = None,
        **kwargs,
    ) -> ServiceOperationResult:
        """Execute batch operations using the service operation handler."""
        return self.operation_handler.execute_batch(
            operation, operations, *args, request_id=request_id, **kwargs
        )
