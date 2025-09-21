"""
Unit tests for UserManager service.

Tests the user management operations including cleanup functionality.
"""

from unittest.mock import Mock, patch
from app.services.user_manager import UserManager


class TestUserManager:
    """Test cases for UserManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_connection_manager = Mock()
        self.user_manager = UserManager(self.mock_connection_manager)

    def test_cleanup_user_before_deletion_success(self):
        """Test successful user cleanup before deletion."""
        # Arrange
        mock_cursor = Mock()
        username = "test@project.iam"
        database_name = "testdb"
        schema_name = "testschema"

        # Mock the connection manager to return True for SQL executions
        self.mock_connection_manager.execute_sql_safely.return_value = True

        # Mock the helper method to return True
        with patch.object(
            self.user_manager, "_revoke_all_schemas_permissions", return_value=True
        ):
            # Act
            result = self.user_manager.cleanup_user_before_deletion(
                mock_cursor, username, database_name, schema_name
            )

            # Assert
            assert result is True
            # Verify REASSIGN OWNED BY was called
            self.mock_connection_manager.execute_sql_safely.assert_any_call(
                mock_cursor, 'REASSIGN OWNED BY "test@project.iam" TO postgres'
            )
            # Verify DROP OWNED BY was called
            self.mock_connection_manager.execute_sql_safely.assert_any_call(
                mock_cursor, 'DROP OWNED BY "test@project.iam"'
            )

    def test_cleanup_user_before_deletion_all_schemas(self):
        """Test user cleanup for all schemas (no specific schema)."""
        # Arrange
        mock_cursor = Mock()
        username = "test@project.iam"
        database_name = "testdb"

        # Mock the connection manager to return True for SQL executions
        self.mock_connection_manager.execute_sql_safely.return_value = True

        # Mock the helper method to return True
        with patch.object(
            self.user_manager, "_revoke_all_schemas_permissions", return_value=True
        ):
            # Act
            result = self.user_manager.cleanup_user_before_deletion(
                mock_cursor, username, database_name
            )

            # Assert
            assert result is True
            # Verify REASSIGN OWNED BY was called
            self.mock_connection_manager.execute_sql_safely.assert_any_call(
                mock_cursor, 'REASSIGN OWNED BY "test@project.iam" TO postgres'
            )

    def test_cleanup_user_before_deletion_reassign_failure(self):
        """Test cleanup failure when REASSIGN OWNED BY fails."""
        # Arrange
        mock_cursor = Mock()
        username = "test@project.iam"
        database_name = "testdb"

        # Mock the connection manager to return False for REASSIGN
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
        assert result is False

    def test_cleanup_user_before_deletion_permission_revoke_failure(self):
        """Test cleanup when permission revocation fails but continues."""
        # Arrange
        mock_cursor = Mock()
        username = "test@project.iam"
        database_name = "testdb"

        # Mock the connection manager to return True for SQL executions
        self.mock_connection_manager.execute_sql_safely.return_value = True

        # Mock the helper method to return False (permission revocation failed)
        with patch.object(
            self.user_manager, "_revoke_all_schemas_permissions", return_value=False
        ):
            # Act
            result = self.user_manager.cleanup_user_before_deletion(
                mock_cursor, username, database_name
            )

            # Assert
            assert (
                result is True
            )  # Should still succeed despite permission revocation failure

    def test_cleanup_user_before_deletion_exception(self):
        """Test cleanup when an exception occurs."""
        # Arrange
        mock_cursor = Mock()
        username = "test@project.iam"
        database_name = "testdb"

        # Mock the connection manager to raise an exception
        self.mock_connection_manager.execute_sql_safely.side_effect = Exception(
            "Database error"
        )

        # Act
        result = self.user_manager.cleanup_user_before_deletion(
            mock_cursor, username, database_name
        )

        # Assert
        assert result is False

    def test_revoke_all_schemas_permissions_specific_schemas(self):
        """Test revoking permissions from specific schemas."""
        # Arrange
        mock_cursor = Mock()
        username = "test@project.iam"
        database_name = "testdb"
        specific_schemas = ["schema1", "schema2"]

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
            result = self.user_manager._revoke_all_schemas_permissions(
                mock_cursor, username, database_name, specific_schemas
            )

            # Assert
            assert result is True
            assert mock_role_permission_manager.revoke_all_permissions.call_count == 2
            mock_role_permission_manager.revoke_all_permissions.assert_any_call(
                mock_cursor, username, database_name, "schema1"
            )
            mock_role_permission_manager.revoke_all_permissions.assert_any_call(
                mock_cursor, username, database_name, "schema2"
            )

    def test_revoke_all_schemas_permissions_all_schemas(self):
        """Test revoking permissions from all schemas in database."""
        # Arrange
        mock_cursor = Mock()
        username = "test@project.iam"
        database_name = "testdb"

        # Mock cursor to return schemas
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
            result = self.user_manager._revoke_all_schemas_permissions(
                mock_cursor, username, database_name
            )

            # Assert
            assert result is True
            assert mock_role_permission_manager.revoke_all_permissions.call_count == 3
            # Verify the SQL query was executed to get schemas
            mock_cursor.execute.assert_called_once()

    def test_revoke_all_schemas_permissions_partial_failure(self):
        """Test revoking permissions when some schemas fail."""
        # Arrange
        mock_cursor = Mock()
        username = "test@project.iam"
        database_name = "testdb"
        specific_schemas = ["schema1", "schema2"]

        # Mock the role permission manager to fail on second call
        mock_role_permission_manager = Mock()
        mock_role_permission_manager.revoke_all_permissions.side_effect = [True, False]

        with (
            patch(
                "app.services.role_permission_manager.RolePermissionManager"
            ) as mock_rpm_class,
            patch("app.services.schema_manager.SchemaManager") as mock_sm_class,
        ):
            mock_rpm_class.return_value = mock_role_permission_manager
            mock_sm_class.return_value = Mock()

            # Act
            result = self.user_manager._revoke_all_schemas_permissions(
                mock_cursor, username, database_name, specific_schemas
            )

            # Assert
            assert result is False  # Should return False if any revocation fails

    def test_revoke_all_schemas_permissions_exception(self):
        """Test revoking permissions when an exception occurs."""
        # Arrange
        mock_cursor = Mock()
        username = "test@project.iam"
        database_name = "testdb"

        # Mock cursor to raise an exception
        mock_cursor.execute.side_effect = Exception("Database error")

        # Act
        result = self.user_manager._revoke_all_schemas_permissions(
            mock_cursor, username, database_name
        )

        # Assert
        assert result is False

    def test_user_exists_valid_iam_user(self):
        """Test user_exists with a valid IAM user."""
        # Arrange
        mock_cursor = Mock()
        username = "test@project.iam"

        with patch(
            "app.services.user_manager.DatabaseValidator.is_iam_user", return_value=True
        ):
            # Act
            result = self.user_manager.user_exists(mock_cursor, username)

            # Assert
            assert result is True

    def test_user_exists_invalid_user(self):
        """Test user_exists with an invalid user."""
        # Arrange
        mock_cursor = Mock()
        username = "invalid@project.iam"

        with patch(
            "app.services.user_manager.DatabaseValidator.is_iam_user",
            return_value=False,
        ):
            # Act
            result = self.user_manager.user_exists(mock_cursor, username)

            # Assert
            assert result is False

    def test_is_valid_iam_user_success(self):
        """Test is_valid_iam_user with a valid user."""
        # Arrange
        mock_cursor = Mock()
        username = "test@project.iam"

        # Mock cursor to return user info
        mock_cursor.fetchone.return_value = (
            "test@project.iam",  # rolname
            True,  # rolcanlogin
            False,  # rolsuper
            False,  # rolcreatedb
            False,  # rolcreaterole
            True,  # rolinherit
            False,  # rolreplication
        )

        with patch(
            "app.services.user_manager.PostgreSQLValidator.is_system_role",
            return_value=False,
        ):
            # Act
            result = self.user_manager.is_valid_iam_user(mock_cursor, username)

            # Assert
            assert result["valid"] is True
            assert result["username"] == "test@project.iam"
            assert result["user_type"] == "iam_user"

    def test_is_valid_iam_user_not_found(self):
        """Test is_valid_iam_user with a non-existent user."""
        # Arrange
        mock_cursor = Mock()
        username = "nonexistent@project.iam"

        # Mock cursor to return None (user not found)
        mock_cursor.fetchone.return_value = None

        # Act
        result = self.user_manager.is_valid_iam_user(mock_cursor, username)

        # Assert
        assert result["valid"] is False
        assert "does not exist" in result["reason"]

    def test_is_valid_iam_user_system_role(self):
        """Test is_valid_iam_user with a system role."""
        # Arrange
        mock_cursor = Mock()
        username = "postgres"

        # Mock cursor to return user info
        mock_cursor.fetchone.return_value = (
            "postgres",  # rolname
            True,  # rolcanlogin
            True,  # rolsuper
            True,  # rolcreatedb
            True,  # rolcreaterole
            True,  # rolinherit
            False,  # rolreplication
        )

        with patch(
            "app.services.user_manager.PostgreSQLValidator.is_system_role",
            return_value=True,
        ):
            # Act
            result = self.user_manager.is_valid_iam_user(mock_cursor, username)

            # Assert
            assert result["valid"] is False
            assert "system role" in result["reason"]
            assert result["user_type"] == "system"
