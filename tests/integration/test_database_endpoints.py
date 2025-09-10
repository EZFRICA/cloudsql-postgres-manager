"""
Integration tests for database endpoints.

Tests the database management functionality including schema listing, table listing, and health checks.
"""

from unittest.mock import patch


class TestDatabaseEndpoints:
    """Test cases for database endpoints."""

    def test_list_schemas_success(self, client, sample_project_config, test_schemas):
        """Test successful schema listing."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
        }

        with patch("app.routers.database.schema_manager") as mock_manager:
            mock_manager.list_schemas.return_value = {
                "success": True,
                "message": f"Retrieved {len(test_schemas)} schemas",
                "schemas": test_schemas,
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "execution_time_seconds": 0.2,
            }

            # Act
            response = client.post("/database/schemas", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["schemas"] == test_schemas
            assert len(data["schemas"]) == len(test_schemas)

    def test_list_schemas_empty(self, client, sample_project_config):
        """Test schema listing with no schemas."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
        }

        with patch("app.routers.database.schema_manager") as mock_manager:
            mock_manager.list_schemas.return_value = {
                "success": True,
                "message": "Retrieved 0 schemas",
                "schemas": [],
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "execution_time_seconds": 0.1,
            }

            # Act
            response = client.post("/database/schemas", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["schemas"] == []

    def test_list_tables_success(self, client, sample_project_config, test_tables):
        """Test successful table listing."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "schema_name": sample_project_config["schema_name"],
        }

        with patch("app.routers.database.schema_manager") as mock_manager:
            mock_manager.list_tables.return_value = {
                "success": True,
                "message": f"Retrieved {len(test_tables)} tables",
                "tables": test_tables,
                "schema_name": sample_project_config["schema_name"],
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "execution_time_seconds": 0.3,
            }

            # Act
            response = client.post("/database/tables", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["tables"] == test_tables
            assert len(data["tables"]) == len(test_tables)

    def test_database_health_check_success(self, client, sample_project_config):
        """Test successful database health check."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
        }

        with patch("app.routers.database.health_manager") as mock_manager:
            mock_manager.check_database_health.return_value = {
                "success": True,
                "message": "Database is healthy",
                "status": "healthy",
                "connection_time_ms": 45.2,
                "database_info": {
                    "version": "PostgreSQL 15.4",
                    "uptime": "5 days, 12 hours",
                    "active_connections": 15,
                },
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "execution_time_seconds": 0.1,
            }

            # Act
            response = client.post("/database/health", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "healthy"
            assert "connection_time_ms" in data
            assert "database_info" in data

    def test_database_health_check_unhealthy(self, client, sample_project_config):
        """Test database health check when database is unhealthy."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
        }

        with patch("app.routers.database.health_manager") as mock_manager:
            mock_manager.check_database_health.return_value = {
                "success": False,
                "message": "Database connection failed",
                "status": "unhealthy",
                "connection_time_ms": None,
                "database_info": None,
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "execution_time_seconds": 5.0,
            }

            # Act
            response = client.post("/database/health", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert data["status"] == "unhealthy"

    def test_postgres_inheritance_grant_success(
        self, client, sample_project_config, sample_iam_user
    ):
        """Test successful postgres inheritance grant."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "username": sample_iam_user,
        }

        with patch("app.routers.database.user_manager") as mock_manager:
            mock_manager.grant_user_to_postgres.return_value = {
                "success": True,
                "message": "User granted to postgres successfully",
                "username": sample_iam_user,
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "execution_time_seconds": 0.5,
            }

            # Act
            response = client.post(
                "/database/postgres-inheritance/grant", json=request_data
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["username"] == sample_iam_user

    def test_postgres_inheritance_revoke_success(
        self, client, sample_project_config, sample_iam_user
    ):
        """Test successful postgres inheritance revoke."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "username": sample_iam_user,
        }

        with patch("app.routers.database.user_manager") as mock_manager:
            mock_manager.revoke_user_from_postgres.return_value = {
                "success": True,
                "message": "User revoked from postgres successfully",
                "username": sample_iam_user,
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "execution_time_seconds": 0.3,
            }

            # Act
            response = client.post(
                "/database/postgres-inheritance/revoke", json=request_data
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["username"] == sample_iam_user

    def test_validation_error_missing_fields(self, client):
        """Test validation error with missing required fields."""
        # Arrange
        request_data = {
            "project_id": "test-project"
            # Missing required fields
        }

        # Act
        response = client.post("/database/schemas", json=request_data)

        # Assert
        assert response.status_code == 422  # Validation Error

    def test_validation_error_invalid_data_types(self, client):
        """Test validation error with invalid data types."""
        # Arrange
        request_data = {
            "project_id": 123,  # Should be string
            "instance_name": "test-instance",
            "database_name": "test_database",
            "region": "europe-west1",
        }

        # Act
        response = client.post("/database/schemas", json=request_data)

        # Assert
        assert response.status_code == 422  # Validation Error

    def test_service_error_handling(self, client, sample_project_config):
        """Test service error handling."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
        }

        with patch("app.routers.database.schema_manager") as mock_manager:
            mock_manager.list_schemas.side_effect = Exception(
                "Database connection failed"
            )

            # Act
            response = client.post("/database/schemas", json=request_data)

            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Database connection failed" in data["detail"]

    def test_method_not_allowed(self, client, sample_project_config):
        """Test unsupported HTTP methods."""

        # Act
        response = client.get("/database/schemas")

        # Assert
        assert response.status_code == 405  # Method Not Allowed
