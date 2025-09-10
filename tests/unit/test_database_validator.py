"""
Unit tests for DatabaseValidator service.

Tests the centralized database validation utilities.
"""

import pytest
from unittest.mock import patch
from app.services.database_validator import DatabaseValidator


class TestDatabaseValidator:
    """Test cases for DatabaseValidator."""

    def test_role_exists_true(self, mock_cursor):
        """Test role_exists returns True when role exists."""
        # Arrange
        mock_cursor.fetchone.return_value = (1,)

        # Act
        result = DatabaseValidator.role_exists(mock_cursor, "test_role")

        # Assert
        assert result is True
        mock_cursor.execute.assert_called_once_with(
            "SELECT 1 FROM pg_roles WHERE rolname = %s", ("test_role",)
        )

    def test_role_exists_false(self, mock_cursor):
        """Test role_exists returns False when role doesn't exist."""
        # Arrange
        mock_cursor.fetchone.return_value = None

        # Act
        result = DatabaseValidator.role_exists(mock_cursor, "nonexistent_role")

        # Assert
        assert result is False

    def test_role_exists_exception(self, mock_cursor):
        """Test role_exists handles exceptions gracefully."""
        # Arrange
        mock_cursor.execute.side_effect = Exception("Database error")

        # Act
        result = DatabaseValidator.role_exists(mock_cursor, "test_role")

        # Assert
        assert result is False

    def test_schema_exists_true(self, mock_cursor):
        """Test schema_exists returns True when schema exists."""
        # Arrange
        mock_cursor.fetchone.return_value = (1,)

        # Act
        result = DatabaseValidator.schema_exists(mock_cursor, "test_schema")

        # Assert
        assert result is True
        mock_cursor.execute.assert_called_once_with(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
            ("test_schema",),
        )

    def test_schema_exists_false(self, mock_cursor):
        """Test schema_exists returns False when schema doesn't exist."""
        # Arrange
        mock_cursor.fetchone.return_value = None

        # Act
        result = DatabaseValidator.schema_exists(mock_cursor, "nonexistent_schema")

        # Assert
        assert result is False

    def test_database_exists_true(self, mock_cursor):
        """Test database_exists returns True when database exists."""
        # Arrange
        mock_cursor.fetchone.return_value = (1,)

        # Act
        result = DatabaseValidator.database_exists(mock_cursor, "test_database")

        # Assert
        assert result is True
        mock_cursor.execute.assert_called_once_with(
            "SELECT 1 FROM pg_database WHERE datname = %s", ("test_database",)
        )

    def test_database_exists_false(self, mock_cursor):
        """Test database_exists returns False when database doesn't exist."""
        # Arrange
        mock_cursor.fetchone.return_value = None

        # Act
        result = DatabaseValidator.database_exists(mock_cursor, "nonexistent_database")

        # Assert
        assert result is False

    @patch("app.services.database_validator.PostgreSQLValidator")
    def test_is_iam_user_true(self, mock_validator, mock_cursor):
        """Test is_iam_user returns True for valid IAM user."""
        # Arrange
        mock_validator.is_system_role.return_value = False
        mock_cursor.fetchone.return_value = ("test@project.iam", True, False)

        # Act
        result = DatabaseValidator.is_iam_user(mock_cursor, "test@project.iam")

        # Assert
        assert result is True

    @patch("app.services.database_validator.PostgreSQLValidator")
    def test_is_iam_user_false_system_role(self, mock_validator, mock_cursor):
        """Test is_iam_user returns False for system role."""
        # Arrange
        mock_validator.is_system_role.return_value = True
        mock_cursor.fetchone.return_value = ("postgres", True, True)

        # Act
        result = DatabaseValidator.is_iam_user(mock_cursor, "postgres")

        # Assert
        assert result is False

    @patch("app.services.database_validator.PostgreSQLValidator")
    def test_is_iam_user_false_cannot_login(self, mock_validator, mock_cursor):
        """Test is_iam_user returns False for user that cannot login."""
        # Arrange
        mock_validator.is_system_role.return_value = False
        mock_cursor.fetchone.return_value = ("test@project.iam", False, False)

        # Act
        result = DatabaseValidator.is_iam_user(mock_cursor, "test@project.iam")

        # Assert
        assert result is False

    @patch("app.services.database_validator.PostgreSQLValidator")
    def test_is_iam_user_false_cloudsql_user(self, mock_validator, mock_cursor):
        """Test is_iam_user returns False for cloudsql user."""
        # Arrange
        mock_validator.is_system_role.return_value = False
        mock_cursor.fetchone.return_value = ("cloudsqluser", True, False)

        # Act
        result = DatabaseValidator.is_iam_user(mock_cursor, "cloudsqluser")

        # Assert
        assert result is False

    def test_get_user_roles(self, mock_cursor):
        """Test get_user_roles returns list of roles."""
        # Arrange
        mock_cursor.fetchall.return_value = [("test_reader",), ("test_writer",)]

        # Act
        result = DatabaseValidator.get_user_roles(mock_cursor, "test@project.iam")

        # Assert
        assert result == ["test_reader", "test_writer"]
        mock_cursor.execute.assert_called_once()

    def test_get_user_roles_with_schema_prefix(self, mock_cursor):
        """Test get_user_roles with schema prefix filter."""
        # Arrange
        mock_cursor.fetchall.return_value = [
            ("test_schema_reader",),
            ("other_schema_writer",),
        ]

        # Act
        result = DatabaseValidator.get_user_roles(
            mock_cursor, "test@project.iam", "test_schema"
        )

        # Assert
        assert result == ["test_schema_reader", "other_schema_writer"]
        mock_cursor.execute.assert_called_once()

    def test_normalize_service_account_name(self):
        """Test normalize_service_account_name handles various formats."""
        # Test cases
        test_cases = [
            (
                "user@project.iam.gserviceaccount.com",
                "user@project.iam",
            ),
            ("user@project.iam", "user@project.iam"),
            ("user", "user"),
            ("", ""),
        ]

        for input_name, expected in test_cases:
            result = DatabaseValidator.normalize_service_account_name(input_name)
            assert result == expected

    def test_validate_schema_name_valid(self):
        """Test validate_schema_name with valid names."""
        valid_names = ["app_schema", "analytics", "user_data", "test123"]

        for name in valid_names:
            result = DatabaseValidator.validate_schema_name(name)
            assert result == name

    def test_validate_schema_name_invalid(self):
        """Test validate_schema_name with invalid names."""
        invalid_names = ["", "123schema", "schema-name", "schema name", "public"]

        for name in invalid_names:
            with pytest.raises(ValueError):
                DatabaseValidator.validate_schema_name(name)

    def test_validate_database_name_valid(self):
        """Test validate_database_name with valid names."""
        valid_names = ["app_database", "analytics_db", "user_data", "test123"]

        for name in valid_names:
            result = DatabaseValidator.validate_database_name(name)
            assert result == name

    def test_validate_database_name_invalid(self):
        """Test validate_database_name with invalid names."""
        invalid_names = ["", "123database", "database-name", "database name"]

        for name in invalid_names:
            with pytest.raises(ValueError):
                DatabaseValidator.validate_database_name(name)
