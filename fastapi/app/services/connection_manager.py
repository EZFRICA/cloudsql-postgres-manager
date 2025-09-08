import os
import threading
from contextlib import contextmanager
from typing import Tuple, Dict, Any
from queue import Queue, Empty
from google.cloud.sql.connector import Connector, IPTypes
from ..utils.logging_config import logger
from ..utils.secret_manager import access_regional_secret
from ..config import get_database_config


class ConnectionPool:
    """Thread-safe connection pool for Cloud SQL connections."""

    def __init__(self, max_size: int = 10, max_overflow: int = 20, timeout: int = 30):
        self.max_size = max_size
        self.max_overflow = max_overflow
        self.timeout = timeout
        self._pool = Queue(maxsize=max_size + max_overflow)
        self._created_connections = 0
        self._lock = threading.Lock()
        self._connector = Connector()

    def _create_connection(
        self, project_id: str, region: str, instance_name: str, database_name: str
    ) -> Any:
        """Create a new database connection."""
        instance_connection_name = f"{project_id}:{region}:{instance_name}"
        admin_password = access_regional_secret(project_id, instance_name, region)

        config = get_database_config()
        db_admin_user = config["db_admin_user"]

        conn = self._connector.connect(
            instance_connection_name,
            "pg8000",
            user=db_admin_user,
            password=admin_password,
            db=database_name,
            ip_type=IPTypes.PRIVATE,
        )
        conn.autocommit = False
        return conn

    def get_connection(
        self, project_id: str, region: str, instance_name: str, database_name: str
    ) -> Any:
        """Get a connection from the pool or create a new one."""
        try:
            # Try to get existing connection from pool
            conn = self._pool.get(timeout=self.timeout)
            # Test if connection is still alive
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                return conn
            except Exception:
                # Connection is dead, create a new one
                pass
        except Empty:
            # No connection available in pool
            pass

        # Create new connection if under limit
        with self._lock:
            if self._created_connections < self.max_size + self.max_overflow:
                self._created_connections += 1
                return self._create_connection(
                    project_id, region, instance_name, database_name
                )
            else:
                # Wait for a connection to become available
                conn = self._pool.get(timeout=self.timeout)
                return conn

    def return_connection(self, conn: Any):
        """Return a connection to the pool."""
        try:
            self._pool.put_nowait(conn)
        except:
            # Pool is full, close the connection
            try:
                conn.close()
            except:
                pass
            with self._lock:
                self._created_connections -= 1

    def close_all(self):
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except:
                pass
        self._connector.close()


class ConnectionManager:
    """Enhanced manager for Cloud SQL database connections with connection pooling"""

    def __init__(self):
        config = get_database_config()
        self.pools: Dict[str, ConnectionPool] = {}
        self._lock = threading.Lock()

    def _get_pool_key(self, project_id: str, region: str, instance_name: str) -> str:
        """Get pool key for connection caching."""
        return f"{project_id}:{region}:{instance_name}"

    def _get_or_create_pool(
        self, project_id: str, region: str, instance_name: str
    ) -> ConnectionPool:
        """Get or create connection pool for the instance."""
        pool_key = self._get_pool_key(project_id, region, instance_name)

        with self._lock:
            if pool_key not in self.pools:
                config = get_database_config()
                self.pools[pool_key] = ConnectionPool(
                    max_size=config["pool_size"],
                    max_overflow=config["pool_max_overflow"],
                    timeout=config["pool_timeout"],
                )
            return self.pools[pool_key]

    @contextmanager
    def get_connection(
        self, project_id: str, region: str, instance_name: str, database_name: str
    ):
        """
        Context manager for Cloud SQL connections with connection pooling

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name

        Yields:
            Database connection

        Raises:
            Exception: If connection fails
        """
        instance_connection_name = f"{project_id}:{region}:{instance_name}"
        conn = None
        pool = None

        try:
            logger.debug(
                f"Getting connection from pool for {instance_connection_name}/{database_name}"
            )

            # Get or create connection pool for this instance
            pool = self._get_or_create_pool(project_id, region, instance_name)

            # Get connection from pool
            conn = pool.get_connection(project_id, region, instance_name, database_name)
            logger.debug(
                f"Connection obtained from pool for {instance_connection_name}/{database_name}"
            )

            yield conn

        except Exception as e:
            logger.error(f"Connection failed to {instance_connection_name}: {str(e)}")
            if conn:
                try:
                    conn.rollback()
                except Exception as rollback_err:
                    logger.warning(f"Rollback failed: {rollback_err}")
            raise
        finally:
            if conn and pool:
                try:
                    # Return connection to pool instead of closing it
                    pool.return_connection(conn)
                    logger.debug(
                        f"Connection returned to pool for {instance_connection_name}/{database_name}"
                    )
                except Exception as return_err:
                    logger.warning(f"Failed to return connection to pool: {return_err}")
                    try:
                        conn.close()
                    except Exception as close_err:
                        logger.warning(f"Connection close failed: {close_err}")

    def execute_sql_safely(self, cursor, sql: str, params: Tuple = None) -> bool:
        """
        Execute SQL query with error handling

        Args:
            cursor: Database cursor
            sql: SQL query to execute
            params: Query parameters (optional)

        Returns:
            True if execution succeeds, False otherwise
        """
        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return True
        except Exception as e:
            logger.error(f"SQL execution failed: {sql[:100]}... Error: {str(e)}")
            return False

    def close(self):
        """Close all connection pools and connectors properly"""
        try:
            logger.info("Closing all connection pools...")
            for pool in self.pools.values():
                pool.close_all()
            self.pools.clear()
            logger.info("All connection pools closed successfully")
        except Exception as e:
            logger.warning(f"Error closing connection pools: {e}")

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get statistics about connection pools."""
        stats = {}
        for pool_key, pool in self.pools.items():
            stats[pool_key] = {
                "max_size": pool.max_size,
                "max_overflow": pool.max_overflow,
                "created_connections": pool._created_connections,
                "available_connections": pool._pool.qsize(),
                "timeout": pool.timeout,
            }
        return stats
