"""
Unit tests for ConnectionManager service.

Tests the connection pooling and database isolation functionality.
"""

from unittest.mock import patch, MagicMock
from app.services.connection_manager import ConnectionManager


class TestConnectionManager:
    """Test cases for ConnectionManager."""

    def test_pool_key_includes_database_name(self):
        """Test that pool keys include database name for proper isolation."""
        # Arrange
        cm = ConnectionManager()

        # Act
        key1 = cm._get_pool_key("project1", "region1", "instance1", "database1")
        key2 = cm._get_pool_key("project1", "region1", "instance1", "database2")
        key3 = cm._get_pool_key("project1", "region1", "instance1", "database1")

        # Assert
        assert key1 == "project1:region1:instance1:database1"
        assert key2 == "project1:region1:instance1:database2"
        assert key1 != key2, "Different databases should have different pool keys"
        assert key1 == key3, "Same database should have same pool key"

    def test_pool_key_different_for_different_databases_same_instance(self):
        """Test that different databases on same instance get different pool keys."""
        # Arrange
        cm = ConnectionManager()

        # Act
        dbtest_key = cm._get_pool_key("test-project", "europe-west9", "iamdb", "dbtest")
        workdb_key = cm._get_pool_key("test-project", "europe-west9", "iamdb", "workdb")

        # Assert
        assert dbtest_key != workdb_key, (
            "Different databases on same instance should have different pool keys"
        )
        assert "dbtest" in dbtest_key
        assert "workdb" in workdb_key

    @patch("app.services.connection_manager.ConnectionPool")
    def test_get_or_create_pool_uses_database_name(self, mock_pool_class):
        """Test that _get_or_create_pool uses database name in pool key."""
        # Arrange
        cm = ConnectionManager()
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        # Act
        pool1 = cm._get_or_create_pool("project1", "region1", "instance1", "database1")
        pool2 = cm._get_or_create_pool("project1", "region1", "instance1", "database2")

        # Assert
        assert pool1 == mock_pool
        assert pool2 == mock_pool
        # Should create separate pools for different databases
        assert mock_pool_class.call_count == 2

    def test_pool_key_format(self):
        """Test that pool key follows expected format."""
        # Arrange
        cm = ConnectionManager()

        # Act
        key = cm._get_pool_key(
            "my-project", "europe-west1", "my-instance", "my-database"
        )

        # Assert
        expected_format = "my-project:europe-west1:my-instance:my-database"
        assert key == expected_format
        assert key.count(":") == 3, "Pool key should have exactly 3 colons"
