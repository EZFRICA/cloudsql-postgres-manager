"""
Integration tests for role endpoints.

Tests the role management functionality including initialization, assignment, and listing.
"""

from unittest.mock import patch, Mock


class TestRoleEndpoints:
    """Test cases for role endpoints."""

    def test_initialize_roles_success(self, client, sample_project_config):
        """Test successful role initialization."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "schema_name": sample_project_config["schema_name"],
            "force_update": False,
        }

        with patch("app.routers.roles.role_manager") as mock_manager:
            # Create a mock object with the expected attributes
            mock_result = Mock()
            mock_result.success = True
            mock_result.message = "Roles initialized successfully"
            mock_result.roles_created = ["test_reader", "test_writer", "test_admin"]
            mock_result.roles_updated = []
            mock_result.roles_skipped = []
            mock_result.total_roles = 3
            mock_result.firebase_document_id = (
                "test-project_test-instance_test_database"
            )
            mock_result.execution_time_seconds = 2.5

            mock_manager.initialize_roles.return_value = mock_result

            # Act
            response = client.post("/roles/initialize", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["roles_created"]) == 3
            assert data["total_roles"] == 3

    def test_initialize_roles_with_force_update(self, client, sample_project_config):
        """Test role initialization with force update."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "schema_name": sample_project_config["schema_name"],
            "force_update": True,
        }

        with patch("app.routers.roles.role_manager") as mock_manager:
            # Create a mock object with the expected attributes
            mock_result = Mock()
            mock_result.success = True
            mock_result.message = "Roles updated successfully"
            mock_result.roles_created = []
            mock_result.roles_updated = ["test_reader", "test_writer"]
            mock_result.roles_skipped = ["test_admin"]
            mock_result.total_roles = 3
            mock_result.firebase_document_id = (
                "test-project_test-instance_test_database"
            )
            mock_result.execution_time_seconds = 1.8

            mock_manager.initialize_roles.return_value = mock_result

            # Act
            response = client.post("/roles/initialize", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["roles_updated"]) == 2
            assert len(data["roles_skipped"]) == 1

    def test_assign_role_success(
        self, client, sample_project_config, sample_iam_user, sample_role_name
    ):
        """Test successful role assignment."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "schema_name": sample_project_config["schema_name"],
            "username": sample_iam_user,
            "role_name": sample_role_name,
        }

        with patch("app.routers.roles.role_permission_manager") as mock_manager:
            mock_manager.assign_role.return_value = {
                "success": True,
                "message": "Role assigned successfully",
                "username": sample_iam_user,
                "role_name": sample_role_name,
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "schema_name": sample_project_config["schema_name"],
                "execution_time_seconds": 0.5,
            }

            # Act
            response = client.post("/roles/assign", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["username"] == sample_iam_user
            assert data["role_name"] == sample_role_name

    def test_revoke_role_success(
        self, client, sample_project_config, sample_iam_user, sample_role_name
    ):
        """Test successful role revocation."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "schema_name": sample_project_config["schema_name"],
            "username": sample_iam_user,
            "role_name": sample_role_name,
        }

        with patch("app.routers.roles.role_permission_manager") as mock_manager:
            mock_manager.revoke_role.return_value = {
                "success": True,
                "message": "Role revoked successfully",
                "username": sample_iam_user,
                "role_name": sample_role_name,
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "schema_name": sample_project_config["schema_name"],
                "execution_time_seconds": 0.3,
            }

            # Act
            response = client.post("/roles/revoke", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["username"] == sample_iam_user
            assert data["role_name"] == sample_role_name

    def test_list_roles_success(self, client, sample_project_config, test_roles):
        """Test successful role listing."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "schema_name": sample_project_config["schema_name"],
        }

        with patch("app.routers.roles.role_manager") as mock_manager:
            mock_manager.list_roles.return_value = {
                "success": True,
                "message": f"Retrieved {len(test_roles)} roles",
                "roles": test_roles,
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "execution_time_seconds": 0.2,
            }

            # Act
            response = client.post("/roles/list", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["roles"] == test_roles
            assert len(data["roles"]) == len(test_roles)

    def test_list_users_success(self, client, sample_project_config, test_users):
        """Test successful user listing."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "schema_name": sample_project_config["schema_name"],
        }

        with patch("app.routers.roles.user_manager") as mock_manager:
            # Create a mock object with the expected attributes
            mock_result = {
                "success": True,
                "message": f"Retrieved {len(test_users)} users",
                "users": test_users,
                "project_id": sample_project_config["project_id"],
                "instance_name": sample_project_config["instance_name"],
                "database_name": sample_project_config["database_name"],
                "schema_name": sample_project_config["schema_name"],
                "execution_time_seconds": 0.4,
            }

            mock_manager.get_users_and_roles.return_value = mock_result

            # Act
            response = client.post("/roles/users", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["users"] == test_users
            assert len(data["users"]) == len(test_users)

    def test_role_status_success(self, client, sample_project_config):
        """Test successful role status check."""
        # Arrange
        with patch("app.routers.roles.role_manager") as mock_manager:
            mock_manager.get_role_status.return_value = {
                "success": True,
                "message": "Role status retrieved successfully",
                "roles_initialized": True,
                "total_roles": 5,
                "last_updated": "2024-01-15T10:00:00Z",
                "firebase_document_id": "test-project_test-instance_test_database",
            }

            # Act
            response = client.get(
                "/roles/status",
                params={
                    "project_id": sample_project_config["project_id"],
                    "instance_name": sample_project_config["instance_name"],
                    "database_name": sample_project_config["database_name"],
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["roles_initialized"] is True

    def test_validation_error_missing_fields(self, client):
        """Test validation error with missing required fields."""
        # Arrange
        request_data = {
            "project_id": "test-project"
            # Missing required fields
        }

        # Act
        response = client.post("/roles/initialize", json=request_data)

        # Assert
        assert response.status_code == 422  # Validation Error

    def test_validation_error_invalid_username(
        self, client, sample_project_config, sample_role_name
    ):
        """Test validation error with invalid username format."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "schema_name": sample_project_config["schema_name"],
            "username": "invalid-username",  # Invalid format
            "role_name": sample_role_name,
        }

        # Act
        response = client.post("/roles/assign", json=request_data)

        # Assert
        assert (
            response.status_code == 200
        )  # The API handles invalid usernames gracefully
        data = response.json()
        assert data["success"] is False
        assert "Failed to assign role" in data["message"]

    def test_service_error_handling(self, client, sample_project_config):
        """Test service error handling."""
        # Arrange
        request_data = {
            "project_id": sample_project_config["project_id"],
            "instance_name": sample_project_config["instance_name"],
            "database_name": sample_project_config["database_name"],
            "region": sample_project_config["region"],
            "schema_name": sample_project_config["schema_name"],
            "force_update": False,
        }

        with patch("app.routers.roles.role_manager") as mock_manager:
            mock_manager.initialize_roles.side_effect = Exception(
                "Database connection failed"
            )

            # Act
            response = client.post("/roles/initialize", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Database connection failed" in data["message"]

    def test_method_not_allowed(self, client, sample_project_config):
        """Test unsupported HTTP methods."""

        # Act
        response = client.get("/roles/initialize")

        # Assert
        assert response.status_code == 405  # Method Not Allowed
