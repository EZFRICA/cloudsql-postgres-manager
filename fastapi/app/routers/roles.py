"""
Role management router for role assignment, revocation, and management operations.
"""

from fastapi import APIRouter, HTTPException, status
from app.models import (
    RoleInitializeRequest,
    RoleInitializeResponse,
    RoleAssignRequest,
    RoleRevokeRequest,
    RoleListRequest,
    RoleOperationResponse,
    UserRoleListResponse,
    RoleListResponse,
)
from app.services.role_manager import RoleManager
from app.services.role_permission_manager import RolePermissionManager
from app.services.user_manager import UserManager
from app.utils.logging_config import logger

router = APIRouter(prefix="/roles", tags=["Role Management"])

# Global instances
role_manager = RoleManager()
role_permission_manager = RolePermissionManager()
user_manager = UserManager()


@router.post("/initialize", response_model=RoleInitializeResponse)
async def initialize_roles(request: RoleInitializeRequest):
    """
    Initialize PostgreSQL roles for a database with plugin architecture.

    This endpoint creates and manages PostgreSQL roles with support for:
    - Standard roles (app_reader, app_writer, app_admin, app_monitor, app_analyst)
    - Plugin-based custom role definitions
    - Versioning and checksum validation
    - Idempotent operations (safe to call multiple times)
    - Firebase registry for tracking role state

    **Features:**
    - Idempotent: Safe to call multiple times
    - Plugin architecture: Supports custom role definitions
    - Versioning: Automatic detection of role definition changes
    - Firebase integration: Tracks role initialization state
    - Force update: Option to re-create existing roles

    **Standard Roles Created:**
    - `app_reader`: Read-only access to application schema
    - `app_writer`: Write access (inherits from app_reader)
    - `app_admin`: Administrative access (inherits from app_writer)
    - `app_monitor`: Monitoring access with PostgreSQL native roles
    - `app_analyst`: Analytics access (inherits from app_reader + monitoring)

    **Plugin System:**
    Developers can create custom role definitions by:
    1. Creating a class that inherits from `RolePlugin`
    2. Implementing `get_role_definitions()` method
    3. Registering the plugin with the system

    **Firebase Registry:**
    Role initialization state is tracked in Firebase Firestore:
    - Collection: `database_role_registry`
    - Document ID: `{project_id}_{instance}_{database}`
    - Tracks versions, checksums, and creation history
    """
    try:
        logger.info(
            f"Role initialization request - project: {request.project_id}, "
            f"instance: {request.instance_name}, database: {request.database_name}, "
            f"force_update: {request.force_update}"
        )

        # Initialize roles
        result = role_manager.initialize_roles(
            project_id=request.project_id,
            instance_name=request.instance_name,
            database_name=request.database_name,
            region=request.region,
            force_update=request.force_update,
            schema_name=request.schema_name,
        )

        if result.success:
            logger.info(f"Role initialization completed successfully: {result.message}")
        else:
            logger.error(f"Role initialization failed: {result.message}")

        return result

    except Exception as e:
        logger.error(f"Unexpected error in role initialization: {e}")
        return RoleInitializeResponse(
            success=False,
            message=f"Internal server error: {str(e)}",
            execution_time_seconds=0.0,
        )


@router.get("/status", response_model=dict)
async def get_role_status(project_id: str, instance_name: str, database_name: str):
    """
    Get role initialization status for a database.

    Returns the current status of role initialization including:
    - Whether roles have been initialized
    - Creation and update timestamps
    - Number of roles created
    - Creation history

    Args:
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
    """
    try:
        status = role_manager.get_role_status(project_id, instance_name, database_name)

        if status is None:
            return {
                "roles_initialized": False,
                "message": "No role registry found for this database",
            }

        return status

    except Exception as e:
        logger.error(f"Failed to get role status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get role status: {str(e)}",
        )


@router.post("/assign", response_model=RoleOperationResponse)
async def assign_role(request: RoleAssignRequest):
    """
    Assign a role to a user.

    This endpoint assigns a specific role to an IAM user. The role must exist
    and the user must exist in the database.

    **Features:**
    - Role validation: Ensures role exists before assignment
    - User validation: Ensures user exists before assignment
    - Idempotent: Safe to call multiple times
    - Error handling: Comprehensive error reporting

    **Example:**
    ```json
    {
        "project_id": "my-project",
        "instance_name": "my-instance",
        "database_name": "my-database",
        "region": "europe-west1",
        "schema_name": "app_schema",
        "username": "user@example.com",
        "role_name": "mydb_app_writer"
    }
    ```
    """
    try:
        logger.info(
            f"Role assignment request - user: {request.username}, role: {request.role_name}"
        )

        result = role_permission_manager.assign_role(
            project_id=request.project_id,
            region=request.region,
            instance_name=request.instance_name,
            database_name=request.database_name,
            schema_name=request.schema_name,
            username=request.username,
            role_name=request.role_name,
        )

        if result["success"]:
            logger.info(f"Role assignment successful: {result['message']}")
        else:
            logger.error(f"Role assignment failed: {result['message']}")

        return RoleOperationResponse(**result)

    except Exception as e:
        logger.error(f"Role assignment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Role assignment failed: {str(e)}",
        )


@router.post("/revoke", response_model=RoleOperationResponse)
async def revoke_role(request: RoleRevokeRequest):
    """
    Revoke a role from a user.

    This endpoint revokes a specific role from an IAM user.

    **Features:**
    - Role validation: Ensures role exists before revocation
    - User validation: Ensures user exists before revocation
    - Safe operation: No error if role not assigned
    - Error handling: Comprehensive error reporting

    **Example:**
    ```json
    {
        "project_id": "my-project",
        "instance_name": "my-instance",
        "database_name": "my-database",
        "region": "europe-west1",
        "schema_name": "app_schema",
        "username": "user@example.com",
        "role_name": "mydb_app_writer"
    }
    ```
    """
    try:
        logger.info(
            f"Role revocation request - user: {request.username}, role: {request.role_name}"
        )

        result = role_permission_manager.revoke_role(
            project_id=request.project_id,
            region=request.region,
            instance_name=request.instance_name,
            database_name=request.database_name,
            schema_name=request.schema_name,
            username=request.username,
            role_name=request.role_name,
        )

        if result["success"]:
            logger.info(f"Role revocation successful: {result['message']}")
        else:
            logger.error(f"Role revocation failed: {result['message']}")

        return RoleOperationResponse(**result)

    except Exception as e:
        logger.error(f"Role revocation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Role revocation failed: {str(e)}",
        )


@router.post("/users", response_model=UserRoleListResponse)
async def get_users_and_roles(request: RoleListRequest):
    """
    Get all users and their assigned roles for a schema.

    This endpoint retrieves all IAM users and their assigned roles for a specific schema.

    **Features:**
    - Complete user listing: All IAM users in the database
    - Role filtering: Only roles for the specified schema
    - User classification: Distinguishes IAM users from system users
    - Performance optimized: Single query execution

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
    try:
        logger.info(f"User role listing request - schema: {request.schema_name}")

        result = user_manager.get_users_and_roles(
            project_id=request.project_id,
            region=request.region,
            instance_name=request.instance_name,
            database_name=request.database_name,
            schema_name=request.schema_name,
        )

        if result["success"]:
            logger.info(f"User role listing successful: {result['message']}")
        else:
            logger.error(f"User role listing failed: {result['message']}")

        return UserRoleListResponse(**result)

    except Exception as e:
        logger.error(f"User role listing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User role listing failed: {str(e)}",
        )


@router.post("/list", response_model=RoleListResponse)
async def list_roles(request: RoleListRequest):
    """
    List all available roles in the database.

    This endpoint retrieves all user-created roles in the database,
    excluding system roles like postgres, cloudsqlsuperuser, etc.

    **Features:**
    - Lists all non-system roles
    - Excludes PostgreSQL system roles
    - Provides execution timing information
    - Comprehensive error handling

    **Use Cases:**
    - Role inventory management
    - Permission auditing
    - Role discovery for applications
    - Security compliance checking

    **Example:**
    ```json
    {
        "project_id": "my-project",
        "instance_name": "my-instance",
        "database_name": "my-database",
        "region": "europe-west1"
    }
    ```
    """
    try:
        logger.info(
            f"Role list request - project: {request.project_id}, "
            f"instance: {request.instance_name}, database: {request.database_name}"
        )

        result = role_manager.list_roles(
            project_id=request.project_id,
            region=request.region,
            instance_name=request.instance_name,
            database_name=request.database_name,
        )

        if result["success"]:
            logger.info(f"Successfully listed {len(result['roles'])} roles")
        else:
            logger.error(f"Failed to list roles: {result['message']}")

        return result

    except Exception as e:
        logger.error(f"Unexpected error listing roles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )
