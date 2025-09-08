"""
Health Manager for database health monitoring and diagnostics.

This module provides functionality to check database health, connection status,
and performance metrics.
"""

import time
from ..utils.logging_config import logger
from .connection_manager import ConnectionManager


class HealthManager:
    """
    Manager for database health monitoring and diagnostics.

    This class handles health checks, connection monitoring, and performance metrics
    for PostgreSQL databases.
    """

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize HealthManager with connection manager.

        Args:
            connection_manager: ConnectionManager instance
        """
        self.connection_manager = connection_manager

    def check_database_health(
        self, project_id: str, region: str, instance_name: str, database_name: str
    ) -> dict:
        """
        Check database health and connection status.

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name

        Returns:
            Dictionary with database health information
        """

        start_time = time.time()

        try:
            connection_start = time.time()
            with self.connection_manager.get_connection(
                project_id, region, instance_name, database_name
            ) as conn:
                connection_time = (
                    time.time() - connection_start
                ) * 1000  # Convert to milliseconds
                cursor = conn.cursor()

                try:
                    # Get database information
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]

                    cursor.execute("SELECT pg_postmaster_start_time()")
                    start_time_db = cursor.fetchone()[0]

                    cursor.execute(
                        "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                    )
                    active_connections = cursor.fetchone()[0]

                    # Calculate uptime
                    uptime_seconds = time.time() - start_time_db.timestamp()
                    uptime_days = int(uptime_seconds // 86400)
                    uptime_hours = int((uptime_seconds % 86400) // 3600)
                    uptime_str = f"{uptime_days} days, {uptime_hours} hours"

                    database_info = {
                        "version": version,
                        "uptime": uptime_str,
                        "active_connections": active_connections,
                    }

                    logger.info(f"Database health check successful for {database_name}")

                    return {
                        "success": True,
                        "message": "Database is healthy",
                        "status": "healthy",
                        "connection_time_ms": connection_time,
                        "database_info": database_info,
                        "project_id": project_id,
                        "instance_name": instance_name,
                        "database_name": database_name,
                        "execution_time_seconds": time.time() - start_time,
                    }

                except Exception as e:
                    raise e
                finally:
                    cursor.close()

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "success": False,
                "message": f"Database health check failed: {str(e)}",
                "status": "unhealthy",
                "connection_time_ms": None,
                "database_info": None,
                "project_id": project_id,
                "instance_name": instance_name,
                "database_name": database_name,
                "execution_time_seconds": time.time() - start_time,
            }
