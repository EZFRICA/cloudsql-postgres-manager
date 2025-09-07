"""
Reusable database operation components.

This module provides standardized database operation patterns
to reduce code duplication and improve error handling.
"""

import time
from typing import Any, Dict, List, Optional, Callable, Union
from contextlib import contextmanager
from dataclasses import dataclass
from app.services.connection_manager import ConnectionManager
from app.utils.logging_config import logger


@dataclass
class DatabaseOperationResult:
    """
    Standardized result for database operations.
    
    Attributes:
        success: Whether the operation was successful
        data: Result data from the operation
        message: Human-readable message
        execution_time: Time taken to execute the operation
        rows_affected: Number of rows affected (for write operations)
        error: Error message if operation failed
    """
    
    success: bool
    data: Optional[Any] = None
    message: str = ""
    execution_time: float = 0.0
    rows_affected: int = 0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "execution_time": self.execution_time,
            "rows_affected": self.rows_affected,
            "error": self.error
        }


class DatabaseOperation:
    """
    Reusable database operation component with standardized error handling.
    
    This class provides a consistent interface for database operations
    with automatic error handling, logging, and performance monitoring.
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    def execute_query(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        query: str,
        params: Optional[tuple] = None,
        fetch_results: bool = True
    ) -> DatabaseOperationResult:
        """
        Execute a SQL query with standardized error handling.
        
        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            query: SQL query to execute
            params: Optional query parameters
            fetch_results: Whether to fetch and return results
            
        Returns:
            DatabaseOperationResult with operation details
        """
        start_time = time.time()
        
        try:
            with self.connection_manager.get_connection(
                project_id, region, instance_name, database_name
            ) as conn:
                cursor = conn.cursor()
                
                try:
                    # Execute the query
                    cursor.execute(query, params or ())
                    
                    # Fetch results if requested
                    data = None
                    rows_affected = 0
                    
                    if fetch_results:
                        if query.strip().upper().startswith('SELECT'):
                            results = cursor.fetchall()
                            if results:
                                columns = [desc[0] for desc in cursor.description]
                                data = [dict(zip(columns, row)) for row in results]
                        else:
                            rows_affected = cursor.rowcount
                    
                    conn.commit()
                    
                    execution_time = time.time() - start_time
                    
                    return DatabaseOperationResult(
                        success=True,
                        data=data,
                        message="Query executed successfully",
                        execution_time=execution_time,
                        rows_affected=rows_affected
                    )
                    
                except Exception as e:
                    conn.rollback()
                    raise e
                    
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Database query failed: {str(e)}"
            logger.error(f"{error_msg} - Query: {query[:100]}...")
            
            return DatabaseOperationResult(
                success=False,
                message="Database operation failed",
                execution_time=execution_time,
                error=error_msg
            )
    
    def execute_script(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        script: str
    ) -> DatabaseOperationResult:
        """
        Execute a SQL script with multiple statements.
        
        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            script: SQL script to execute
            
        Returns:
            DatabaseOperationResult with operation details
        """
        start_time = time.time()
        
        try:
            with self.connection_manager.get_connection(
                project_id, region, instance_name, database_name
            ) as conn:
                cursor = conn.cursor()
                
                try:
                    # Split script into individual statements
                    statements = [stmt.strip() for stmt in script.split(';') if stmt.strip()]
                    
                    executed_statements = 0
                    for statement in statements:
                        if statement:
                            cursor.execute(statement)
                            executed_statements += 1
                    
                    conn.commit()
                    
                    execution_time = time.time() - start_time
                    
                    return DatabaseOperationResult(
                        success=True,
                        message=f"Script executed successfully ({executed_statements} statements)",
                        execution_time=execution_time,
                        rows_affected=executed_statements
                    )
                    
                except Exception as e:
                    conn.rollback()
                    raise e
                    
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Database script failed: {str(e)}"
            logger.error(f"{error_msg} - Script: {script[:100]}...")
            
            return DatabaseOperationResult(
                success=False,
                message="Database script execution failed",
                execution_time=execution_time,
                error=error_msg
            )
    
    def execute_transaction(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        operations: List[Callable[[Any], None]]
    ) -> DatabaseOperationResult:
        """
        Execute multiple operations within a single transaction.
        
        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            operations: List of functions that take a cursor and perform operations
            
        Returns:
            DatabaseOperationResult with operation details
        """
        start_time = time.time()
        
        try:
            with self.connection_manager.get_connection(
                project_id, region, instance_name, database_name
            ) as conn:
                cursor = conn.cursor()
                
                try:
                    # Execute all operations
                    for operation in operations:
                        operation(cursor)
                    
                    conn.commit()
                    
                    execution_time = time.time() - start_time
                    
                    return DatabaseOperationResult(
                        success=True,
                        message=f"Transaction completed successfully ({len(operations)} operations)",
                        execution_time=execution_time,
                        rows_affected=len(operations)
                    )
                    
                except Exception as e:
                    conn.rollback()
                    raise e
                    
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Database transaction failed: {str(e)}"
            logger.error(f"{error_msg}")
            
            return DatabaseOperationResult(
                success=False,
                message="Database transaction failed",
                execution_time=execution_time,
                error=error_msg
            )
    
    def check_connection(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str
    ) -> DatabaseOperationResult:
        """
        Check database connection health.
        
        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            
        Returns:
            DatabaseOperationResult with connection status
        """
        start_time = time.time()
        
        try:
            with self.connection_manager.get_connection(
                project_id, region, instance_name, database_name
            ) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                execution_time = time.time() - start_time
                
                return DatabaseOperationResult(
                    success=True,
                    data={"connection": "healthy", "test_query": result[0] if result else None},
                    message="Database connection is healthy",
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Database connection check failed: {str(e)}"
            logger.error(error_msg)
            
            return DatabaseOperationResult(
                success=False,
                message="Database connection is unhealthy",
                execution_time=execution_time,
                error=error_msg
            )