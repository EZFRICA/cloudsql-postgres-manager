"""
Integration tests for schema database isolation.

Tests that schemas are properly isolated between different databases
on the same Cloud SQL instance.
"""

from unittest.mock import patch, MagicMock
from app.services.schema_manager import SchemaManager
from app.services.connection_manager import ConnectionManager


class TestSchemaDatabaseIsolation:
    """Test cases for schema isolation between databases."""

    @patch("app.services.connection_manager.ConnectionManager.get_connection")
    def test_schema_exists_check_is_database_specific(self, mock_get_connection):
        """Test that schema existence check is specific to the target database."""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value.__enter__.return_value = mock_conn

        # Simulate different schemas in different databases
        def mock_execute(sql, params=None):
            if "information_schema.schemata" in sql:
                if params and params[0] == "sa_schema":
                    # Simulate that sa_schema exists in dbtest but not in workdb
                    if "dbtest" in str(mock_get_connection.call_args):
                        mock_cursor.fetchone.return_value = (1,)  # Schema exists
                    else:
                        mock_cursor.fetchone.return_value = None  # Schema doesn't exist
                else:
                    mock_cursor.fetchone.return_value = None
            else:
                mock_cursor.fetchone.return_value = None

        mock_cursor.execute.side_effect = mock_execute

        cm = ConnectionManager()
        sm = SchemaManager(cm)

        # Act & Assert - Test dbtest (schema should exist)
        result_dbtest = sm.create_schema(
            project_id="test-project",
            region="europe-west9",
            instance_name="iamdb",
            database_name="dbtest",
            schema_name="sa_schema",
        )

        # Should return "already exists" for dbtest
        assert result_dbtest["success"] is True
        assert "already exists" in result_dbtest["message"]

        # Act & Assert - Test workdb (schema should not exist)
        result_workdb = sm.create_schema(
            project_id="test-project",
            region="europe-west9",
            instance_name="iamdb",
            database_name="workdb",
            schema_name="sa_schema",
        )

        # Should create the schema in workdb
        assert result_workdb["success"] is True
        assert "created successfully" in result_workdb["message"]

    def test_connection_manager_creates_separate_pools_for_different_databases(self):
        """Test that ConnectionManager creates separate pools for different databases."""
        # Arrange
        cm = ConnectionManager()

        # Act
        pool_key_dbtest = cm._get_pool_key(
            "test-project", "europe-west9", "iamdb", "dbtest"
        )
        pool_key_workdb = cm._get_pool_key(
            "test-project", "europe-west9", "iamdb", "workdb"
        )

        # Assert
        assert pool_key_dbtest != pool_key_workdb
        assert "dbtest" in pool_key_dbtest
        assert "workdb" in pool_key_workdb

        # Verify they would create separate pools
        pool1 = cm._get_or_create_pool(
            "test-project", "europe-west9", "iamdb", "dbtest"
        )
        pool2 = cm._get_or_create_pool(
            "test-project", "europe-west9", "iamdb", "workdb"
        )

        # These should be different pool objects
        assert pool1 is not pool2
