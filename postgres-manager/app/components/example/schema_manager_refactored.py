"""
Refactored schema manager using reusable components.

This module demonstrates how to use the reusable components
to reduce code duplication and improve maintainability in services.
"""

from app.components import ServiceManager, DatabaseOperation, LoggingHelper
from .connection_manager import ConnectionManager


class SchemaManagerRefactored(ServiceManager):
    """
    Refactored manager for database schema operations using reusable components.

    This class demonstrates how to use:
    - ServiceManager for standardized operation execution
    - DatabaseOperation for database operations
    - LoggingHelper for consistent logging
    """

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__("SchemaManager")
        self.connection_manager = connection_manager
        self.db_operation = DatabaseOperation(connection_manager)

    def schema_exists(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        schema_name: str,
    ) -> bool:
        """
        Check if a schema exists in the database using DatabaseOperation.

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            schema_name: Schema name to check

        Returns:
            True if schema exists, False otherwise
        """
        result = self.db_operation.execute_query(
            project_id,
            region,
            instance_name,
            database_name,
            """
            SELECT EXISTS(
                SELECT 1 FROM information_schema.schemata 
                WHERE schema_name = %s
            )
            """,
            (schema_name,),
        )

        if not result.success:
            LoggingHelper.log_operation_error(
                "schema_exists_check",
                f"Failed to check schema existence: {result.error}",
            )
            return False

        exists = result.data[0]["exists"] if result.data else False
        LoggingHelper.log_operation_success(
            "schema_exists_check",
            execution_time=result.execution_time,
            details={"schema_name": schema_name, "exists": exists},
        )

        return exists

    def create_schema(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        schema_name: str,
    ) -> dict:
        """
        Create a schema in the database using ServiceManager.

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            schema_name: Schema name to create

        Returns:
            Dictionary with operation result
        """
        # Execute with ServiceManager for automatic logging and error handling
        result = self._execute_operation(
            "create_schema",
            self._create_schema_impl,
            project_id,
            region,
            instance_name,
            database_name,
            schema_name,
        )

        return result.to_dict()

    def _create_schema_impl(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        schema_name: str,
    ) -> dict:
        """
        Implementation of schema creation using DatabaseOperation.

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            schema_name: Schema name to create

        Returns:
            Dictionary with schema creation result
        """
        # Check if schema already exists
        if self.schema_exists(
            project_id, region, instance_name, database_name, schema_name
        ):
            return {
                "message": f"Schema '{schema_name}' already exists",
                "schema_name": schema_name,
                "already_exists": True,
            }

        # Create the schema using DatabaseOperation
        result = self.db_operation.execute_query(
            project_id,
            region,
            instance_name,
            database_name,
            f"CREATE SCHEMA IF NOT EXISTS {schema_name}",
            fetch_results=False,
        )

        if not result.success:
            raise Exception(f"Failed to create schema: {result.error}")

        return {
            "message": f"Schema '{schema_name}' created successfully",
            "schema_name": schema_name,
            "already_exists": False,
        }

    def list_schemas(
        self, project_id: str, region: str, instance_name: str, database_name: str
    ) -> dict:
        """
        List all non-system schemas in the database.

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name

        Returns:
            Dictionary with list of schemas
        """
        result = self._execute_operation(
            "list_schemas",
            self._list_schemas_impl,
            project_id,
            region,
            instance_name,
            database_name,
        )

        return result.to_dict()

    def _list_schemas_impl(
        self, project_id: str, region: str, instance_name: str, database_name: str
    ) -> dict:
        """
        Implementation of schema listing using DatabaseOperation.

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name

        Returns:
            Dictionary with list of schemas
        """
        result = self.db_operation.execute_query(
            project_id,
            region,
            instance_name,
            database_name,
            """
            SELECT schema_name, schema_owner
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY schema_name
            """,
        )

        if not result.success:
            raise Exception(f"Failed to list schemas: {result.error}")

        schemas = result.data if result.data else []

        return {
            "schemas": schemas,
            "count": len(schemas),
            "message": f"Found {len(schemas)} user schemas",
        }

    def drop_schema(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        schema_name: str,
        cascade: bool = False,
    ) -> dict:
        """
        Drop a schema from the database.

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            schema_name: Schema name to drop
            cascade: Whether to cascade drop (drop all objects in schema)

        Returns:
            Dictionary with operation result
        """
        result = self._execute_operation(
            "drop_schema",
            self._drop_schema_impl,
            project_id,
            region,
            instance_name,
            database_name,
            schema_name,
            cascade,
        )

        return result.to_dict()

    def _drop_schema_impl(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        schema_name: str,
        cascade: bool,
    ) -> dict:
        """
        Implementation of schema dropping using DatabaseOperation.

        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            schema_name: Schema name to drop
            cascade: Whether to cascade drop

        Returns:
            Dictionary with drop result
        """
        # Check if schema exists first
        if not self.schema_exists(
            project_id, region, instance_name, database_name, schema_name
        ):
            return {
                "message": f"Schema '{schema_name}' does not exist",
                "schema_name": schema_name,
                "dropped": False,
            }

        # Build DROP SCHEMA query
        cascade_clause = " CASCADE" if cascade else ""
        query = f"DROP SCHEMA {schema_name}{cascade_clause}"

        result = self.db_operation.execute_query(
            project_id, region, instance_name, database_name, query, fetch_results=False
        )

        if not result.success:
            raise Exception(f"Failed to drop schema: {result.error}")

        return {
            "message": f"Schema '{schema_name}' dropped successfully",
            "schema_name": schema_name,
            "dropped": True,
            "cascade": cascade,
        }
