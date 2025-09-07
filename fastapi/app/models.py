"""
Data models for Cloud SQL IAM User Permission Manager.

This module defines Pydantic models for handling IAM user requests,
Pub/Sub messages, and API responses.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class IAMUser(BaseModel):
    """
    Model representing an IAM user with permission role.

    Attributes:
        name: IAM user email address
        permission_role: Role type (e.g., reader, writer, admin, analyst, monitor)
    """

    name: str = Field(
        ..., description="IAM user email (e.g., user@project.iam.gserviceaccount.com)"
    )
    permission_role: str = Field(
        default="reader",
        description="Role type: reader, writer, admin, analyst, or monitor",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "my-service@project.iam.gserviceaccount.com",
                "permission_role": "reader",
            }
        }


class PubSubMessage(BaseModel):
    """
    Model for Pub/Sub message structure.

    Attributes:
        data: Base64-encoded JSON data
        attributes: Optional message attributes
        messageId: Unique message identifier
        publishTime: Message publication timestamp
    """

    data: str = Field(..., description="Base64-encoded JSON data")
    attributes: Optional[Dict[str, str]] = Field(
        default={}, description="Message attributes"
    )
    messageId: Optional[str] = Field(default=None, description="Pub/Sub message ID")
    publishTime: Optional[str] = Field(default=None, description="Publish timestamp")


class PubSubRequest(BaseModel):
    """
    Wrapper for Pub/Sub message requests.

    Attributes:
        message: The actual Pub/Sub message
    """

    message: PubSubMessage


class IAMUserRequest(BaseModel):
    """
    Model for IAM user permission management requests.

    Attributes:
        project_id: GCP project identifier
        instance_name: Cloud SQL instance name
        database_name: Target database name
        region: GCP region
        schema_name: Schema name
        iam_users: List of users to manage
    """

    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    region: str = Field(..., description="GCP region")
    schema_name: str = Field(..., description="Schema name")
    iam_users: List[IAMUser] = Field(
        default=[], description="List of IAM users to manage"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "region": "europe-west1",
                "schema_name": "my_schema",
                "iam_users": [
                    {
                        "name": "service-account@project.iam.gserviceaccount.com",
                        "permission_role": "reader",
                    }
                ],
            }
        }


class HealthResponse(BaseModel):
    """
    Health check response model.

    Attributes:
        status: Service health status
        service: Service name
        version: Service version
    """

    status: str
    service: str
    version: str


class ErrorResponse(BaseModel):
    """
    Error response model.

    Attributes:
        error: Error message
        details: Optional additional error details
    """

    error: str
    details: Optional[Dict] = None


# Role Management Models

class RoleInitializeRequest(BaseModel):
    """
    Model for role initialization requests.
    
    Attributes:
        project_id: GCP project identifier
        instance_name: Cloud SQL instance name
        database_name: Target database name
        region: GCP region
        force_update: Whether to force update existing roles
        schema_name: Schema name for app roles
    """
    
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    region: str = Field(..., description="GCP region")
    force_update: bool = Field(default=False, description="Force update existing roles")
    schema_name: str = Field(..., description="Schema name for app roles")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my-project",
                "instance_name": "my-instance", 
                "database_name": "my-database",
                "region": "europe-west1",
                "force_update": False,
                "schema_name": "app_schema"
            }
        }


class RoleInitializeResponse(BaseModel):
    """
    Model for role initialization responses.
    
    Attributes:
        success: Whether the operation was successful
        message: Response message
        roles_created: List of roles that were created
        roles_updated: List of roles that were updated
        roles_skipped: List of roles that were skipped
        total_roles: Total number of roles processed
        firebase_document_id: Firebase document ID for tracking
        execution_time_seconds: Time taken to execute the operation
    """
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    roles_created: List[str] = Field(default=[], description="Roles that were created")
    roles_updated: List[str] = Field(default=[], description="Roles that were updated")
    roles_skipped: List[str] = Field(default=[], description="Roles that were skipped")
    total_roles: int = Field(default=0, description="Total number of roles processed")
    firebase_document_id: Optional[str] = Field(default=None, description="Firebase document ID")
    execution_time_seconds: float = Field(default=0.0, description="Execution time in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Roles initialized successfully",
                "roles_created": ["app_public_reader", "app_public_writer", "app_public_admin"],
                "roles_updated": [],
                "roles_skipped": [],
                "total_roles": 3,
                "firebase_document_id": "my-project_my-instance_my-database",
                "execution_time_seconds": 2.5
            }
        }


class FirestoreRoleRegistry(BaseModel):
    """
    Model for Firestore role registry document structure.
    
    This model represents the complete structure stored in Firestore
    for tracking role initialization state and definitions.
    
    Role naming convention: {database}_{schema}_{role_type}
    Examples: app_public_reader, ecommerce_products_writer, analytics_reports_admin
    """
    
    roles_initialized: bool = Field(default=False, description="Whether roles have been initialized")
    created_at: datetime = Field(default_factory=datetime.now, description="Initial creation timestamp")
    created_by: str = Field(default="system", description="Who created the roles")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    force_update: bool = Field(default=False, description="Force update flag")
    roles_definitions: Dict[str, Dict[str, Any]] = Field(default={}, description="Standard role definitions")
    plugin_roles: Dict[str, Dict[str, Any]] = Field(default={}, description="Plugin role definitions")
    creation_history: List[Dict[str, Any]] = Field(default=[], description="History of role operations")
    
    class Config:
        json_schema_extra = {
            "example": {
                "roles_initialized": True,
                "created_at": "2024-01-15T10:00:00Z",
                "created_by": "system",
                "last_updated": "2024-01-15T10:00:00Z",
                "force_update": False,
                "roles_definitions": {
                    "app_public_reader": {
                        "version": "1.0.0",
                        "checksum": "sha256_hash",
                        "sql_commands": ["CREATE ROLE app_public_reader NOLOGIN;"],
                        "inherits": [],
                        "native_roles": [],
                        "created_at": "2024-01-15T10:00:00Z",
                        "status": "active"
                    }
                },
                "plugin_roles": {},
                "creation_history": []
            }
        }
        
        # Configuration for Firestore compatibility
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class RoleAssignRequest(BaseModel):
    """
    Model for role assignment requests.
    
    Attributes:
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        region: GCP region
        schema_name: Schema name
        username: IAM username to assign role to
        role_name: Role name to assign
    """
    
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    region: str = Field(..., description="GCP region")
    schema_name: str = Field(..., description="Schema name")
    username: str = Field(..., description="IAM username to assign role to")
    role_name: str = Field(..., description="Role name to assign")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "region": "europe-west1",
                "schema_name": "app_schema",
                "username": "user@example.com",
                "role_name": "mydb_app_writer"
            }
        }


class RoleRevokeRequest(BaseModel):
    """
    Model for role revocation requests.
    
    Attributes:
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        region: GCP region
        schema_name: Schema name
        username: IAM username to revoke role from
        role_name: Role name to revoke
    """
    
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    region: str = Field(..., description="GCP region")
    schema_name: str = Field(..., description="Schema name")
    username: str = Field(..., description="IAM username to revoke role from")
    role_name: str = Field(..., description="Role name to revoke")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "region": "europe-west1",
                "schema_name": "app_schema",
                "username": "user@example.com",
                "role_name": "mydb_app_writer"
            }
        }


class RoleListRequest(BaseModel):
    """
    Model for role listing requests.
    
    Attributes:
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        region: GCP region
        schema_name: Schema name
    """
    
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    region: str = Field(..., description="GCP region")
    schema_name: str = Field(..., description="Schema name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "region": "europe-west1",
                "schema_name": "app_schema"
            }
        }


class UserRoleInfo(BaseModel):
    """
    Model for user role information.
    
    Attributes:
        username: Username
        roles: List of assigned roles
        is_iam_user: Whether this is an IAM user
    """
    
    username: str = Field(..., description="Username")
    roles: List[str] = Field(..., description="List of assigned roles")
    is_iam_user: bool = Field(..., description="Whether this is an IAM user")


class RoleOperationResponse(BaseModel):
    """
    Model for role operation responses.
    
    Attributes:
        success: Whether the operation was successful
        message: Response message
        username: Username
        role_name: Role name
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        schema_name: Schema name
        execution_time_seconds: Time taken to execute the operation
    """
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    username: str = Field(..., description="Username")
    role_name: str = Field(..., description="Role name")
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    schema_name: str = Field(..., description="Schema name")
    execution_time_seconds: float = Field(..., description="Time taken to execute the operation")


class UserRoleListResponse(BaseModel):
    """
    Model for user role list responses.
    
    Attributes:
        success: Whether the operation was successful
        message: Response message
        users: List of users with their roles
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        schema_name: Schema name
        execution_time_seconds: Time taken to execute the operation
    """
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    users: List[UserRoleInfo] = Field(..., description="List of users with their roles")
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    schema_name: str = Field(..., description="Schema name")
    execution_time_seconds: float = Field(..., description="Time taken to execute the operation")


class DatabaseExecuteRequest(BaseModel):
    """
    Model for database execution requests.
    
    Attributes:
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        region: GCP region
        sql_script: SQL script to execute
    """
    
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    region: str = Field(..., description="GCP region")
    sql_script: str = Field(..., description="SQL script to execute")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "region": "europe-west1",
                "sql_script": "SELECT * FROM information_schema.tables LIMIT 10;"
            }
        }


class DatabaseExecuteResponse(BaseModel):
    """
    Model for database execution responses.
    
    Attributes:
        success: Whether the operation was successful
        message: Response message
        results: Query results (if any)
        row_count: Number of rows returned
        execution_time_seconds: Time taken to execute the operation
    """
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    results: List[dict] = Field(default=[], description="Query results")
    row_count: int = Field(default=0, description="Number of rows returned")
    execution_time_seconds: float = Field(..., description="Time taken to execute the operation")


class SchemaCreateRequest(BaseModel):
    """
    Model for schema creation requests.
    
    Attributes:
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        region: GCP region
        schema_name: Schema name to create
        owner: Optional IAM user or service account to be the schema owner (defaults to postgres)
    """
    
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    region: str = Field(..., description="GCP region")
    schema_name: str = Field(..., description="Schema name to create")
    owner: Optional[str] = Field(default=None, description="IAM user or service account to be the schema owner (optional, defaults to postgres)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "region": "europe-west1",
                "schema_name": "app_schema",
                "owner": "my-service@project.iam.gserviceaccount.com"
            }
        }


class SchemaCreateResponse(BaseModel):
    """
    Model for schema creation responses.
    
    Attributes:
        success: Whether the operation was successful
        message: Response message
        schema_name: Name of the created schema
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        execution_time_seconds: Time taken to execute the operation
    """
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    schema_name: str = Field(..., description="Name of the created schema")
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    execution_time_seconds: float = Field(..., description="Time taken to execute the operation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Schema created successfully",
                "schema_name": "app_schema",
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "execution_time_seconds": 0.5
            }
        }


class SchemaListRequest(BaseModel):
    """
    Model for schema list requests.
    
    Attributes:
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        region: Instance region
    """
    
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    region: str = Field(..., description="Instance region")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "region": "europe-west1"
            }
        }


class SchemaListResponse(BaseModel):
    """
    Model for schema list responses.
    
    Attributes:
        success: Whether the operation was successful
        message: Response message
        schemas: List of schema names
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        execution_time_seconds: Time taken to execute the operation
    """
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    schemas: List[str] = Field(..., description="List of schema names")
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    execution_time_seconds: float = Field(..., description="Time taken to execute the operation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Retrieved 3 schemas",
                "schemas": ["public", "app_schema", "analytics"],
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "execution_time_seconds": 0.2
            }
        }


class TableListRequest(BaseModel):
    """
    Model for table list requests.
    
    Attributes:
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        region: Instance region
        schema_name: Schema name to list tables from
    """
    
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    region: str = Field(..., description="Instance region")
    schema_name: str = Field(..., description="Schema name to list tables from")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "region": "europe-west1",
                "schema_name": "app_schema"
            }
        }


class TableInfo(BaseModel):
    """
    Model for table information.
    
    Attributes:
        table_name: Name of the table
        table_type: Type of table (BASE TABLE, VIEW, etc.)
        row_count: Approximate number of rows
        size_bytes: Approximate size in bytes
    """
    
    table_name: str = Field(..., description="Name of the table")
    table_type: str = Field(..., description="Type of table")
    row_count: Optional[int] = Field(None, description="Approximate number of rows")
    size_bytes: Optional[int] = Field(None, description="Approximate size in bytes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "table_name": "users",
                "table_type": "BASE TABLE",
                "row_count": 1000,
                "size_bytes": 65536
            }
        }


class TableListResponse(BaseModel):
    """
    Model for table list responses.
    
    Attributes:
        success: Whether the operation was successful
        message: Response message
        tables: List of table information
        schema_name: Schema name
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        execution_time_seconds: Time taken to execute the operation
    """
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    tables: List[TableInfo] = Field(..., description="List of table information")
    schema_name: str = Field(..., description="Schema name")
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    execution_time_seconds: float = Field(..., description="Time taken to execute the operation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Retrieved 2 tables",
                "tables": [
                    {
                        "table_name": "users",
                        "table_type": "BASE TABLE",
                        "row_count": 1000,
                        "size_bytes": 65536
                    },
                    {
                        "table_name": "orders",
                        "table_type": "BASE TABLE",
                        "row_count": 5000,
                        "size_bytes": 327680
                    }
                ],
                "schema_name": "app_schema",
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "execution_time_seconds": 0.3
            }
        }


class DatabaseHealthRequest(BaseModel):
    """
    Model for database health check requests.
    
    Attributes:
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        region: Instance region
    """
    
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    region: str = Field(..., description="Instance region")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "region": "europe-west1"
            }
        }


class DatabaseHealthResponse(BaseModel):
    """
    Model for database health check responses.
    
    Attributes:
        success: Whether the operation was successful
        message: Response message
        status: Database status (healthy, unhealthy, unknown)
        connection_time_ms: Connection time in milliseconds
        database_info: Database information
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        execution_time_seconds: Time taken to execute the operation
    """
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    status: str = Field(..., description="Database status")
    connection_time_ms: Optional[float] = Field(None, description="Connection time in milliseconds")
    database_info: Optional[Dict[str, Any]] = Field(None, description="Database information")
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    execution_time_seconds: float = Field(..., description="Time taken to execute the operation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Database is healthy",
                "status": "healthy",
                "connection_time_ms": 45.2,
                "database_info": {
                    "version": "PostgreSQL 15.4",
                    "uptime": "5 days, 12 hours",
                    "active_connections": 15
                },
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "execution_time_seconds": 0.1
            }
        }


class RoleListResponse(BaseModel):
    """
    Model for role list responses.
    
    Attributes:
        success: Whether the operation was successful
        message: Response message
        roles: List of available roles
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        database_name: Database name
        execution_time_seconds: Time taken to execute the operation
    """
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    roles: List[str] = Field(..., description="List of available roles")
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    execution_time_seconds: float = Field(..., description="Time taken to execute the operation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Retrieved 5 roles",
                "roles": [
                    "app_reader",
                    "app_writer", 
                    "app_admin",
                    "app_monitor",
                    "app_analyst"
                ],
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "execution_time_seconds": 0.2
            }
        }


class PostgresInheritanceRequest(BaseModel):
    """
    Model for postgres inheritance management requests.
    
    This model is used for granting or revoking postgres's ability to manage
    IAM users through inheritance relationships.
    """
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    region: str = Field(..., description="GCP region")
    username: str = Field(..., description="IAM username")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "my-project",
                "instance_name": "my-instance",
                "database_name": "my-database",
                "region": "europe-west1",
                "username": "user@example.com"
            }
        }


