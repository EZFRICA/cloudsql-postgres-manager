# Configuration Examples for revoke_object_permissions

## Overview

This document provides practical configuration examples for using the `revoke_object_permissions` feature in different scenarios.

## Basic Configuration

### 1. Default Behavior (No revoke_object_permissions specified)

```json
{
  "project_id": "my-project",
  "instance_name": "postgres-instance",
  "database_name": "app_db",
  "region": "europe-west1",
  "schema_name": "app_schema",
  "iam_users": [
    {
      "name": "app-service@my-project.iam.gserviceaccount.com",
      "permission_level": "readwrite"
    }
  ]
}
```

**Result**: Only basic permissions (database, schema) are revoked. Object permissions remain intact.

### 2. Full Object Permission Revocation

```json
{
  "project_id": "my-project",
  "instance_name": "postgres-instance",
  "database_name": "app_db",
  "region": "europe-west1",
  "schema_name": "app_schema",
  "iam_users": [
    {
      "name": "temp-service@my-project.iam.gserviceaccount.com",
      "permission_level": "readwrite",
      "revoke_object_permissions": true
    }
  ]
}
```

**Result**: All permissions are revoked, including tables, sequences, and routines.

## Production Scenarios

### 3. Multi-Environment Setup

```json
{
  "project_id": "my-project",
  "instance_name": "postgres-production",
  "database_name": "app_db",
  "region": "europe-west1",
  "schema_name": "app_schema",
  "iam_users": [
    {
      "name": "app-service@my-project.iam.gserviceaccount.com",
      "permission_level": "readwrite"
      // revoke_object_permissions: false (default) - Keep object access for production
    },
    {
      "name": "monitoring-service@my-project.iam.gserviceaccount.com",
      "permission_level": "readonly"
      // revoke_object_permissions: false (default) - Keep object access for monitoring
    },
    {
      "name": "admin-service@my-project.iam.gserviceaccount.com",
      "permission_level": "admin"
      // revoke_object_permissions: false (default) - Keep full access for admins
    }
  ]
}
```

### 4. Development Environment

```json
{
  "project_id": "my-project",
  "instance_name": "postgres-development",
  "database_name": "app_db",
  "region": "europe-west1",
  "schema_name": "app_schema",
  "iam_users": [
    {
      "name": "dev-service@my-project.iam.gserviceaccount.com",
      "permission_level": "readwrite",
      "revoke_object_permissions": true
      // Full revocation for development cleanup
    },
    {
      "name": "test-service@my-project.iam.gserviceaccount.com",
      "permission_level": "readonly",
      "revoke_object_permissions": true
      // Full revocation for test cleanup
    }
  ]
}
```

### 5. Staging Environment

```json
{
  "project_id": "my-project",
  "instance_name": "postgres-staging",
  "database_name": "app_db",
  "region": "europe-west1",
  "schema_name": "app_schema",
  "iam_users": [
    {
      "name": "staging-service@my-project.iam.gserviceaccount.com",
      "permission_level": "readwrite",
      "revoke_object_permissions": true
      // Full revocation for staging cleanup
    },
    {
      "name": "qa-service@my-project.iam.gserviceaccount.com",
      "permission_level": "readonly",
      "revoke_object_permissions": true
      // Full revocation for QA cleanup
    }
  ]
}
```

## Business Logic Scenarios

### 6. Role-Based Configuration

```json
{
  "project_id": "my-project",
  "instance_name": "postgres-instance",
  "database_name": "app_db",
  "region": "europe-west1",
  "schema_name": "app_schema",
  "iam_users": [
    {
      "name": "admin@my-project.iam.gserviceaccount.com",
      "permission_level": "admin"
      // revoke_object_permissions: false - Admins keep full access
    },
    {
      "name": "developer@my-project.iam.gserviceaccount.com",
      "permission_level": "readwrite",
      "revoke_object_permissions": true
      // Developers get full revocation (clean slate)
    },
    {
      "name": "viewer@my-project.iam.gserviceaccount.com",
      "permission_level": "readonly"
      // Viewers keep object access (minimal impact)
    }
  ]
}
```

### 7. Time-Based Configuration

```json
{
  "project_id": "my-project",
  "instance_name": "postgres-instance",
  "database_name": "app_db",
  "region": "europe-west1",
  "schema_name": "app_schema",
  "iam_users": [
    {
      "name": "nightly-job@my-project.iam.gserviceaccount.com",
      "permission_level": "readwrite",
      "revoke_object_permissions": true
      // Full revocation for temporary nightly jobs
    },
    {
      "name": "batch-processor@my-project.iam.gserviceaccount.com",
      "permission_level": "readwrite",
      "revoke_object_permissions": true
      // Full revocation for batch processing
    },
    {
      "name": "continuous-service@my-project.iam.gserviceaccount.com",
      "permission_level": "readwrite"
      // Keep object access for continuous services
    }
  ]
}
```

### 8. Compliance and Audit Requirements

```json
{
  "project_id": "my-project",
  "instance_name": "postgres-instance",
  "database_name": "app_db",
  "region": "europe-west1",
  "schema_name": "app_schema",
  "iam_users": [
    {
      "name": "audit-service@my-project.iam.gserviceaccount.com",
      "permission_level": "readonly"
      // revoke_object_permissions: false - Keep access for audit trails
    },
    {
      "name": "compliance-checker@my-project.iam.gserviceaccount.com",
      "permission_level": "readonly"
      // revoke_object_permissions: false - Keep access for compliance checks
    },
    {
      "name": "temporary-access@my-project.iam.gserviceaccount.com",
      "permission_level": "readwrite",
      "revoke_object_permissions": true
      // Full revocation for temporary access
    }
  ]
}
```

## Configuration Best Practices

### 1. Environment-Specific Defaults

- **Production**: `revoke_object_permissions: false` (preserve access)
- **Staging**: `revoke_object_permissions: true` (clean slate)
- **Development**: `revoke_object_permissions: true` (clean slate)

### 2. User Type Considerations

- **Service Accounts**: Consider lifecycle and purpose
- **Human Users**: Consider role and responsibilities
- **Temporary Access**: Always use `revoke_object_permissions: true`

### 3. Compliance Requirements

- **Audit Trails**: Keep access for audit services
- **Compliance Checks**: Preserve access for compliance tools
- **Monitoring**: Maintain access for monitoring services

### 4. Performance Impact

- **Frequent Changes**: Use selective revocation
- **Batch Operations**: Use full revocation for cleanup
- **Continuous Services**: Preserve object access

## Testing Your Configuration

### 1. Validate JSON Schema

```bash
# Test your configuration
curl -X POST http://localhost:8080/manage-users \
  -H "Content-Type: application/json" \
  -d @your-config.json
```

### 2. Check Logs

Look for these log messages:
- `"Revoking object permissions for user {username} (revoke_object_permissions=True)"`
- `"Skipping object permissions revocation for user {username} (revoke_object_permissions=False)"`

### 3. Verify Database State

```sql
-- Check user permissions
SELECT grantee, privilege_type, table_name 
FROM information_schema.table_privileges 
WHERE table_schema = 'your_schema';

-- Check default privileges
SELECT grantee, privilege_type 
FROM information_schema.role_table_grants 
WHERE table_schema = 'your_schema';
```

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**: Cloud SQL limitations on object ownership
2. **Partial Revocation**: Some permissions may fail due to ownership constraints
3. **Transaction Rollbacks**: Ensure proper error handling in your application

### Debug Steps

1. Check application logs for detailed error messages
2. Verify user permissions in the database
3. Test with minimal configuration first
4. Gradually add complexity while testing 