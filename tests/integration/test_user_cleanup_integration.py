"""
Integration tests for user cleanup functionality.

Tests the complete workflow of cleaning up a user before deletion.
"""

from unittest.mock import Mock, patch
from app.services.user_manager import UserManager
from app.services.connection_manager import ConnectionManager


class TestUserCleanupIntegration:
    """Integration test cases for user cleanup workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_connection_manager = Mock(spec=ConnectionManager)
        self.user_manager = UserManager(self.mock_connection_manager)

    def test_complete_cleanup_workflow_success(self):
        """Test the complete cleanup workflow for a user with objects."""
        # Arrange
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)
        self.mock_connection_manager.get_connection.return_value = mock_connection

        username = "test@project.iam"
        database_name = "testdb"
        schema_name = "testschema"

        # Mock successful SQL executions
        self.mock_connection_manager.execute_sql_safely.return_value = True

        # Mock the permission revocation to succeed
        with patch.object(
            self.user_manager, "_revoke_all_schemas_permissions", return_value=True
        ):
            # Act
            result = self.user_manager.cleanup_user_before_deletion(
                mock_cursor, username, database_name, schema_name
            )

            # Assert
            assert result is True

            # Verify the complete workflow was executed
            expected_calls = [
                ('REASSIGN OWNED BY "test@project.iam" TO postgres',),
                ('DROP OWNED BY "test@project.iam"',),
            ]

            actual_calls = [
                call[0][1]
                for call in self.mock_connection_manager.execute_sql_safely.call_args_list
            ]

            for expected_call in expected_calls:
                assert expected_call[0] in actual_calls

    def test_cleanup_workflow_with_multiple_schemas(self):
        """Test cleanup workflow affecting multiple schemas."""
        # Arrange
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)
        self.mock_connection_manager.get_connection.return_value = mock_connection

        username = "test@project.iam"
        database_name = "testdb"

        # Mock successful SQL executions
        self.mock_connection_manager.execute_sql_safely.return_value = True

        # Mock cursor to return multiple schemas
        mock_cursor.fetchall.return_value = [("schema1",), ("schema2",), ("schema3",)]

        # Mock the role permission manager
        mock_role_permission_manager = Mock()
        mock_role_permission_manager.revoke_all_permissions.return_value = True

        with (
            patch(
                "app.services.role_permission_manager.RolePermissionManager"
            ) as mock_rpm_class,
            patch("app.services.schema_manager.SchemaManager") as mock_sm_class,
        ):
            mock_rpm_class.return_value = mock_role_permission_manager
            mock_sm_class.return_value = Mock()

            # Act
            result = self.user_manager.cleanup_user_before_deletion(
                mock_cursor, username, database_name
            )

            # Assert
            assert result is True

            # Verify permissions were revoked from all schemas
            assert mock_role_permission_manager.revoke_all_permissions.call_count == 3

            # Verify the schema query was executed
            mock_cursor.execute.assert_called_once()

    def test_cleanup_workflow_with_permission_failures(self):
        """Test cleanup workflow when some permission revocations fail."""
        # Arrange
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)
        self.mock_connection_manager.get_connection.return_value = mock_connection

        username = "test@project.iam"
        database_name = "testdb"

        # Mock successful SQL executions for ownership transfer
        self.mock_connection_manager.execute_sql_safely.return_value = True

        # Mock the permission revocation to fail
        with patch.object(
            self.user_manager, "_revoke_all_schemas_permissions", return_value=False
        ):
            # Act
            result = self.user_manager.cleanup_user_before_deletion(
                mock_cursor, username, database_name
            )

            # Assert
            assert result is True  # Should still succeed despite permission failures

            # Verify ownership transfer still happened
            self.mock_connection_manager.execute_sql_safely.assert_any_call(
                mock_cursor, 'REASSIGN OWNED BY "test@project.iam" TO postgres'
            )

    def test_cleanup_workflow_with_ownership_transfer_failure(self):
        """Test cleanup workflow when ownership transfer fails."""
        # Arrange
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)
        self.mock_connection_manager.get_connection.return_value = mock_connection

        username = "test@project.iam"
        database_name = "testdb"

        # Mock the connection manager to fail on REASSIGN OWNED BY
        def mock_execute_sql_safely(cursor, sql):
            if "REASSIGN OWNED BY" in sql:
                return False
            return True

        self.mock_connection_manager.execute_sql_safely.side_effect = (
            mock_execute_sql_safely
        )

        # Act
        result = self.user_manager.cleanup_user_before_deletion(
            mock_cursor, username, database_name
        )

        # Assert
        assert result is False  # Should fail if ownership transfer fails

    def test_cleanup_workflow_with_drop_owned_failure(self):
        """Test cleanup workflow when DROP OWNED BY fails."""
        # Arrange
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)
        self.mock_connection_manager.get_connection.return_value = mock_connection

        username = "test@project.iam"
        database_name = "testdb"

        # Mock the connection manager to fail on DROP OWNED BY
        def mock_execute_sql_safely(cursor, sql):
            if "DROP OWNED BY" in sql:
                return False
            return True

        self.mock_connection_manager.execute_sql_safely.side_effect = (
            mock_execute_sql_safely
        )

        # Mock successful permission revocation
        with patch.object(
            self.user_manager, "_revoke_all_schemas_permissions", return_value=True
        ):
            # Act
            result = self.user_manager.cleanup_user_before_deletion(
                mock_cursor, username, database_name
            )

            # Assert
            assert result is True  # Should still succeed despite DROP OWNED BY failure

    def test_cleanup_workflow_with_exception(self):
        """Test cleanup workflow when an exception occurs."""
        # Arrange
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)
        self.mock_connection_manager.get_connection.return_value = mock_connection

        username = "test@project.iam"
        database_name = "testdb"

        # Mock the connection manager to raise an exception
        self.mock_connection_manager.execute_sql_safely.side_effect = Exception(
            "Database connection lost"
        )

        # Act
        result = self.user_manager.cleanup_user_before_deletion(
            mock_cursor, username, database_name
        )

        # Assert
        assert result is False

    def test_cleanup_workflow_with_normalized_username(self):
        """Test cleanup workflow with username normalization."""
        # Arrange
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)
        self.mock_connection_manager.get_connection.return_value = mock_connection

        username = "test@project.iam.gserviceaccount.com"  # Full service account name
        database_name = "testdb"

        # Mock successful SQL executions
        self.mock_connection_manager.execute_sql_safely.return_value = True

        # Mock the permission revocation to succeed
        with patch.object(
            self.user_manager, "_revoke_all_schemas_permissions", return_value=True
        ):
            # Act
            result = self.user_manager.cleanup_user_before_deletion(
                mock_cursor, username, database_name
            )

            # Assert
            assert result is True

            # Verify the normalized username was used in SQL commands
            self.mock_connection_manager.execute_sql_safely.assert_any_call(
                mock_cursor, 'REASSIGN OWNED BY "test@project.iam" TO postgres'
            )
            self.mock_connection_manager.execute_sql_safely.assert_any_call(
                mock_cursor, 'DROP OWNED BY "test@project.iam"'
            )
