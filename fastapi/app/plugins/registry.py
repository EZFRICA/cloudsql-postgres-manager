"""
Plugin registry for managing role definition plugins.

This module provides functionality to discover, load, and manage
role definition plugins dynamically.
"""

import importlib
import inspect
from typing import List, Dict, Optional
from .base import RolePlugin, RoleDefinition
from ..utils.logging_config import logger


class PluginRegistry:
    """
    Registry for managing role definition plugins.
    
    This class handles the discovery, loading, and management of
    role definition plugins in the system.
    """
    
    def __init__(self):
        self._plugins: Dict[str, RolePlugin] = {}
        self._plugin_modules: Dict[str, str] = {}
    
    def register_plugin(self, plugin: RolePlugin) -> None:
        """
        Register a plugin instance.
        
        Args:
            plugin: Plugin instance to register
        """
        if not isinstance(plugin, RolePlugin):
            raise ValueError("Plugin must be an instance of RolePlugin")
        
        plugin_name = plugin.plugin_name
        if plugin_name in self._plugins:
            logger.warning(f"Plugin {plugin_name} is already registered, overwriting")
        
        self._plugins[plugin_name] = plugin
        logger.info(f"Registered plugin: {plugin_name} v{plugin.plugin_version}")
    
    def load_plugin_from_module(self, module_path: str) -> Optional[RolePlugin]:
        """
        Load a plugin from a module path.
        
        Args:
            module_path: Python module path (e.g., "plugins.custom_roles")
            
        Returns:
            Plugin instance if found, None otherwise
        """
        try:
            module = importlib.import_module(module_path)
            
            # Find RolePlugin subclasses in the module
            plugin_classes = []
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, RolePlugin) and 
                    obj != RolePlugin):
                    plugin_classes.append(obj)
            
            if not plugin_classes:
                logger.warning(f"No RolePlugin subclasses found in {module_path}")
                return None
            
            if len(plugin_classes) > 1:
                logger.warning(f"Multiple RolePlugin subclasses found in {module_path}, using first one")
            
            plugin_class = plugin_classes[0]
            plugin_instance = plugin_class()
            
            self.register_plugin(plugin_instance)
            self._plugin_modules[plugin_instance.plugin_name] = module_path
            
            return plugin_instance
            
        except Exception as e:
            logger.error(f"Failed to load plugin from {module_path}: {e}")
            return None
    
    def get_plugin(self, plugin_name: str) -> Optional[RolePlugin]:
        """
        Get a registered plugin by name.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin instance if found, None otherwise
        """
        return self._plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, RolePlugin]:
        """
        Get all registered plugins.
        
        Returns:
            Dictionary mapping plugin names to plugin instances
        """
        return self._plugins.copy()
    
    def get_all_role_definitions(self) -> List[RoleDefinition]:
        """
        Get all role definitions from all registered plugins.
        
        Returns:
            List of all role definitions from all plugins
        """
        all_definitions = []
        
        for plugin in self._plugins.values():
            try:
                definitions = plugin.get_role_definitions()
                all_definitions.extend(definitions)
                logger.debug(f"Loaded {len(definitions)} role definitions from {plugin.plugin_name}")
            except Exception as e:
                logger.error(f"Failed to get role definitions from {plugin.plugin_name}: {e}")
        
        return all_definitions
    
    def get_role_definition(self, role_name: str) -> Optional[RoleDefinition]:
        """
        Get a specific role definition by name.
        
        Args:
            role_name: Name of the role
            
        Returns:
            Role definition if found, None otherwise
        """
        for plugin in self._plugins.values():
            try:
                definitions = plugin.get_role_definitions()
                for definition in definitions:
                    if definition.name == role_name:
                        return definition
            except Exception as e:
                logger.error(f"Failed to get role definitions from {plugin.plugin_name}: {e}")
        
        return None
    
    def validate_all_definitions(self) -> Dict[str, List[str]]:
        """
        Validate all role definitions from all plugins.
        
        Returns:
            Dictionary mapping plugin names to lists of validation errors
        """
        validation_results = {}
        
        for plugin_name, plugin in self._plugins.items():
            errors = []
            try:
                definitions = plugin.get_role_definitions()
                for definition in definitions:
                    if not plugin.validate_role_definition(definition):
                        errors.append(f"Role {definition.name} has dangerous permissions")
            except Exception as e:
                errors.append(f"Failed to validate plugin: {e}")
            
            if errors:
                validation_results[plugin_name] = errors
        
        return validation_results
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """
        Unregister a plugin.
        
        Args:
            plugin_name: Name of the plugin to unregister
            
        Returns:
            True if plugin was unregistered, False if not found
        """
        if plugin_name in self._plugins:
            del self._plugins[plugin_name]
            if plugin_name in self._plugin_modules:
                del self._plugin_modules[plugin_name]
            logger.info(f"Unregistered plugin: {plugin_name}")
            return True
        return False
    
    def get_registry_status(self) -> Dict[str, any]:
        """
        Get registry status information.
        
        Returns:
            Dictionary containing registry status
        """
        return {
            "total_plugins": len(self._plugins),
            "plugins": {
                name: {
                    "version": plugin.plugin_version,
                    "role_count": len(plugin.get_role_definitions())
                }
                for name, plugin in self._plugins.items()
            },
            "total_role_definitions": len(self.get_all_role_definitions())
        }