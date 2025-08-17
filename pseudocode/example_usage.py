#!/usr/bin/env python3
"""
Example Usage of Custom revoke_object_permissions Implementation

This file demonstrates how to integrate custom revocation logic
with the Cloud SQL Manager.
"""

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomCloudSQLUserManager:
    """
    Example of extending the Cloud SQL User Manager with custom logic
    """
    
    def __init__(self):
        # Initialize your custom manager
        pass
    
    def revoke_object_permissions_custom(self, cursor, username: str, schema_name: str) -> bool:
        """
        Custom implementation: Role-based permission revocation
        
        This example shows how to implement different revocation strategies
        based on user roles or other business logic.
        """
        try:
            # Get user role (this would come from your user management system)
            user_role = self.get_user_role(username)
            
            if user_role == 'admin':
                # Full revocation for admins
                return self.revoke_all_object_permissions(cursor, username, schema_name)
                
            elif user_role == 'developer':
                # Selective revocation for developers
                return self.revoke_developer_permissions(cursor, username, schema_name)
                
            elif user_role == 'viewer':
                # Minimal revocation for viewers
                return self.revoke_viewer_permissions(cursor, username, schema_name)
            
            else:
                # Default behavior
                logger.warning(f"Unknown role '{user_role}' for user {username}, using default revocation")
                return self.revoke_all_object_permissions(cursor, username, schema_name)
                
        except Exception as e:
            logger.error(f"Error in custom permission revocation: {e}")
            return False
    
    def get_user_role(self, username: str) -> str:
        """
        Get user role from your user management system
        
        This is where you would integrate with your existing user management
        system (LDAP, Active Directory, custom database, etc.)
        """
        # Example implementation - replace with your actual logic
        if 'admin' in username.lower():
            return 'admin'
        elif 'dev' in username.lower() or 'developer' in username.lower():
            return 'developer'
        elif 'view' in username.lower() or 'readonly' in username.lower():
            return 'viewer'
        else:
            return 'user'
    
    def revoke_all_object_permissions(self, cursor, username: str, schema_name: str) -> bool:
        """
        Revoke all object permissions (full revocation)
        """
        try:
            commands = [
                f'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{schema_name}" FROM "{username}"',
                f'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA "{schema_name}" FROM "{username}"',
                f'REVOKE ALL PRIVILEGES ON ALL ROUTINES IN SCHEMA "{schema_name}" FROM "{username}"',
            ]
            
            success = True
            for cmd in commands:
                try:
                    cursor.execute(cmd)
                    logger.info(f"Successfully executed: {cmd}")
                except Exception as e:
                    logger.warning(f"Failed to execute: {cmd} - {e}")
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Error in full permission revocation: {e}")
            return False
    
    def revoke_developer_permissions(self, cursor, username: str, schema_name: str) -> bool:
        """
        Revoke developer permissions (keep routine access)
        """
        try:
            # Developers keep routine permissions for debugging
            commands = [
                f'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{schema_name}" FROM "{username}"',
                f'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA "{schema_name}" FROM "{username}"',
                # Keep routine permissions: f'REVOKE ALL PRIVILEGES ON ALL ROUTINES IN SCHEMA "{schema_name}" FROM "{username}"',
            ]
            
            success = True
            for cmd in commands:
                try:
                    cursor.execute(cmd)
                    logger.info(f"Successfully executed: {cmd}")
                except Exception as e:
                    logger.warning(f"Failed to execute: {cmd} - {e}")
                    success = False
            
            logger.info(f"Developer permissions revoked for {username} (routine access preserved)")
            return success
            
        except Exception as e:
            logger.error(f"Error in developer permission revocation: {e}")
            return False
    
    def revoke_viewer_permissions(self, cursor, username: str, schema_name: str) -> bool:
        """
        Revoke viewer permissions (minimal revocation)
        """
        try:
            # Viewers only lose table access, keep sequence and routine access
            commands = [
                f'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{schema_name}" FROM "{username}"',
                # Keep sequence and routine permissions
            ]
            
            success = True
            for cmd in commands:
                try:
                    cursor.execute(cmd)
                    logger.info(f"Successfully executed: {cmd}")
                except Exception as e:
                    logger.warning(f"Failed to execute: {cmd} - {e}")
                    success = False
            
            logger.info(f"Viewer permissions revoked for {username} (sequence and routine access preserved)")
            return success
            
        except Exception as e:
            logger.error(f"Error in viewer permission revocation: {e}")
            return False


# Example usage
if __name__ == "__main__":
    # This is just an example - you would integrate this with your actual Cloud SQL Manager
    manager = CustomCloudSQLUserManager()
    
    # Example of how to use the custom implementation
    print("Custom Cloud SQL User Manager Example")
    print("=" * 40)
    
    # Simulate different user types
    test_users = [
        "admin@example.com",
        "developer@example.com", 
        "viewer@example.com",
        "unknown@example.com"
    ]
    
    for user in test_users:
        role = manager.get_user_role(user)
        print(f"User: {user} -> Role: {role}")
    
    print("\nTo integrate this with your Cloud SQL Manager:")
    print("1. Copy the custom methods to your manager class")
    print("2. Replace the default revoke_object_permissions method")
    print("3. Customize the logic based on your business requirements")
    print("4. Test thoroughly in your environment") 