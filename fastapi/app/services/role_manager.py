"""
Role Manager for PostgreSQL role creation and management.

This module provides functionality to create, update, and manage PostgreSQL roles
with versioning, idempotence, and integration with the plugin system.
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager

from ..utils.logging_config import logger
from ..utils.role_validation import PostgreSQLValidator
from ..utils.role_validation import RoleValidator
from ..models import RoleInitializeResponse
from ..plugins.base import RoleDefinition
from ..plugins.registry import PluginRegistry
from .firebase import FirestoreRoleRegistryManager
from .database_validator import DatabaseValidator
from .connection_manager import ConnectionManager
from ..models import FirestoreRoleRegistry


class RoleManager:
    """
    Manager for PostgreSQL role creation and management.
    
    This class handles the creation, updating, and management of PostgreSQL roles
    with support for versioning, idempotence, and plugin-based role definitions.
    """
    
    def __init__(self):
        """Initialize RoleManager with dependencies."""
        self.connection_manager = ConnectionManager()
        self.firestore_manager = FirestoreRoleRegistryManager()
        self.plugin_registry = PluginRegistry()
    
    def _load_standard_roles(self, db_name: str, schema_name: str):
        """Load standard role definitions."""
        from ..plugins.standard_roles import StandardRolePlugin
        standard_plugin = StandardRolePlugin()
        self.plugin_registry.register_plugin(standard_plugin)
        logger.info(f"Standard roles plugin loaded for {db_name}.{schema_name}")
    
    
    def _execute_sql_commands(self, connection, sql_commands: List[str], role_name: str) -> bool:
        """
        Execute SQL commands for role creation/update.
        
        Args:
            connection: Database connection
            sql_commands: List of SQL commands to execute
            role_name: Name of the role being processed
            
        Returns:
            True if all commands executed successfully, False otherwise
        """
        try:
            cursor = connection.cursor()
            for command in sql_commands:
                logger.debug(f"Executing SQL for {role_name}: {command}")
                if not self.connection_manager.execute_sql_safely(cursor, command):
                    logger.error(f"Failed to execute SQL command for {role_name}: {command}")
                    return False
            connection.commit()
            cursor.close()
            logger.info(f"Successfully executed SQL commands for role {role_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to execute SQL commands for role {role_name}: {e}")
            connection.rollback()
            return False
    
    def _create_or_update_role(self, connection, role_def: RoleDefinition, 
                              force_update: bool = False) -> Tuple[bool, str]:
        """
        Create or update a role based on definition.
        
        Args:
            connection: Database connection
            role_def: Role definition
            force_update: Whether to force update even if role exists
            
        Returns:
            Tuple of (success, action_taken)
        """
        cursor = connection.cursor()
        try:
            role_exists = DatabaseValidator.role_exists(cursor, role_def.name)
        finally:
            cursor.close()
        
        if role_exists and not force_update:
            logger.info(f"Role {role_def.name} already exists, skipping")
            return True, "skipped"
        
        if role_exists and force_update:
            logger.info(f"Role {role_def.name} exists, updating due to force_update=True")
            action = "updated"
        else:
            logger.info(f"Creating new role {role_def.name}")
            action = "created"
        
        success = self._execute_sql_commands(connection, role_def.sql_commands, role_def.name)
        return success, action
    
    def initialize_roles(self, project_id: str, instance_name: str, database_name: str,
                        region: str, schema_name: str, force_update: bool = False) -> RoleInitializeResponse:
        """
        Initialize roles for a database.
        
        Args:
            project_id: GCP project ID
            instance_name: Cloud SQL instance name
            database_name: Database name
            region: GCP region
            force_update: Whether to force update existing roles
            schema_name: Schema name for app roles
            
        Returns:
            RoleInitializeResponse with operation results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting role initialization for {project_id}/{instance_name}/{database_name}")
            
            # Get existing registry
            registry = self.firestore_manager.get_role_registry(project_id, instance_name, database_name)
            if not registry:
                # Create new registry if none exists
                registry = FirestoreRoleRegistry()
                registry.created_by = "system"
            
            # Load standard roles with proper schema
            self._load_standard_roles(database_name, schema_name)
            
            # Get all role definitions from plugins
            all_role_definitions = []
            for plugin in self.plugin_registry.get_all_plugins().values():
                if hasattr(plugin, 'get_role_definitions'):
                    plugin_roles = plugin.get_role_definitions(database_name, schema_name)
                    all_role_definitions.extend(plugin_roles)
            
            # Filter role definitions based on schema_name
            all_role_definitions = [
                rd for rd in all_role_definitions 
                if f"_{schema_name}_" in rd.name or rd.name.endswith(f"_{schema_name}")
            ]
            
            if not all_role_definitions:
                logger.warning("No role definitions found")
                return RoleInitializeResponse(
                    success=False,
                    message="No role definitions found",
                    execution_time_seconds=time.time() - start_time
                )
            
            # Initialize response tracking
            roles_created = []
            roles_updated = []
            roles_skipped = []
            
            # Validate all role definitions before processing
            validation_result = RoleValidator.validate_multiple_roles(all_role_definitions)
            if not validation_result["valid"]:
                logger.warning(f"Role validation found issues: {validation_result['summary']['errors']}")
            
            # Process roles in database
            with self.connection_manager.get_connection(project_id, region, instance_name, database_name) as connection:
                for role_def in all_role_definitions:
                    try:
                        # Validate role definition with comprehensive checks
                        role_validation = RoleValidator.validate_role_definition(role_def)
                        if not role_validation["valid"]:
                            logger.warning(f"Role {role_def.name} failed validation: {role_validation['errors']}")
                            roles_skipped.append(role_def.name)
                            continue
                        
                        # Create or update role
                        success, action = self._create_or_update_role(connection, role_def, force_update)
                        
                        if success:
                            if action == "created":
                                roles_created.append(role_def.name)
                            elif action == "updated":
                                roles_updated.append(role_def.name)
                            else:
                                roles_skipped.append(role_def.name)
                        else:
                            logger.error(f"Failed to process role {role_def.name}")
                            roles_skipped.append(role_def.name)
                            
                    except Exception as e:
                        logger.error(f"Error processing role {role_def.name}: {e}")
                        roles_skipped.append(role_def.name)
                
            
            # Update Firebase registry
            registry.roles_initialized = True
            registry.last_updated = datetime.now()
            registry.force_update = force_update
            
            # Store role definitions in registry
            for role_def in all_role_definitions:
                role_data = {
                    "version": role_def.version,
                    "checksum": role_def.checksum,
                    "sql_commands": role_def.sql_commands,
                    "inherits": role_def.inherits,
                    "native_roles": role_def.native_roles,
                    "created_at": role_def.created_at,
                    "status": role_def.status
                }
                
                # Store all role definitions in plugin_roles for consistency
                # The new naming convention makes all roles plugin-based
                registry.plugin_roles[role_def.name] = role_data
            
            # Save registry to Firestore
            firestore_success = self.firestore_manager.save_role_registry(
                project_id, instance_name, database_name, registry
            )
            
            if not firestore_success:
                logger.warning("Failed to save registry to Firestore, but roles were created successfully")
            
            # Add creation history entry
            self.firestore_manager.add_creation_history_entry(
                project_id, instance_name, database_name,
                "role_initialization",
                roles_created + roles_updated,
                True,
                {
                    "roles_created": roles_created,
                    "roles_updated": roles_updated,
                    "roles_skipped": roles_skipped,
                    "force_update": force_update
                }
            )
            
            execution_time = time.time() - start_time
            total_roles = len(roles_created) + len(roles_updated) + len(roles_skipped)
            
            success = len(roles_created) > 0 or len(roles_updated) > 0
            
            message = f"Role initialization completed. Created: {len(roles_created)}, Updated: {len(roles_updated)}, Skipped: {len(roles_skipped)}"
            
            logger.info(f"Role initialization completed in {execution_time:.2f}s: {message}")
            
            return RoleInitializeResponse(
                success=success,
                message=message,
                roles_created=roles_created,
                roles_updated=roles_updated,
                roles_skipped=roles_skipped,
                total_roles=total_roles,
                firebase_document_id=f"{project_id}_{instance_name}_{database_name}",
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Role initialization failed: {e}")
            
            # Add failure to history
            self.firestore_manager.add_creation_history_entry(
                project_id, instance_name, database_name,
                "role_initialization",
                [],
                False,
                {"error": str(e)}
            )
            
            return RoleInitializeResponse(
                success=False,
                message=f"Role initialization failed: {str(e)}",
                execution_time_seconds=execution_time
            )
    
    def get_role_status(self, project_id: str, instance_name: str, database_name: str) -> Optional[Dict[str, Any]]:
        """
        Get role initialization status.
        
        Args:
            project_id: GCP project ID
            instance_name: Cloud SQL instance name
            database_name: Database name
            
        Returns:
            Dictionary with role status or None if not found
        """
        return self.firestore_manager.get_registry_status(project_id, instance_name, database_name)
    
    def load_plugin(self, plugin_module_path: str) -> bool:
        """
        Load a role plugin from module path.
        
        Args:
            plugin_module_path: Python module path for the plugin
            
        Returns:
            True if plugin loaded successfully, False otherwise
        """
        try:
            plugin = self.plugin_registry.load_plugin_from_module(plugin_module_path)
            return plugin is not None
        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_module_path}: {e}")
            return False

    def list_roles(self, project_id: str, region: str, instance_name: str, database_name: str) -> dict:
        """
        List all available roles in the database.
        
        Args:
            project_id: GCP project ID
            region: Instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            
        Returns:
            Dictionary with list of roles
        """
        import time
        start_time = time.time()
        
        try:
            with self.connection_manager.get_connection(project_id, region, instance_name, database_name) as conn:
                cursor = conn.cursor()
                
                try:
                    # Get all roles (excluding system roles using centralized list)
                    system_roles = list(PostgreSQLValidator.get_all_system_roles())
                    placeholders = ",".join(["%s"] * len(system_roles))
                    
                    cursor.execute(
                        f"""
                        SELECT rolname 
                        FROM pg_roles 
                        WHERE rolname NOT IN ({placeholders})
                        AND rolname NOT LIKE 'pg_%'
                        AND rolname NOT LIKE 'cloudsql%'
                        ORDER BY rolname
                        """,
                        system_roles
                    )
                    
                    roles = [row[0] for row in cursor.fetchall()]
                    
                    logger.info(f"Found {len(roles)} roles in database {database_name}")
                    
                    return {
                        "success": True,
                        "message": f"Retrieved {len(roles)} roles",
                        "roles": roles,
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
            logger.error(f"Failed to list roles: {e}")
            return {
                "success": False,
                "message": f"Failed to list roles: {str(e)}",
                "roles": [],
                "project_id": project_id,
                "instance_name": instance_name,
                "database_name": database_name,
                "execution_time_seconds": time.time() - start_time
            }
        