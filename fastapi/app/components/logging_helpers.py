"""
Reusable logging helper components.

This module provides standardized logging utilities
to reduce code duplication and improve consistency.
"""

import time
import uuid
from typing import Any, Dict, Optional, Union
from functools import wraps
from contextlib import contextmanager
from app.utils.logging_config import logger


class LoggingHelper:
    """
    Reusable logging helper with common logging patterns.
    
    This class provides standardized logging methods
    for common operations and patterns used throughout the application.
    """
    
    @staticmethod
    def log_operation_start(
        operation: str,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> str:
        """
        Log the start of an operation.
        
        Args:
            operation: Name of the operation
            details: Optional details about the operation
            request_id: Optional request ID for tracing
            
        Returns:
            Generated request ID if none provided
        """
        if not request_id:
            request_id = str(uuid.uuid4())
        
        log_data = {
            "operation": operation,
            "request_id": request_id,
            "status": "started"
        }
        
        if details:
            log_data.update(details)
        
        logger.info(f"Operation started: {operation}", extra=log_data)
        return request_id
    
    @staticmethod
    def log_operation_success(
        operation: str,
        request_id: str,
        execution_time: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log the successful completion of an operation.
        
        Args:
            operation: Name of the operation
            request_id: Request ID for tracing
            execution_time: Optional execution time in seconds
            details: Optional details about the operation
        """
        log_data = {
            "operation": operation,
            "request_id": request_id,
            "status": "success"
        }
        
        if execution_time is not None:
            log_data["execution_time"] = execution_time
        
        if details:
            log_data.update(details)
        
        logger.info(f"Operation completed successfully: {operation}", extra=log_data)
    
    @staticmethod
    def log_operation_error(
        operation: str,
        request_id: str,
        error: Union[str, Exception],
        execution_time: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an operation error.
        
        Args:
            operation: Name of the operation
            request_id: Request ID for tracing
            error: Error message or exception
            execution_time: Optional execution time in seconds
            details: Optional details about the operation
        """
        log_data = {
            "operation": operation,
            "request_id": request_id,
            "status": "error"
        }
        
        if execution_time is not None:
            log_data["execution_time"] = execution_time
        
        if details:
            log_data.update(details)
        
        error_message = str(error) if isinstance(error, Exception) else error
        logger.error(f"Operation failed: {operation} - {error_message}", extra=log_data)
    
    @staticmethod
    def log_database_operation(
        operation: str,
        table: Optional[str] = None,
        query: Optional[str] = None,
        rows_affected: Optional[int] = None,
        execution_time: Optional[float] = None,
        request_id: Optional[str] = None
    ) -> None:
        """
        Log a database operation.
        
        Args:
            operation: Database operation type (SELECT, INSERT, UPDATE, DELETE, etc.)
            table: Optional table name
            query: Optional query string (truncated for security)
            rows_affected: Optional number of rows affected
            execution_time: Optional execution time in seconds
            request_id: Optional request ID for tracing
        """
        log_data = {
            "operation": "database",
            "db_operation": operation,
            "request_id": request_id
        }
        
        if table:
            log_data["table"] = table
        
        if query:
            # Truncate query for security
            log_data["query"] = query[:100] + "..." if len(query) > 100 else query
        
        if rows_affected is not None:
            log_data["rows_affected"] = rows_affected
        
        if execution_time is not None:
            log_data["execution_time"] = execution_time
        
        logger.info(f"Database operation: {operation}", extra=log_data)
    
    @staticmethod
    def log_security_event(
        event_type: str,
        user: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> None:
        """
        Log a security-related event.
        
        Args:
            event_type: Type of security event
            user: Optional user involved
            resource: Optional resource affected
            action: Optional action taken
            details: Optional additional details
            request_id: Optional request ID for tracing
        """
        log_data = {
            "operation": "security",
            "event_type": event_type,
            "request_id": request_id
        }
        
        if user:
            log_data["user"] = user
        
        if resource:
            log_data["resource"] = resource
        
        if action:
            log_data["action"] = action
        
        if details:
            log_data.update(details)
        
        logger.warning(f"Security event: {event_type}", extra=log_data)
    
    @staticmethod
    def log_performance_metric(
        metric_name: str,
        value: Union[int, float],
        unit: str = "ms",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> None:
        """
        Log a performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
            details: Optional additional details
            request_id: Optional request ID for tracing
        """
        log_data = {
            "operation": "performance",
            "metric_name": metric_name,
            "value": value,
            "unit": unit,
            "request_id": request_id
        }
        
        if details:
            log_data.update(details)
        
        logger.info(f"Performance metric: {metric_name}={value}{unit}", extra=log_data)


def log_execution_time(operation_name: str):
    """
    Decorator to log execution time of a function.
    
    Args:
        operation_name: Name of the operation for logging
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request_id = str(uuid.uuid4())
            start_time = time.time()
            
            LoggingHelper.log_operation_start(operation_name, request_id=request_id)
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                LoggingHelper.log_operation_success(
                    operation_name, request_id, execution_time
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                LoggingHelper.log_operation_error(
                    operation_name, request_id, e, execution_time
                )
                raise
        
        return wrapper
    return decorator


@contextmanager
def log_operation_context(operation_name: str, request_id: Optional[str] = None):
    """
    Context manager to log operation start and end.
    
    Args:
        operation_name: Name of the operation
        request_id: Optional request ID for tracing
    """
    if not request_id:
        request_id = str(uuid.uuid4())
    
    start_time = time.time()
    LoggingHelper.log_operation_start(operation_name, request_id=request_id)
    
    try:
        yield request_id
        execution_time = time.time() - start_time
        LoggingHelper.log_operation_success(operation_name, request_id, execution_time)
    except Exception as e:
        execution_time = time.time() - start_time
        LoggingHelper.log_operation_error(operation_name, request_id, e, execution_time)
        raise


class RequestLogger:
    """
    Request-specific logger for tracking operations within a single request.
    """
    
    def __init__(self, request_id: Optional[str] = None):
        self.request_id = request_id or str(uuid.uuid4())
        self.start_time = time.time()
    
    def log_operation(self, operation: str, **kwargs):
        """Log an operation with the request context."""
        kwargs["request_id"] = self.request_id
        LoggingHelper.log_operation_start(operation, kwargs)
    
    def log_success(self, operation: str, **kwargs):
        """Log operation success with the request context."""
        LoggingHelper.log_operation_success(operation, self.request_id, **kwargs)
    
    def log_error(self, operation: str, error: Union[str, Exception], **kwargs):
        """Log operation error with the request context."""
        kwargs["request_id"] = self.request_id
        LoggingHelper.log_operation_error(operation, self.request_id, error, **kwargs)
    
    def get_execution_time(self) -> float:
        """Get total execution time since request start."""
        return time.time() - self.start_time