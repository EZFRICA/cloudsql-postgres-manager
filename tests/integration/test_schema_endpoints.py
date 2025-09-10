"""
Integration tests for schema endpoints.

Tests the schema creation and management functionality.
"""

from unittest.mock import patch


class TestSchemaEndpoints:
    """Test cases for schema endpoints."""

    def test_create_schema_success(self, client, sample_project_config):
        """Test successful schema creation."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "schema_name": sample_project_config["schema_name"],
            "owner": "test@project.iam.gserviceaccount.com",
        }

        with patch("app.routers.schemas.schema_manager") as mock_manager:
            mock_manager.create_schema.return_value = {
                "success": True,
                "message": "Schema created successfully",
                "schema_name": sample_project_config["schema_name"],
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "execution_time_seconds": 0.5,
            }

            # Act
            response = client.post("/schemas/create", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["schema_name"] == sample_project_config["schema_name"]
            assert "execution_time_seconds" in data

    def test_create_schema_without_owner(self, client, sample_project_config):
        """Test schema creation without specifying owner."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "schema_name": sample_project_config["schema_name"],
        }

        with patch("app.routers.schemas.schema_manager") as mock_manager:
            mock_manager.create_schema.return_value = {
                "success": True,
                "message": "Schema created successfully",
                "schema_name": sample_project_config["schema_name"],
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "execution_time_seconds": 0.5,
            }

            # Act
            response = client.post("/schemas/create", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_create_schema_validation_error(self, client):
        """Test schema creation with validation error."""
        # Arrange
        request_data = {
            "project_id": "",  # Invalid empty project ID
            "instance_name": "test-instance",
            "database_name": "test_database",
            "region": "europe-west1",
            "schema_name": "test_schema",
        }

        # Act
        response = client.post("/schemas/create", json=request_data)

        # Assert
        assert response.status_code == 422  # Validation Error

    def test_create_schema_missing_fields(self, client):
        """Test schema creation with missing required fields."""
        # Arrange
        request_data = {
            "project_id": "test-project",
            "instance_name": "test-instance",
            # Missing required fields
        }

        # Act
        response = client.post("/schemas/create", json=request_data)

        # Assert
        assert response.status_code == 422  # Validation Error

    def test_create_schema_invalid_schema_name(self, client, sample_project_config):
        """Test schema creation with invalid schema name."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "schema_name": "invalid-schema-name",  # Invalid name with hyphen
        }

        with patch("app.routers.schemas.schema_manager") as mock_manager:
            mock_manager.create_schema.return_value = {
                "success": False,
                "message": "Invalid schema name: invalid-schema-name",
                "schema_name": "invalid-schema-name",
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "execution_time_seconds": 0.1,
            }

            # Act
            response = client.post("/schemas/create", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Invalid schema name" in data["message"]

    def test_create_schema_service_error(self, client, sample_project_config):
        """Test schema creation with service error."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "schema_name": sample_project_config["schema_name"],
        }

        with patch("app.routers.schemas.schema_manager") as mock_manager:
            mock_manager.create_schema.side_effect = Exception(
                "Database connection failed"
            )

            # Act
            response = client.post("/schemas/create", json=request_data)

            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Database connection failed" in data["detail"]

    def test_create_schema_content_type(self, client, sample_project_config):
        """Test schema creation content type."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "schema_name": sample_project_config["schema_name"],
        }

        with patch("app.routers.schemas.schema_manager") as mock_manager:
            mock_manager.create_schema.return_value = {
                "success": True,
                "message": "Schema created successfully",
                "schema_name": sample_project_config["schema_name"],
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "execution_time_seconds": 0.5,
            }

            # Act
            response = client.post("/schemas/create", json=request_data)

            # Assert
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"

    def test_create_schema_method_not_allowed(self, client, sample_project_config):
        """Test schema creation with unsupported HTTP method."""

        # Act
        response = client.get("/schemas/create")

        # Assert
        assert response.status_code == 405  # Method Not Allowed
