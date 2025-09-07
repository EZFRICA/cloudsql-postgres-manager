import time
from typing import Dict
from ..utils.logging_config import logger
from ..utils.role_validation import PostgreSQLValidator
from .connection_manager import ConnectionManager
from .database_validator import DatabaseValidator


class SchemaManager:
    """Manager for database schema operations"""

    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    def schema_exists(self, cursor, schema_name: str) -> bool:
        """
        Check if a schema exists in the database

        Args:
            cursor: Database cursor
            schema_name: Schema name to check

        Returns:
            True if schema exists, False otherwise
        """
        return DatabaseValidator.schema_exists(cursor, schema_name)


    def create_schema(self, project_id: str, region: str, instance_name: str, 
                     database_name: str, schema_name: str, owner: str = None) -> dict:
        """
        Create a schema in the database.
        
        This method is idempotent - if the schema already exists, it returns success
        without attempting to create it again. The existence check is performed before
        the CREATE SCHEMA statement, so IF NOT EXISTS is not needed in the SQL.
        
        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            schema_name: Schema name to create
            owner: Optional IAM user or service account to be the schema owner (defaults to postgres)
            
        Returns:
            Dictionary with operation result
        """
        start_time = time.time()
        
        try:
            # Validate schema name according to PostgreSQL standards
            try:
                validated_schema_name = PostgreSQLValidator.validate_schema_name(schema_name)
            except ValueError as e:
                logger.error(f"Invalid schema name '{schema_name}': {e}")
                return {
                    "success": False,
                    "message": f"Invalid schema name: {e}",
                    "schema_name": schema_name,
                    "project_id": project_id,
                    "instance_name": instance_name,
                    "database_name": database_name,
                    "execution_time_seconds": time.time() - start_time
                }
            
            # Validate database name
            try:
                validated_database_name = PostgreSQLValidator.validate_identifier(database_name, "database_name")
            except ValueError as e:
                logger.error(f"Invalid database name '{database_name}': {e}")
                return {
                    "success": False,
                    "message": f"Invalid database name: {e}",
                    "schema_name": schema_name,
                    "project_id": project_id,
                    "instance_name": instance_name,
                    "database_name": database_name,
                    "execution_time_seconds": time.time() - start_time
                }
            
            with self.connection_manager.get_connection(project_id, region, instance_name, database_name) as conn:
                cursor = conn.cursor()
                
                try:
                    # Check if schema already exists
                    if self.schema_exists(cursor, validated_schema_name):
                        logger.info(f"Schema '{validated_schema_name}' already exists")
                        return {
                            "success": True,
                            "message": f"Schema '{validated_schema_name}' already exists",
                            "schema_name": validated_schema_name,
                            "project_id": project_id,
                            "instance_name": instance_name,
                            "database_name": validated_database_name,
                            "execution_time_seconds": time.time() - start_time
                        }
                    
                    # Create schema with optional owner
                    if owner:
                        # Normalize the owner name to a PostgreSQL role name
                        normalized_owner = DatabaseValidator.normalize_service_account_name(owner)
                        
                        # Check if the owner role exists in the database (skip validation for system roles)
                        if not PostgreSQLValidator.is_system_role(normalized_owner) and not self.role_exists(cursor, normalized_owner):
                            logger.error(f"Owner role '{normalized_owner}' does not exist in the database")
                            return {
                                "success": False,
                                "message": f"Owner role '{normalized_owner}' does not exist in the database. Please ensure the IAM user or service account is properly configured.",
                                "schema_name": validated_schema_name,
                                "project_id": project_id,
                                "instance_name": instance_name,
                                "database_name": validated_database_name,
                                "execution_time_seconds": time.time() - start_time
                            }
                        
                        # Grant the role to postgres before using it in AUTHORIZATION
                        grant_sql = f'GRANT "{normalized_owner}" TO postgres'
                        logger.info(f"Granting role '{normalized_owner}' to postgres before schema creation")
                        
                        if not self.connection_manager.execute_sql_safely(cursor, grant_sql):
                            logger.warning(f"Failed to grant role '{normalized_owner}' to postgres, continuing with schema creation")
                        
                        create_sql = f'CREATE SCHEMA "{validated_schema_name}" AUTHORIZATION "{normalized_owner}"'
                        logger.info(f"Creating schema '{validated_schema_name}' with owner '{normalized_owner}'")
                    else:
                        # Use default owner (postgres )
                        create_sql = f'CREATE SCHEMA "{validated_schema_name}"'
                        logger.info(f"Creating schema '{validated_schema_name}' with default owner (postgres)")
                    
                    if not self.connection_manager.execute_sql_safely(cursor, create_sql):
                        return {
                            "success": False,
                            "message": f"Failed to create schema '{validated_schema_name}'",
                            "schema_name": validated_schema_name,
                            "project_id": project_id,
                            "instance_name": instance_name,
                            "database_name": validated_database_name,
                            "execution_time_seconds": time.time() - start_time
                        }
                    
                    # Commit the transaction
                    conn.commit()
                    
                    logger.info(f"Successfully created schema '{validated_schema_name}'")
                    return {
                        "success": True,
                        "message": f"Schema '{validated_schema_name}' created successfully",
                        "schema_name": validated_schema_name,
                        "project_id": project_id,
                        "instance_name": instance_name,
                        "database_name": validated_database_name,
                        "execution_time_seconds": time.time() - start_time
                    }
                    
                except Exception as e:
                    conn.rollback()
                    raise e
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to create schema '{schema_name}': {e}")
            return {
                "success": False,
                "message": f"Failed to create schema '{schema_name}': {str(e)}",
                "schema_name": schema_name,
                "project_id": project_id,
                "instance_name": instance_name,
                "database_name": database_name,
                "execution_time_seconds": time.time() - start_time
            }


    def role_exists(self, cursor, role_name: str) -> bool:
        """
        Check if a role exists in the database

        Args:
            cursor: Database cursor
            role_name: Role name to check

        Returns:
            True if role exists, False otherwise
        """
        return DatabaseValidator.role_exists(cursor, role_name)
    
    def change_schema_owner(self, cursor, schema_name: str, new_owner: str) -> bool:
        """
        Change the owner of an existing schema using ALTER SCHEMA.
        
        Args:
            cursor: Database cursor
            schema_name: Name of the schema
            new_owner: New owner role name
            
        Returns:
            True if ownership change succeeded, False otherwise
        """
        try:
            alter_sql = f'ALTER SCHEMA "{schema_name}" OWNER TO "{new_owner}"'
            logger.info(f"Changing schema '{schema_name}' ownership to '{new_owner}'")
            
            if self.connection_manager.execute_sql_safely(cursor, alter_sql):
                logger.info(f"Successfully changed schema '{schema_name}' ownership to '{new_owner}'")
                return True
            else:
                logger.warning(f"Failed to change schema ownership to '{new_owner}'")
                return False
                
        except Exception as e:
            logger.error(f"Error changing schema ownership to '{new_owner}': {e}")
            return False

    def list_schemas(self, project_id: str, region: str, instance_name: str, database_name: str) -> dict:
        """
        List all schemas in the database.
        
        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            
        Returns:
            Dictionary with list of schemas
        """
        import time
        start_time = time.time()
        
        try:
            with self.connection_manager.get_connection(project_id, region, instance_name, database_name) as conn:
                cursor = conn.cursor()
                
                try:
                    # Get all schemas
                    cursor.execute(
                        """
                        SELECT schema_name 
                        FROM information_schema.schemata 
                        WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                        ORDER BY schema_name
                        """
                    )
                    
                    schemas = [row[0] for row in cursor.fetchall()]
                    
                    logger.info(f"Found {len(schemas)} schemas in database {database_name}")
                    
                    return {
                        "success": True,
                        "message": f"Retrieved {len(schemas)} schemas",
                        "schemas": schemas,
                        "project_id": project_id,
                        "instance_name": instance_name,
                        "database_name": database_name,
                        "execution_time_seconds": time.time() - start_time
                    }
                    
                except Exception as e:
                    raise e
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to list schemas: {e}")
            return {
                "success": False,
                "message": f"Failed to list schemas: {str(e)}",
                "schemas": [],
                "project_id": project_id,
                "instance_name": instance_name,
                "database_name": database_name,
                "execution_time_seconds": time.time() - start_time
            }

    def list_tables(self, project_id: str, region: str, instance_name: str, database_name: str, schema_name: str) -> dict:
        """
        List all tables in a schema.
        
        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            schema_name: Schema name to list tables from
            
        Returns:
            Dictionary with list of tables
        """
        import time
        start_time = time.time()
        
        try:
            with self.connection_manager.get_connection(project_id, region, instance_name, database_name) as conn:
                cursor = conn.cursor()
                
                try:
                    # Get all tables in the schema
                    cursor.execute(
                        """
                        SELECT 
                            t.table_name,
                            t.table_type,
                            COALESCE(s.n_tup_ins + s.n_tup_upd + s.n_tup_del, 0) as row_count,
                            COALESCE(pg_total_relation_size(c.oid), 0) as size_bytes
                        FROM information_schema.tables t
                        LEFT JOIN pg_class c ON c.relname = t.table_name
                        LEFT JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
                        LEFT JOIN pg_stat_user_tables s ON s.relname = t.table_name AND s.schemaname = t.table_schema
                        WHERE t.table_schema = %s
                        AND t.table_type IN ('BASE TABLE', 'VIEW')
                        ORDER BY t.table_name
                        """,
                        (schema_name,)
                    )
                    
                    tables = []
                    for row in cursor.fetchall():
                        table_name, table_type, row_count, size_bytes = row
                        tables.append({
                            "table_name": table_name,
                            "table_type": table_type,
                            "row_count": row_count if row_count > 0 else None,
                            "size_bytes": size_bytes if size_bytes > 0 else None
                        })
                    
                    logger.info(f"Found {len(tables)} tables in schema {schema_name}")
                    
                    return {
                        "success": True,
                        "message": f"Retrieved {len(tables)} tables",
                        "tables": tables,
                        "schema_name": schema_name,
                        "project_id": project_id,
                        "instance_name": instance_name,
                        "database_name": database_name,
                        "execution_time_seconds": time.time() - start_time
                    }
                    
                except Exception as e:
                    raise e
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return {
                "success": False,
                "message": f"Failed to list tables: {str(e)}",
                "tables": [],
                "schema_name": schema_name,
                "project_id": project_id,
                "instance_name": instance_name,
                "database_name": database_name,
                "execution_time_seconds": time.time() - start_time
            }