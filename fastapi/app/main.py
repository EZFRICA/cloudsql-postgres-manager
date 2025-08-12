import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.models import ErrorResponse, HealthResponse, IAMUserRequest
from app.services.cloudsql import CloudSQLUserManager
from app.services.pubsub import PubSubMessageParser
from app.utils.logging_config import logger


# Global instances
user_manager = CloudSQLUserManager()
message_parser = PubSubMessageParser()


# FastAPI lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting Cloud SQL IAM User Permission Manager")
    yield
    logger.info("Shutting down Cloud SQL IAM User Permission Manager")
    user_manager.close()


# Initialize FastAPI app
app = FastAPI(
    title="Cloud SQL IAM User Permission Manager",
    description="""
    A service to manage IAM user permissions for Cloud SQL PostgreSQL databases.

    **IMPORTANT**: This service only manages SQL permissions (GRANT/REVOKE).
    IAM users must be created separately via Terraform, gcloud, or Cloud SQL API.

    Features:
    - Automatic schema creation if it doesn't exist
    - Permission levels: readonly, readwrite, admin
    - Pub/Sub message processing
    - Comprehensive error handling and logging
    - Automatic cleanup of permissions for removed users
    """,
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint for service monitoring

    Returns service status and version information.
    """
    return HealthResponse(
        status="healthy",
        service="Cloud SQL IAM User Permission Manager",
        version="4.0.0",
    )


@app.post("/", status_code=204, tags=["Pub/Sub"])
@app.post("/pubsub", status_code=204, tags=["Pub/Sub"])
async def handle_pubsub(request: Request):
    """
    Main endpoint for processing Pub/Sub messages

    **IMPORTANT**: This service only manages permissions for IAM Database Authentication users.
    The IAM users themselves must be created/deleted via Terraform, gcloud, or Cloud SQL API.

    Expected message format:
    ```json
    {
        "project_id": "my-project",
        "instance_name": "my-instance",
        "database_name": "my-db",
        "region": "europe-west1",
        "schema_name": "my-schema",
        "iam_users": [
            {
                "name": "user@project.iam.gserviceaccount.com",
                "permission_level": "readonly|readwrite|admin"
            }
        ]
    }
    ```

    Returns HTTP 204 on success, HTTP 400/500 on error.
    """
    try:
        # Parse Pub/Sub message
        request_json = await request.json()
        logger.info("Received Pub/Sub message for IAM user permission management")

        # Basic JSON validation
        if not request_json:
            logger.error("Empty request payload")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Empty request payload"
            )

        try:
            message_data = message_parser.parse_pubsub_message(request_json)
        except ValueError as e:
            logger.error(f"Invalid Pub/Sub message format: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid message format: {str(e)}",
            )

        # Validate message schema
        try:
            validated_data = message_parser.validate_message_schema(message_data)
        except ValueError as e:
            logger.error(f"Invalid message schema: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid message schema: {str(e)}",
            )

        # Log processing information (without sensitive data)
        logger.info(
            f"Processing IAM user permissions for project: {validated_data['project_id']}, "
            f"instance: {validated_data['instance_name']}, "
            f"database: {validated_data['database_name']}, "
            f"schema: {validated_data['schema_name']}, "
            f"region: {validated_data['region']}, "
            f"users: {len(validated_data['iam_users'])}"
        )

        # Check if there are users to process or revocations to perform
        if not validated_data["iam_users"]:
            logger.info(
                "No IAM users specified in message - will revoke permissions for all existing users"
            )

        # Validate IAM permissions for specified users
        if validated_data["iam_users"]:
            permissions_valid, invalid_users = user_manager.validate_iam_permissions(
                validated_data["project_id"], validated_data["iam_users"]
            )

            if not permissions_valid:
                # Filter out invalid users
                original_count = len(validated_data["iam_users"])
                validated_data["iam_users"] = [
                    user
                    for user in validated_data["iam_users"]
                    if user["name"] not in invalid_users
                ]

                logger.warning(
                    f"Proceeding with {len(validated_data['iam_users'])} valid users out of {original_count}, "
                    f"skipping {len(invalid_users)} users with invalid IAM permissions"
                )

        # Process IAM user permissions
        result = user_manager.process_users(validated_data)

        if result["success"]:
            # Success even with partial errors
            total_errors = result.get("total_errors", 0)
            message_id = result.get("message_id", "unknown")

            if total_errors > 0:
                logger.warning(
                    f"Processed Pub/Sub message {message_id} with {total_errors} errors"
                )
            else:
                logger.info(f"Successfully processed Pub/Sub message: {message_id}")

            # Return 204 No Content to indicate success to Pub/Sub
            return None
        else:
            logger.error(
                f"Failed to process IAM user permissions: {result.get('error', 'Unknown error')}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error=result.get("error", "Unknown processing error"),
                    details={
                        "project_id": result.get("project_id"),
                        "instance_name": result.get("instance_name"),
                        "database_name": result.get("database_name"),
                        "schema_name": result.get("schema_name"),
                    },
                ).dict(),
            )

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON format"
        )
    except Exception as e:
        logger.error(f"Unexpected error processing Pub/Sub message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@app.post("/manage-users", response_model=dict, tags=["Direct API"])
async def manage_users_direct(request: IAMUserRequest):
    """
    Direct API endpoint for managing IAM user permissions (not via Pub/Sub)

    This endpoint allows direct management of IAM user permissions without going through Pub/Sub.
    Useful for testing or direct integration.

    **IMPORTANT**: IAM users must already exist in the database (created via Terraform/gcloud).
    """
    try:
        # Convert Pydantic model to dict format expected by process_users
        message_data = {
            "project_id": request.project_id,
            "instance_name": request.instance_name,
            "database_name": request.database_name,
            "region": request.region,
            "schema_name": request.schema_name or f"{request.database_name}_schema",
            "iam_users": [user.dict() for user in request.iam_users],
        }

        logger.info(
            f"Direct API request for IAM user permissions - project: {request.project_id}, "
            f"instance: {request.instance_name}, users: {len(request.iam_users)}"
        )

        # Validate IAM permissions for specified users
        if message_data["iam_users"]:
            permissions_valid, invalid_users = user_manager.validate_iam_permissions(
                message_data["project_id"], message_data["iam_users"]
            )

            if not permissions_valid:
                # Filter out invalid users
                original_count = len(message_data["iam_users"])
                message_data["iam_users"] = [
                    user
                    for user in message_data["iam_users"]
                    if user["name"] not in invalid_users
                ]

                logger.warning(
                    f"Proceeding with {len(message_data['iam_users'])} valid users out of {original_count}, "
                    f"skipping {len(invalid_users)} users with invalid IAM permissions"
                )

        # Process IAM user permissions
        result = user_manager.process_users(message_data)

        if result["success"]:
            logger.info(
                f"Successfully processed direct API request for {request.project_id}/{request.instance_name}"
            )
            return result
        else:
            logger.error(
                f"Failed to process IAM user permissions: {result.get('error', 'Unknown error')}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error=result.get("error", "Unknown processing error"),
                    details={
                        "project_id": result.get("project_id"),
                        "instance_name": result.get("instance_name"),
                        "database_name": result.get("database_name"),
                        "schema_name": result.get("schema_name"),
                    },
                ).dict(),
            )

    except Exception as e:
        logger.error(f"Unexpected error in direct API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


# Error handlers
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
