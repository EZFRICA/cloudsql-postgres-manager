# revoke_object_permissions - Pseudocode Implementation Guide

## Overview

This document provides pseudocode examples for implementing custom `revoke_object_permissions` logic. The current implementation in `cloudsql.py` is a basic example that can be extended or replaced based on your specific requirements.

## Current Implementation (Basic)

```python
def revoke_object_permissions(self, cursor, username: str, schema_name: str) -> bool:
    """
    Basic implementation: Attempts to revoke all object permissions
    """
    try:
        success = True
        
        # Revoke table permissions
        revoke_commands = [
            f'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{schema_name}" FROM "{username}"',
            f'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA "{schema_name}" FROM "{username}"',
            f'REVOKE ALL PRIVILEGES ON ALL ROUTINES IN SCHEMA "{schema_name}" FROM "{username}"',
        ]
        
        for cmd in revoke_commands:
            if not self.execute_sql_safely(cursor, cmd):
                success = False
        
        # Revoke default privileges
        default_privilege_commands = [
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" REVOKE ALL PRIVILEGES ON TABLES FROM "{username}"',
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" REVOKE ALL PRIVILEGES ON SEQUENCES FROM "{username}"',
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" REVOKE ALL PRIVILEGES ON ROUTINES FROM "{username}"',
        ]
        
        for cmd in default_privilege_commands:
            if not self.execute_sql_safely(cursor, cmd):
                success = False
        
        return success
        
    except Exception as e:
        logger.error(f"Error revoking object permissions: {e}")
        return False
```

## Custom Implementation Examples

### Example 1: Selective Permission Revocation

```python
def revoke_object_permissions_selective(self, cursor, username: str, schema_name: str, permissions_to_revoke: List[str]) -> bool:
    """
    Custom implementation: Revoke only specific permission types
    """
    try:
        success = True
        
        # Define permission mappings
        permission_mappings = {
            'tables': f'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{schema_name}" FROM "{username}"',
            'sequences': f'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA "{schema_name}" FROM "{username}"',
            'routines': f'REVOKE ALL PRIVILEGES ON ALL ROUTINES IN SCHEMA "{schema_name}" FROM "{username}"',
            'default_tables': f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" REVOKE ALL PRIVILEGES ON TABLES FROM "{username}"',
            'default_sequences': f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" REVOKE ALL PRIVILEGES ON SEQUENCES FROM "{username}"',
            'default_routines': f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" REVOKE ALL PRIVILEGES ON ROUTINES FROM "{username}"'
        }
        
        # Execute only requested revocations
        for permission_type in permissions_to_revoke:
            if permission_type in permission_mappings:
                cmd = permission_mappings[permission_type]
                if not self.execute_sql_safely(cursor, cmd):
                    success = False
                    logger.warning(f"Failed to revoke {permission_type} permissions")
        
        return success
        
    except Exception as e:
        logger.error(f"Error in selective permission revocation: {e}")
        return False
```

### Example 2: Role-Based Permission Revocation

```python
def revoke_object_permissions_role_based(self, cursor, username: str, schema_name: str, user_role: str) -> bool:
    """
    Custom implementation: Different revocation strategies based on user role
    """
    try:
        success = True
        commands = []
        if user_role == 'admin':
            # Full revocation for admins
            return self.revoke_object_permissions(cursor, username, schema_name)
            
        elif user_role == 'developer':
            # Keep some permissions for developers
            commands = [
                f'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{schema_name}" FROM "{username}"',
                f'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA "{schema_name}" FROM "{username}"',
                # Keep routine permissions for developers
            ]
            
        elif user_role == 'viewer':
            # Minimal revocation for viewers
            commands = [
                f'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{schema_name}" FROM "{username}"',
                # Keep sequence and routine permissions
            ]
        
        # Execute role-specific commands
        if commands:
            for cmd in commands:
                if not self.execute_sql_safely(cursor, cmd):
                    success = False
        
        return success
        
    except Exception as e:
        logger.error(f"Error in role-based permission revocation: {e}")
        return False
```

### Example 3: Audit Trail with Permission Revocation

```python
def revoke_object_permissions_with_audit(self, cursor, username: str, schema_name: str, admin_user: str) -> bool:
    """
    Custom implementation: Log all revocation actions for audit purposes
    """
    try:
        success = True
        
        # Create audit log entry
        audit_sql = """
            INSERT INTO permission_audit_log (
                username, schema_name, action, admin_user, timestamp
            ) VALUES (%s, %s, %s, %s, NOW())
        """
        cursor.execute(audit_sql, (username, schema_name, 'REVOKE_OBJECT_PERMISSIONS', admin_user))
        
        # Perform standard revocation
        if not self.revoke_object_permissions(cursor, username, schema_name):
            success = False
        
        # Update audit log with result
        result_sql = """
            UPDATE permission_audit_log 
            SET success = %s, completed_at = NOW()
            WHERE username = %s AND action = 'REVOKE_OBJECT_PERMISSIONS'
            ORDER BY timestamp DESC LIMIT 1
        """
        cursor.execute(result_sql, (success, username))
        
        return success
        
    except Exception as e:
        logger.error(f"Error in audited permission revocation: {e}")
        return False
```

### Example 4: Conditional Permission Revocation

```python
def revoke_object_permissions_conditional(self, cursor, username: str, schema_name: str, conditions: Dict) -> bool:
    """
    Custom implementation: Revoke permissions based on specific conditions
    """
    try:
        success = True
        
        # Check if user has active sessions
        if conditions.get('check_active_sessions', False):
            active_sessions = self.check_user_active_sessions(cursor, username)
            if active_sessions > 0:
                logger.warning(f"User {username} has {active_sessions} active sessions")
                if not conditions.get('force_revoke', False):
                    return False
        
        # Check if user owns objects
        if conditions.get('check_object_ownership', False):
            owned_objects = self.get_user_owned_objects(cursor, username, schema_name)
            if owned_objects:
                logger.info(f"User {username} owns {len(owned_objects)} objects")
                # Handle ownership transfer if needed
        
        # Check business hours
        if conditions.get('business_hours_only', False):
            if not self.is_business_hours():
                logger.warning("Revocation attempted outside business hours")
                return False
        
        # Perform standard revocation
        return self.revoke_object_permissions(cursor, username, schema_name)
        
    except Exception as e:
        logger.error(f"Error in conditional permission revocation: {e}")
        return False
```

## Integration with Main Function

To use a custom implementation, modify the `revoke_all_permissions` function:

```python
def revoke_all_permissions(
    self, cursor, username: str, database_name: str, schema_name: str, revoke_object_permissions: bool = False
) -> bool:
    try:
        # ... existing code ...
        
        if revoke_object_permissions:
            # Use custom implementation instead of basic one
            if not self.revoke_object_permissions_custom(cursor, username, schema_name):
                success = False
        
        # ... rest of the function ...
        
    except Exception as e:
        logger.error(f"Error revoking permissions: {e}")
        return False
```

## Best Practices

1. **Error Handling**: Always wrap custom logic in try-catch blocks
2. **Logging**: Log all actions for debugging and audit purposes
3. **Transaction Safety**: Ensure your custom logic works within database transactions
4. **Performance**: Consider the performance impact of custom logic
5. **Testing**: Test custom implementations thoroughly before production use

## Customization Points

- **Permission Types**: Which specific permissions to revoke
- **User Roles**: Different strategies for different user types
- **Business Rules**: Time-based, condition-based revocations
- **Audit Requirements**: Logging and tracking of actions
- **Integration**: Hooks for external systems or notifications

## Notes

- The current implementation in `cloudsql.py` serves as a reference
- Custom implementations can completely replace the basic one
- Consider Cloud SQL limitations when implementing custom logic
- Test thoroughly in your specific environment 