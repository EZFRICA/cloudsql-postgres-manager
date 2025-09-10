"""
Schema management router for database schema operations.
"""

from fastapi import APIRouter, HTTPException, status
from ..models import SchemaCreateRequest, SchemaCreateResponse
from ..services.schema_manager import SchemaManager
from ..services.connection_manager import ConnectionManager
from ..utils.logging_config import logger

router = APIRouter(prefix="/schemas", tags=["Schema Management"])

# Global instances
connection_manager = ConnectionManager()
schema_manager = SchemaManager(connection_manager)


@router.post("/create", response_model=SchemaCreateResponse)
async def create_schema(request: SchemaCreateRequest):
    """
    Create a schema in the database.

    This endpoint creates a PostgreSQL schema in the specified database.
    The schema creation is idempotent - if the schema already exists,
    the operation will succeed without error.

    **Features:**
    - Idempotent: Safe to call multiple times
    - Schema validation: Ensures proper PostgreSQL naming conventions
    - Owner validation: Verifies that the specified owner exists in the database
    - Optional owner: Specify IAM user or service account as schema owner (defaults to postgres)
    - Error handling: Comprehensive error reporting
    - Transaction safety: Automatic rollback on failure

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
        "schema_name": "app_schema",
        "owner": "my-service@project.iam.gserviceaccount.com"
    }
    ```
    """
    try:
        logger.info(
            f"Schema creation request - project: {request.project_id}, "
            f"instance: {request.instance_name}, database: {request.database_name}, "
            f"schema: {request.schema_name}"
        )

        result = schema_manager.create_schema(
            project_id=request.project_id,
            region=request.region,
            instance_name=request.instance_name,
            database_name=request.database_name,
            schema_name=request.schema_name,
            owner=request.owner,
        )

        if result["success"]:
            logger.info(f"Schema creation successful: {result['message']}")
        else:
            logger.error(f"Schema creation failed: {result['message']}")

        return SchemaCreateResponse(**result)

    except Exception as e:
        logger.error(f"Schema creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schema creation failed: {str(e)}",
        )
