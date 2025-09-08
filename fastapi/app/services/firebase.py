"""
Firestore integration for role registry management.

This module provides functionality to store and retrieve role initialization
state and definitions in Google Cloud Firestore.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from google.cloud import firestore

from ..utils.logging_config import logger
from ..models import FirestoreRoleRegistry
from ..config import get_firestore_config

# Retrieve default credentials and project
config = get_firestore_config()
firestore_client = firestore.Client(database=config["firestore_db_name"])


class FirestoreRoleRegistryManager:
    """
    Manager for Firestore role registry operations.

    This class handles storing and retrieving role initialization state
    and definitions in Google Cloud Firestore.
    """

    def __init__(self):
        """Initialize Firestore client."""
        try:
            self.db = firestore.Client()
            logger.info("Firestore client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            raise RuntimeError(f"Firestore initialization failed: {e}")

    def _get_document_id(
        self, project_id: str, instance_name: str, database_name: str
    ) -> str:
        """
        Generate Firestore document ID for role registry.

        Args:
            project_id: GCP project ID
            instance_name: Cloud SQL instance name
            database_name: Database name

        Returns:
            Document ID in format: {project_id}-{instance}-{database}
        """
        return f"{project_id}-{instance_name}-{database_name}"

    def get_role_registry(
        self, project_id: str, instance_name: str, database_name: str
    ) -> Optional[FirestoreRoleRegistry]:
        """
        Get role registry from Firestore.

        Args:
            project_id: GCP project ID
            instance_name: Cloud SQL instance name
            database_name: Database name

        Returns:
            FirestoreRoleRegistry object if found, None otherwise
        """

        try:
            doc_id = self._get_document_id(project_id, instance_name, database_name)
            doc_ref = self.db.collection("role_registry").document(doc_id)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                # Convert timestamps back to datetime objects
                if "created_at" in data:
                    data["created_at"] = data["created_at"].replace(tzinfo=None)
                if "last_updated" in data:
                    data["last_updated"] = data["last_updated"].replace(tzinfo=None)

                return FirestoreRoleRegistry(**data)
            else:
                logger.info(f"No role registry found for {doc_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to get role registry from Firestore: {e}")
            return None

    def save_role_registry(
        self,
        project_id: str,
        instance_name: str,
        database_name: str,
        registry: FirestoreRoleRegistry,
    ) -> bool:
        """
        Save role registry to Firestore.

        Args:
            project_id: GCP project ID
            instance_name: Cloud SQL instance name
            database_name: Database name
            registry: FirestoreRoleRegistry object to save

        Returns:
            True if successful, False otherwise
        """

        try:
            doc_id = self._get_document_id(project_id, instance_name, database_name)
            doc_ref = self.db.collection("role_registry").document(doc_id)

            # Convert to dict - Firestore handles datetime objects directly
            registry_dict = registry.dict()

            doc_ref.set(registry_dict)
            logger.info(f"Role registry saved to Firestore: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save role registry to Firestore: {e}")
            return False

    def update_role_registry(
        self,
        project_id: str,
        instance_name: str,
        database_name: str,
        updates: Dict[str, Any],
    ) -> bool:
        """
        Update specific fields in the role registry.

        Args:
            project_id: GCP project ID
            instance_name: Cloud SQL instance name
            database_name: Database name
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """

        try:
            doc_id = self._get_document_id(project_id, instance_name, database_name)
            doc_ref = self.db.collection("role_registry").document(doc_id)

            # Firestore handles datetime objects directly
            processed_updates = updates

            doc_ref.update(processed_updates)
            logger.info(f"Role registry updated in Firestore: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update role registry in Firestore: {e}")
            return False

    def add_creation_history_entry(
        self,
        project_id: str,
        instance_name: str,
        database_name: str,
        action: str,
        roles_affected: list,
        success: bool,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add an entry to the creation history.

        Args:
            project_id: GCP project ID
            instance_name: Cloud SQL instance name
            database_name: Database name
            action: Action performed (e.g., "initial_creation", "version_update")
            roles_affected: List of roles affected by this action
            success: Whether the action was successful
            additional_data: Additional data to store

        Returns:
            True if successful, False otherwise
        """

        try:
            doc_id = self._get_document_id(project_id, instance_name, database_name)
            doc_ref = self.db.collection("role_registry").document(doc_id)

            history_entry = {
                "timestamp": datetime.now(),
                "action": action,
                "roles_affected": roles_affected,
                "success": success,
            }

            if additional_data:
                history_entry.update(additional_data)

            # Add to creation_history array
            doc_ref.update(
                {
                    "creation_history": firestore.ArrayUnion([history_entry]),
                    "last_updated": datetime.now(),
                }
            )

            logger.info(f"Added creation history entry to Firestore: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add creation history entry to Firestore: {e}")
            return False

    def check_roles_initialized(
        self, project_id: str, instance_name: str, database_name: str
    ) -> bool:
        """
        Check if roles have been initialized for a database.

        Args:
            project_id: GCP project ID
            instance_name: Cloud SQL instance name
            database_name: Database name

        Returns:
            True if roles are initialized, False otherwise
        """
        registry = self.get_role_registry(project_id, instance_name, database_name)
        return registry.roles_initialized if registry else False

    def get_registry_status(
        self, project_id: str, instance_name: str, database_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get registry status information.

        Args:
            project_id: GCP project ID
            instance_name: Cloud SQL instance name
            database_name: Database name

        Returns:
            Dictionary with registry status or None if not found
        """
        registry = self.get_role_registry(project_id, instance_name, database_name)
        if not registry:
            return None

        return {
            "roles_initialized": registry.roles_initialized,
            "created_at": registry.created_at.isoformat(),
            "last_updated": registry.last_updated.isoformat(),
            "total_standard_roles": len(registry.roles_definitions),
            "total_plugin_roles": len(registry.plugin_roles),
            "total_history_entries": len(registry.creation_history),
        }
