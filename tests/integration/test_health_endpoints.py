"""
Integration tests for health endpoints.

Tests the health check functionality.
"""


class TestHealthEndpoints:
    """Test cases for health endpoints."""

    def test_health_check_success(self, client):
        """Test successful health check."""
        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Cloud SQL IAM User Permission Manager"
        assert data["version"] == "0.1.0"

    def test_health_check_response_structure(self, client):
        """Test health check response structure."""
        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify required fields
        required_fields = ["status", "service", "version"]
        for field in required_fields:
            assert field in data
            assert data[field] is not None
            assert isinstance(data[field], str)

    def test_health_check_content_type(self, client):
        """Test health check content type."""
        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_health_check_method_not_allowed(self, client):
        """Test health check with unsupported HTTP method."""
        # Act
        response = client.post("/health")

        # Assert
        assert response.status_code == 405  # Method Not Allowed

    def test_health_check_with_query_params(self, client):
        """Test health check with query parameters (should be ignored)."""
        # Act
        response = client.get("/health?check=detailed")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
