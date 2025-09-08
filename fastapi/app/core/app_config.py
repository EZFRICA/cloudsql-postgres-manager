"""
FastAPI application configuration and setup.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.utils.logging_config import logger


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage application lifecycle"""
        logger.info("Starting Cloud SQL IAM User Permission Manager")
        yield
        logger.info("Shutting down Cloud SQL IAM User Permission Manager")
        # Close any resources here if needed

    app = FastAPI(
        title="Cloud SQL IAM User Permission Manager",
        description="""
        ## Overview
        
        A comprehensive service for managing IAM user permissions and database schemas for Cloud SQL PostgreSQL databases.
        
        ## ⚠️ Important Notes
        
        - **This service only manages SQL permissions (GRANT/REVOKE) and schema creation**
        - **IAM users must be created separately via Terraform, gcloud, or Cloud SQL API**
        - **All operations are idempotent and safe for repeated execution**
        
        ## 🚀 Features
        
        - **Schema Management**: Create and manage database schemas
        - **Role-Based Access Control**: Plugin-based role system with predefined role types
        - **Role Types**: `reader`, `writer`, `admin`, `analyst`, `monitor` with granular control
        - **Connection Pooling**: High-performance connection management
        - **Comprehensive Logging**: Structured logging with configurable levels
        - **Error Handling**: Robust error handling with detailed error responses
        - **Health Monitoring**: Built-in health checks and metrics
        
        ## 🔧 Configuration
        
        The service supports extensive configuration via environment variables:
        
        - **Database**: Connection pooling, timeouts, retry settings
        - **Security**: Allowed regions, user limits, validation rules
        - **Monitoring**: Metrics collection, logging levels
        - **Performance**: Pool sizes, connection limits
        
        ## 📚 API Documentation
        
        - **Health Check**: `/health` - Service status and version
        - **Role Management**: `/roles/*` - Assign, revoke, list roles
        - **Schema Management**: `/schemas/*` - Create and manage schemas
        - **Database Management**: `/database/*` - Health, schemas, tables
        
        ## 🔒 Security
        
        - **IAM Validation**: Validates IAM permissions before processing
        - **Secret Management**: Uses Google Secret Manager for credentials
        - **Input Validation**: Comprehensive request validation with Pydantic
        - **Error Sanitization**: Safe error messages without sensitive data
        
        ## 📊 Monitoring
        
        - **Health Endpoints**: Service and database health checks
        - **Metrics**: Connection pool statistics and performance metrics
        - **Logging**: Structured JSON logging with correlation IDs
        - **Error Tracking**: Detailed error reporting and stack traces
        """,
        version=settings.app_version,
        lifespan=lifespan,
        contact={
            "name": "Cloud SQL IAM User Permission Manager",
        },
        openapi_tags=[
            {"name": "Health", "description": "Health check and monitoring endpoints"},
            {
                "name": "Role Management",
                "description": "Role assignment, revocation, and management operations",
            },
            {
                "name": "Schema Management",
                "description": "Database schema creation and management",
            },
            {
                "name": "Database Management",
                "description": "Database health, schema listing, and table operations",
            },
        ],
    )

    return app
