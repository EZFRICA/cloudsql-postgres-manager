"""
Data models for Cloud SQL IAM User Permission Manager.

This module defines Pydantic models for handling IAM user requests,
Pub/Sub messages, and API responses.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class IAMUser(BaseModel):
    """
    Model representing an IAM user with permission level.
    
    Attributes:
        name: IAM user email address
        permission_level: Access level (readonly, readwrite, admin)
    """
    name: str = Field(
        ..., description="IAM user email (e.g., user@project.iam.gserviceaccount.com)"
    )
    permission_level: str = Field(
        default="readonly",
        description="Permission level: readonly, readwrite, or admin",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "my-service@project.iam.gserviceaccount.com",
                "permission_level": "readonly",
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
        schema_name: Optional schema name
        iam_users: List of users to manage
    """
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    region: str = Field(..., description="GCP region")
    schema_name: Optional[str] = Field(
        default=None, description="Schema name (defaults to {database_name}_schema)"
    )
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
                        "permission_level": "readonly",
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
