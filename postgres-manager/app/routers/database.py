"""
Database management router for health checks, schema listing, and table operations.
"""

from fastapi import APIRouter, HTTPException, status
from ..models import (
    SchemaListRequest,
    SchemaListResponse,
    TableListRequest,
    TableListResponse,
    DatabaseHealthRequest,
    DatabaseHealthResponse,
    PostgresInheritanceRequest,
    UserCleanupRequest,
    UserCleanupResponse,
)
from ..services.schema_manager import SchemaManager
from ..services.role_manager import RoleManager
from ..services.connection_manager import ConnectionManager
from ..services.health_manager import HealthManager
from ..services.user_manager import UserManager
from ..utils.logging_config import logger

router = APIRouter(prefix="/database", tags=["Database Management"])

# Global instances
connection_manager = ConnectionManager()
schema_manager = SchemaManager(connection_manager)
role_manager = RoleManager()
health_manager = HealthManager(connection_manager)
user_manager = UserManager(connection_manager)


@router.post("/schemas", response_model=SchemaListResponse)
async def list_schemas(request: SchemaListRequest):
    """
    List all schemas in the database.

    This endpoint retrieves all user-created schemas in the specified database,
    excluding system schemas like information_schema, pg_catalog, and pg_toast.

    **Features:**
    - Lists all non-system schemas
    - Excludes PostgreSQL system schemas
    - Provides execution timing information
    - Comprehensive error handling

    **Use Cases:**
    - Database exploration and discovery
    - Schema inventory management
    - Application deployment verification
    - Multi-tenant database monitoring

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
            f"Schema list request - project: {request.project_id}, "
            f"instance: {request.instance_name}, database: {request.database_name}"
        )

        result = schema_manager.list_schemas(
            project_id=request.project_id,
            region=request.region,
            instance_name=request.instance_name,
            database_name=request.database_name,
        )

        if result["success"]:
            logger.info(f"Successfully listed schemas: {result['schemas']}")
        else:
            logger.error(f"Failed to list schemas: {result['message']}")

        return result

    except Exception as e:
        logger.error(f"Unexpected error listing schemas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post("/tables", response_model=TableListResponse)
async def list_tables(request: TableListRequest):
    """
    List all tables in a specific schema.

    This endpoint retrieves all tables and views in the specified schema,
    including metadata such as table type, row count, and size information.

    **Features:**
    - Lists tables and views in a schema
    - Provides table metadata (type, row count, size)
    - Excludes system tables
    - Performance metrics included

    **Use Cases:**
    - Schema exploration and discovery
    - Table inventory management
    - Performance monitoring
    - Application deployment verification

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
        logger.info(
            f"Table list request - project: {request.project_id}, "
            f"instance: {request.instance_name}, database: {request.database_name}, "
            f"schema: {request.schema_name}"
        )

        result = schema_manager.list_tables(
            project_id=request.project_id,
            region=request.region,
            instance_name=request.instance_name,
            database_name=request.database_name,
            schema_name=request.schema_name,
        )

        if result["success"]:
            logger.info(
                f"Successfully listed {len(result['tables'])} tables in schema {request.schema_name}"
            )
        else:
            logger.error(f"Failed to list tables: {result['message']}")

        return result

    except Exception as e:
        logger.error(f"Unexpected error listing tables: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post("/health", response_model=DatabaseHealthResponse)
async def check_database_health(request: DatabaseHealthRequest):
    """
    Check database health and connection status.

    This endpoint performs a comprehensive health check of the database,
    including connection testing, version information, and performance metrics.

    **Features:**
    - Connection time measurement
    - Database version information
    - Uptime calculation
    - Active connection count
    - Comprehensive health status

    **Use Cases:**
    - Health monitoring and alerting
    - Performance baseline establishment
    - Troubleshooting connection issues
    - Service availability verification

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
            f"Database health check request - project: {request.project_id}, "
            f"instance: {request.instance_name}, database: {request.database_name}"
        )

        result = health_manager.check_database_health(
            project_id=request.project_id,
            region=request.region,
            instance_name=request.instance_name,
            database_name=request.database_name,
        )

        if result["success"]:
            logger.info(f"Database health check successful: {result['status']}")
        else:
            logger.error(f"Database health check failed: {result['message']}")

        return result

    except Exception as e:
        logger.error(f"Unexpected error checking database health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post("/postgres-inheritance/grant", response_model=dict)
async def grant_user_to_postgres(request: PostgresInheritanceRequest):
    """
    Grant an IAM user to postgres to allow postgres to manage this user.

    This endpoint allows postgres to inherit permissions from an IAM user,
    which is necessary for postgres to grant/revoke roles to/from that user.

    **Features:**
    - Validates that the user is a manageable IAM user
    - Checks for existing inheritance to avoid duplicates
    - Provides detailed execution timing
    - Comprehensive error handling and rollback

    **Use Cases:**
    - Enable postgres to manage specific IAM users
    - Grant role management capabilities to postgres
    - Prepare for role assignment operations

    **Example:**
    ```json
    {
        "project_id": "my-project",
        "instance_name": "my-instance",
        "database_name": "my-database",
        "region": "europe-west1",
        "username": "user@project.iam.gserviceaccount.com"
    }
    ```
    """
    try:
        result = user_manager.grant_user_to_postgres(
            project_id=request.project_id,
            region=request.region,
            instance_name=request.instance_name,
            database_name=request.database_name,
            username=request.username,
        )

        if result["success"]:
            logger.info(f"Successfully granted user {request.username} to postgres")
        else:
            logger.error(
                f"Failed to grant user {request.username} to postgres: {result['message']}"
            )

        return result

    except Exception as e:
        logger.error(f"Error granting user to postgres: {e}")
        return {
            "success": False,
            "message": f"Error granting user to postgres: {str(e)}",
            "username": request.username,
        }


@router.post("/postgres-inheritance/revoke", response_model=dict)
async def revoke_user_from_postgres(request: PostgresInheritanceRequest):
    """
    Revoke an IAM user from postgres (remove inheritance).

    This endpoint removes postgres's ability to manage the specified IAM user
    by revoking the inheritance relationship.

    **Features:**
    - Checks for existing inheritance before attempting revocation
    - Provides detailed execution timing
    - Comprehensive error handling and rollback
    - Idempotent operation (safe to call multiple times)

    **Use Cases:**
    - Remove postgres's ability to manage specific IAM users
    - Clean up unnecessary inheritance relationships
    - Security hardening by reducing postgres privileges

    **Example:**
    ```json
    {
        "project_id": "my-project",
        "instance_name": "my-instance",
        "database_name": "my-database",
        "region": "europe-west1",
        "username": "user@project.iam.gserviceaccount.com"
    }
    ```
    """
    try:
        result = user_manager.revoke_user_from_postgres(
            project_id=request.project_id,
            region=request.region,
            instance_name=request.instance_name,
            database_name=request.database_name,
            username=request.username,
        )

        if result["success"]:
            logger.info(f"Successfully revoked user {request.username} from postgres")
        else:
            logger.error(
                f"Failed to revoke user {request.username} from postgres: {result['message']}"
            )

        return result

    except Exception as e:
        logger.error(f"Error revoking user from postgres: {e}")
        return {
            "success": False,
            "message": f"Error revoking user from postgres: {str(e)}",
            "username": request.username,
        }


@router.post("/users/cleanup", response_model=UserCleanupResponse)
async def cleanup_user_before_deletion(request: UserCleanupRequest):
    """
    Clean up a user's ownership and permissions before permanent deletion.

    This endpoint performs a comprehensive cleanup of an IAM user before they are
    permanently deleted from the database. It ensures that:
    1. All objects owned by the user are transferred to postgres
    2. All permissions are revoked from the user
    3. Any remaining objects are properly dropped

    **Features:**
    - Transfers ownership of all user objects to postgres
    - Revokes all permissions from all schemas or a specific schema
    - Drops any remaining objects owned by the user
    - Comprehensive error handling and logging
    - Detailed response with operation status

    **Use Cases:**
    - Preparing for IAM user deletion
    - Cleaning up orphaned objects
    - Ensuring data continuity during user removal
    - Compliance with data retention policies

    **Important Notes:**
    - This operation should be called BEFORE deleting the IAM user
    - The operation is irreversible once completed
    - All user objects will be owned by postgres after cleanup
    - Use with caution in production environments

    **Example Usage:**
    ```json
    {
        "project_id": "my-project",
        "instance_name": "my-instance",
        "database_name": "my-database",
        "region": "europe-west1",
        "username": "user@example.com",
        "schema_name": "app_schema"
    }
    ```
    """
    try:
        logger.info(f"Starting cleanup for user {request.username} before deletion")

        with user_manager.connection_manager.get_connection(
            request.project_id,
            request.region,
            request.instance_name,
            request.database_name,
        ) as conn:
            cursor = conn.cursor()

            try:
                # Validate that this is a manageable IAM user
                validation = user_manager.is_valid_iam_user(cursor, request.username)
                if not validation["valid"]:
                    logger.warning(
                        f"Cannot cleanup user {request.username}: {validation['reason']}"
                    )
                    return UserCleanupResponse(
                        success=False,
                        message=f"Cannot cleanup user: {validation['reason']}",
                        username=request.username,
                        normalized_username=validation.get(
                            "username", request.username
                        ),
                        database_name=request.database_name,
                        schema_name=request.schema_name,
                        ownership_transferred=False,
                        permissions_revoked=False,
                        objects_dropped=False,
                        execution_time_seconds=0.0,
                    )

                normalized_username = validation["username"]

                # Perform the cleanup operation
                cleanup_success = user_manager.cleanup_user_before_deletion(
                    cursor=cursor,
                    username=request.username,
                    database_name=request.database_name,
                    schema_name=request.schema_name,
                )

                if cleanup_success:
                    logger.info(f"Successfully cleaned up user {normalized_username}")
                    message = (
                        f"User {normalized_username} cleanup completed successfully"
                    )
                    if request.schema_name:
                        message += f" for schema {request.schema_name}"
                    else:
                        message += " for all schemas"
                else:
                    logger.error(f"Failed to cleanup user {normalized_username}")
                    message = f"Failed to cleanup user {normalized_username}"

                return UserCleanupResponse(
                    success=cleanup_success,
                    message=message,
                    username=request.username,
                    normalized_username=normalized_username,
                    database_name=request.database_name,
                    schema_name=request.schema_name,
                    ownership_transferred=cleanup_success,
                    permissions_revoked=cleanup_success,
                    objects_dropped=cleanup_success,
                    execution_time_seconds=0.0,  # Would be calculated in real implementation
                )

            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()

    except Exception as e:
        logger.error(f"Error during user cleanup: {e}")
        return UserCleanupResponse(
            success=False,
            message=f"Error during user cleanup: {str(e)}",
            username=request.username,
            normalized_username=request.username,
            database_name=request.database_name,
            schema_name=request.schema_name,
            ownership_transferred=False,
            permissions_revoked=False,
            objects_dropped=False,
            execution_time_seconds=0.0,
        )
