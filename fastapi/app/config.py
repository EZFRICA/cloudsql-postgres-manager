"""
Configuration management for Cloud SQL IAM User Permission Manager.

This module provides centralized configuration management using environment variables
with sensible defaults and validation.
"""

import logging
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application settings
    app_name: str = Field(
        default="Cloud SQL IAM User Permission Manager", env="APP_NAME"
    )
    app_version: str = Field(default="0.1.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")

    # Logging settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT"
    )

    # Database settings
    db_admin_user: str = Field(default="postgres", env="DB_ADMIN_USER")
    secret_name_suffix: str = Field(
        default="postgres-password", env="SECRET_NAME_SUFFIX"
    )
    connection_timeout: int = Field(default=30, env="CONNECTION_TIMEOUT")
    max_retries: int = Field(default=3, env="MAX_RETRIES")

    # Performance settings - Connection Pool
    connection_pool_size: int = Field(default=10, env="CONNECTION_POOL_SIZE")
    connection_pool_max_overflow: int = Field(
        default=20, env="CONNECTION_POOL_MAX_OVERFLOW"
    )
    connection_pool_timeout: int = Field(default=30, env="CONNECTION_POOL_TIMEOUT")

    # Security settings
    max_users_per_request: int = Field(default=100, env="MAX_USERS_PER_REQUEST")

    # Firebase/Firestore settings
    firestore_db_name: str = Field(default="(default)", env="FIRESTORE_DB_NAME")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper

    @field_validator("db_admin_user")
    @classmethod
    def validate_db_admin_user(cls, v: str) -> str:
        """Validate database admin user name."""
        if not v or not v.strip():
            raise ValueError("db_admin_user cannot be empty")
        return v.strip()

    @field_validator("connection_pool_size")
    @classmethod
    def validate_connection_pool_size(cls, v: int) -> int:
        """Validate connection pool size."""
        if v < 1:
            raise ValueError("connection_pool_size must be at least 1")
        if v > 100:
            raise ValueError("connection_pool_size cannot exceed 100")
        return v

    @field_validator("connection_pool_max_overflow")
    @classmethod
    def validate_connection_pool_max_overflow(cls, v: int) -> int:
        """Validate connection pool max overflow."""
        if v < 0:
            raise ValueError("connection_pool_max_overflow must be at least 0")
        if v > 200:
            raise ValueError("connection_pool_max_overflow cannot exceed 200")
        return v

    @field_validator("connection_timeout", "connection_pool_timeout")
    @classmethod
    def validate_timeout_values(cls, v: int) -> int:
        """Validate timeout values."""
        if v < 1:
            raise ValueError("timeout values must be at least 1 second")
        if v > 300:
            raise ValueError("timeout values cannot exceed 300 seconds")
        return v

    @field_validator("max_retries")
    @classmethod
    def validate_max_retries(cls, v: int) -> int:
        """Validate max retries."""
        if v < 0:
            raise ValueError("max_retries must be at least 0")
        if v > 10:
            raise ValueError("max_retries cannot exceed 10")
        return v

    @field_validator("max_users_per_request")
    @classmethod
    def validate_max_users_per_request(cls, v: int) -> int:
        """Validate max users per request."""
        if v < 1:
            raise ValueError("max_users_per_request must be at least 1")
        if v > 1000:
            raise ValueError("max_users_per_request cannot exceed 1000")
        return v

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow parsing of environment variables as JSON for lists
        env_parse_none_str = "null"


# Global settings instance
settings = Settings()


def get_log_level() -> int:
    """Get logging level as integer."""
    return getattr(logging, settings.log_level)


def is_development() -> bool:
    """Check if running in development mode."""
    return settings.debug


def is_production() -> bool:
    """Check if running in production mode."""
    return not settings.debug


def get_app_config() -> dict:
    """Get application configuration."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
    }


def get_logging_config() -> dict:
    """Get logging configuration."""
    return {
        "level": settings.log_level,
        "level_int": get_log_level(),
        "format": settings.log_format,
    }


def get_database_config() -> dict:
    """Get database configuration."""
    return {
        "db_admin_user": settings.db_admin_user,
        "secret_name_suffix": settings.secret_name_suffix,
        "connection_timeout": settings.connection_timeout,
        "max_retries": settings.max_retries,
        "pool_size": settings.connection_pool_size,
        "pool_max_overflow": settings.connection_pool_max_overflow,
        "pool_timeout": settings.connection_pool_timeout,
    }


def get_security_config() -> dict:
    """Get security configuration."""
    return {
        "allowed_regions": settings.allowed_regions,
        "max_users_per_request": settings.max_users_per_request,
    }


def get_firestore_config() -> dict:
    """Get Firestore configuration."""
    return {
        "firestore_db_name": settings.firestore_db_name,
    }


def get_complete_config() -> dict:
    """Get all configuration sections."""
    return {
        "app": get_app_config(),
        "logging": get_logging_config(),
        "database": get_database_config(),
        "security": get_security_config(),
        "firestore": get_firestore_config(),
    }


def validate_configuration() -> bool:
    """Validate the current configuration."""
    try:
        # This will trigger all validators
        Settings()
        return True
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False


# Validate configuration on import
if not validate_configuration():
    raise RuntimeError("Invalid configuration detected")
