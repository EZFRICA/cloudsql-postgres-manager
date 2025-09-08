"""
Plugin system for role definitions.

This module provides the base classes and interfaces for creating
customizable role definitions in the CloudSQL PostgreSQL Manager.
"""

from .base import RolePlugin, RoleDefinition
from .registry import PluginRegistry

__all__ = ["RolePlugin", "RoleDefinition", "PluginRegistry"]
