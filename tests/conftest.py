"""
Pytest configuration and shared fixtures for Cloud SQL PostgreSQL Manager tests.

This module provides common fixtures and configuration for all test modules.
"""

import pytest
import asyncio
from unittest.mock import Mock
from fastapi.testclient import TestClient

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "postgres-manager"))

# Mock Google Cloud services before importing the app
from unittest.mock import patch, MagicMock

# Mock Firestore client
with patch("google.cloud.firestore.Client") as mock_firestore:
    mock_firestore.return_value = MagicMock()

    # Mock Secret Manager
    with patch(
        "google.cloud.secretmanager_v1.SecretManagerServiceClient"
    ) as mock_secret:
        mock_secret.return_value = MagicMock()

        # Mock Cloud SQL Connector
        with patch("google.cloud.sql.connector.Connector") as mock_connector:
            mock_connector.return_value = MagicMock()

            from app.main import app
from app.services.connection_manager import ConnectionManager
from app.services.schema_manager import SchemaManager
from app.services.role_manager import RoleManager
from app.services.user_manager import UserManager
from app.services.health_manager import HealthManager
from app.services.database_validator import DatabaseValidator


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def mock_connection():
    """Create a mock database connection."""
    connection = Mock()
    cursor = Mock()
    connection.cursor.return_value = cursor
    cursor.fetchone.return_value = None
    cursor.fetchall.return_value = []
    cursor.execute.return_value = None
    return connection


@pytest.fixture
def mock_cursor():
    """Create a mock database cursor."""
    cursor = Mock()
    cursor.fetchone.return_value = None
    cursor.fetchall.return_value = []
    cursor.execute.return_value = None
    return cursor


@pytest.fixture
def mock_connection_manager():
    """Create a mock connection manager."""
    manager = Mock(spec=ConnectionManager)
    manager.get_connection.return_value = Mock()
    manager.execute_sql_safely.return_value = {"success": True, "data": []}
    return manager


@pytest.fixture
def mock_schema_manager():
    """Create a mock schema manager."""
    manager = Mock(spec=SchemaManager)
    manager.create_schema.return_value = {
        "success": True,
        "message": "Schema created successfully",
        "schema_name": "test_schema",
        "execution_time_seconds": 0.1,
    }
    manager.list_schemas.return_value = {
        "success": True,
        "message": "Schemas retrieved successfully",
        "schemas": ["public", "test_schema"],
        "execution_time_seconds": 0.1,
    }
    manager.list_tables.return_value = {
        "success": True,
        "message": "Tables retrieved successfully",
        "tables": [],
        "execution_time_seconds": 0.1,
    }
    return manager


@pytest.fixture
def mock_role_manager():
    """Create a mock role manager."""
    manager = Mock(spec=RoleManager)
    manager.initialize_roles.return_value = {
        "success": True,
        "message": "Roles initialized successfully",
        "roles_created": ["test_reader", "test_writer"],
        "roles_updated": [],
        "roles_skipped": [],
        "total_roles": 2,
        "execution_time_seconds": 1.0,
    }
    manager.list_roles.return_value = {
        "success": True,
        "message": "Roles retrieved successfully",
        "roles": ["test_reader", "test_writer", "test_admin"],
        "execution_time_seconds": 0.1,
    }
    return manager


@pytest.fixture
def mock_user_manager():
    """Create a mock user manager."""
    manager = Mock(spec=UserManager)
    manager.grant_user_to_postgres.return_value = {
        "success": True,
        "message": "User granted to postgres successfully",
        "username": "test@project.iam",
        "execution_time_seconds": 0.1,
    }
    manager.revoke_user_from_postgres.return_value = {
        "success": True,
        "message": "User revoked from postgres successfully",
        "username": "test@project.iam",
        "execution_time_seconds": 0.1,
    }
    return manager


@pytest.fixture
def mock_health_manager():
    """Create a mock health manager."""
    manager = Mock(spec=HealthManager)
    manager.check_database_health.return_value = {
        "success": True,
        "message": "Database is healthy",
        "status": "healthy",
        "connection_time_ms": 50.0,
        "database_info": {"version": "PostgreSQL 15.4"},
        "execution_time_seconds": 0.1,
    }
    return manager


@pytest.fixture
def mock_database_validator():
    """Create a mock database validator."""
    validator = Mock(spec=DatabaseValidator)
    validator.role_exists.return_value = True
    validator.schema_exists.return_value = True
    validator.database_exists.return_value = True
    validator.is_iam_user.return_value = True
    validator.get_user_roles.return_value = ["test_reader", "test_writer"]
    return validator


@pytest.fixture
def sample_project_config():
    """Provide sample project configuration for tests."""
    return {
        "project_id": "test-project",
        "instance_name": "test-instance",
        "database_name": "test_database",
        "region": "europe-west1",
        "schema_name": "test_schema",
    }


@pytest.fixture
def sample_iam_user():
    """Provide sample IAM user for tests."""
    return "test-service@test-project.iam.gserviceaccount.com"


@pytest.fixture
def sample_role_name():
    """Provide sample role name for tests."""
    return "test_database_test_schema_reader"


@pytest.fixture
def sample_schema_data():
    """Provide sample schema data for tests."""
    return {
        "schema_name": "test_schema",
        "owner": "test-service@test-project.iam.gserviceaccount.com",
        "tables": [
            {
                "table_name": "users",
                "table_type": "BASE TABLE",
                "row_count": 1000,
                "size_bytes": 65536,
            },
            {
                "table_name": "orders",
                "table_type": "BASE TABLE",
                "row_count": 5000,
                "size_bytes": 131072,
            },
        ],
    }


@pytest.fixture
def sample_role_data():
    """Provide sample role data for tests."""
    return {
        "role_name": "test_database_test_schema_reader",
        "permissions": ["SELECT"],
        "inherits": [],
        "version": "1.0.0",
        "checksum": "abc123def456",
    }


# Test data fixtures
@pytest.fixture
def test_schemas():
    """Provide test schema names."""
    return ["public", "app_schema", "analytics_schema", "test_schema"]


@pytest.fixture
def test_tables():
    """Provide test table data."""
    return [
        {
            "table_name": "users",
            "table_type": "BASE TABLE",
            "row_count": 1000,
            "size_bytes": 65536,
        },
        {
            "table_name": "orders",
            "table_type": "BASE TABLE",
            "row_count": 5000,
            "size_bytes": 131072,
        },
        {
            "table_name": "products",
            "table_type": "BASE TABLE",
            "row_count": 500,
            "size_bytes": 32768,
        },
    ]


@pytest.fixture
def test_roles():
    """Provide test role names."""
    return [
        "test_database_test_schema_reader",
        "test_database_test_schema_writer",
        "test_database_test_schema_admin",
        "test_database_test_schema_analyst",
        "test_database_monitor",  # Database-wide role
        "test_database_dba_agent",  # Database-wide role
    ]


@pytest.fixture
def test_users():
    """Provide test user data."""
    return [
        {
            "username": "service1@test-project.iam.gserviceaccount.com",
            "roles": ["test_database_test_schema_reader"],
            "is_iam_user": True,
        },
        {
            "username": "service2@test-project.iam.gserviceaccount.com",
            "roles": [
                "test_database_test_schema_writer",
                "test_database_test_schema_reader",
            ],
            "is_iam_user": True,
        },
        {
            "username": "admin@test-project.iam.gserviceaccount.com",
            "roles": ["test_database_test_schema_admin"],
            "is_iam_user": True,
        },
    ]
