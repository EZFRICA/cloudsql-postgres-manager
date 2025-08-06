from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class IAMUser(BaseModel):
    name: str = Field(..., description="IAM user email (e.g., user@project.iam.gserviceaccount.com)")
    permission_level: str = Field(default="readonly", description="Permission level: readonly, readwrite, or admin")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "my-service@project.iam.gserviceaccount.com",
                "permission_level": "readonly"
            }
        }


class PubSubMessage(BaseModel):
    data: str = Field(..., description="Base64-encoded JSON data")
    attributes: Optional[Dict[str, str]] = Field(default={}, description="Message attributes")
    messageId: Optional[str] = Field(default=None, description="Pub/Sub message ID")
    publishTime: Optional[str] = Field(default=None, description="Publish timestamp")


class PubSubRequest(BaseModel):
    message: PubSubMessage


class IAMUserRequest(BaseModel):
    project_id: str = Field(..., description="GCP project ID")
    instance_name: str = Field(..., description="Cloud SQL instance name")
    database_name: str = Field(..., description="Database name")
    region: str = Field(..., description="GCP region")
    schema_name: Optional[str] = Field(default=None, description="Schema name (defaults to {database_name}_schema)")
    iam_users: List[IAMUser] = Field(default=[], description="List of IAM users to manage")

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
                        "permission_level": "readonly"
                    }
                ]
            }
        }


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ErrorResponse(BaseModel):
    error: str
    details: Optional[Dict] = None 