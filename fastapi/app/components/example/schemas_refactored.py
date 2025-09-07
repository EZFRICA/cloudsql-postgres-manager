"""
Refactored schema management router using reusable components.

This module demonstrates how to use the reusable components
to reduce code duplication and improve maintainability.
"""

from fastapi import APIRouter, HTTPException, status, Request
from app.models import SchemaCreateRequest, SchemaCreateResponse
from app.services.schema_manager import SchemaManager
from app.services.connection_manager import ConnectionManager
from app.components import (
    SuccessResponse, ErrorResponse, ValidationHelper, 
    ErrorHandler, ServiceManager, handle_errors
)

router = APIRouter(prefix="/schemas", tags=["Schema Management"])

# Global instances
connection_manager = ConnectionManager()
schema_manager = SchemaManager(connection_manager)

# Service manager for schema operations
schema_service = ServiceManager("SchemaService")


def validate_schema_create_request(request: SchemaCreateRequest) -> tuple[bool, str]:
    """Validate schema creation request using ValidationHelper."""
    # Validate project ID
    is_valid, error = ValidationHelper.validate_project_id(request.project_id)
    if not is_valid:
        return False, f"Invalid project_id: {error}"
    
    # Validate instance name
    is_valid, error = ValidationHelper.validate_instance_name(request.instance_name)
    if not is_valid:
        return False, f"Invalid instance_name: {error}"
    
    # Validate database name
    is_valid, error = ValidationHelper.validate_database_name(request.database_name)
    if not is_valid:
        return False, f"Invalid database_name: {error}"
    
    # Validate schema name
    is_valid, error = ValidationHelper.validate_schema_name(request.schema_name)
    if not is_valid:
        return False, f"Invalid schema_name: {error}"
    
    return True, ""


@router.post("/create", response_model=SchemaCreateResponse)
@handle_errors
async def create_schema(request: SchemaCreateRequest, http_request: Request):
    """
    Create a schema in the database using reusable components.
    
    This endpoint demonstrates the use of reusable components for:
    - Input validation with ValidationHelper
    - Service operation execution with ServiceManager
    - Error handling with @handle_errors decorator
    - Standardized responses with SuccessResponse/ErrorResponse
    - Automatic logging and performance monitoring
    
    **Features:**
    - Idempotent: Safe to call multiple times
    - Schema validation: Ensures proper naming with ValidationHelper
    - Error handling: Comprehensive error reporting with ErrorHandler
    - Transaction safety: Automatic rollback on failure
    - Performance monitoring: Automatic execution time tracking
    
    **Use Cases:**
    - Prepare database for application deployment
    - Create isolated schemas for different environments
    - Set up multi-tenant database structures
    
    **Example:**
    ```json
    {
        "project_id": "my-project",
        "instance_name": "my-instance",
        "database_name": "my-database",
        "region": "europe-west1",
        "schema_name": "app_schema"
    }
    ```
    """
    request_id = getattr(http_request.state, 'request_id', None)
    
    # Validate request using ValidationHelper
    is_valid, error = validate_schema_create_request(request)
    if not is_valid:
        return ErrorHandler.handle_business_logic_error(
            "validation_error",
            error,
            details={"field": "request_validation"},
            request=http_request
        )
    
    # Execute schema creation using ServiceManager
    result = schema_service._execute_operation(
        "create_schema",
        schema_manager.create_schema,
        request.project_id,
        request.region,
        request.instance_name,
        request.database_name,
        request.schema_name,
        request_id=request_id
    )
    
    if not result.success:
        return ErrorHandler.handle_database_error(
            "create_schema",
            result.error,
            request=http_request
        )
    
    # Return success response using SuccessResponse
    return SuccessResponse.create(
        message="Schema created successfully",
        data=result.data,
        metadata={
            "execution_time": result.execution_time,
            "schema_name": request.schema_name,
            "project_id": request.project_id
        },
        request_id=request_id
    )