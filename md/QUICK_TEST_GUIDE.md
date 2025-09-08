# Quick Testing Guide - Standard Roles

## 🚀 Express Tests (5 minutes)

### 1. Quick Connection

```bash
# Connect to your database
gcloud sql connect YOUR_INSTANCE --user=YOUR_USER@DOMAIN.COM --database=DB_NAME
```

### 2. Express Role Testing

```sql
-- Quick role verification
SELECT 
    rolname,
    CASE WHEN rolname LIKE '%_reader' THEN '✅ Reader'
         WHEN rolname LIKE '%_writer' THEN '✅ Writer' 
         WHEN rolname LIKE '%_admin' THEN '✅ Admin'
         WHEN rolname LIKE '%_monitor' THEN '✅ Monitor'
         WHEN rolname LIKE '%_analyst' THEN '✅ Analyst'
         ELSE '❓ Other'
    END as role_type
FROM pg_roles 
WHERE rolname LIKE 'DB_NAME_%' 
ORDER BY rolname;
```

### 3. Permission Testing

```sql
-- Test permissions on schema
SELECT 
    has_schema_privilege('DB_NAME_SCHEMA_NAME_reader', 'schema_name', 'USAGE') as reader_usage,
    has_schema_privilege('DB_NAME_SCHEMA_NAME_admin', 'schema_name', 'CREATE') as admin_create;
```

### 4. Quick Functional Test

```sql
-- Create a test object (as admin)
CREATE TABLE schema_name.quick_test (
    id SERIAL PRIMARY KEY,
    name TEXT
);

-- Read test (should succeed)
SELECT * FROM schema_name.quick_test;

-- Write test (should succeed if writer/admin)
INSERT INTO schema_name.quick_test (name) VALUES ('test_quick');

-- Cleanup
DROP TABLE schema_name.quick_test;
```

## ⚡ Automated Script

For complete automated testing, use the `role_test_scripts.sql` file:

```bash
# Execute the complete test script
psql "host=YOUR_IP dbname=DB_NAME user=YOUR_USER@DOMAIN.COM sslmode=require" -f role_test_scripts.sql
```

## 🎯 Expected Results

### ✅ Success
- All standard roles are created
- Permissions are correctly assigned
- Functional tests pass

### ❌ Failure
- Missing roles → Check role creation
- Missing permissions → Check permission assignment
- Functional tests fail → Check role inheritance

## 🔧 Express Troubleshooting

### Problem: Roles not created
```sql
-- Check existing roles
SELECT rolname FROM pg_roles WHERE rolname LIKE 'DB_NAME_%';
```

### Problem: Missing permissions
```sql
-- Check permissions on schema
SELECT 
    schemaname,
    has_schema_privilege('DB_NAME_SCHEMA_NAME_reader', schemaname, 'USAGE') as usage
FROM information_schema.schemata 
WHERE schemaname = 'schema_name';
```

### Problem: User without role
```sql
-- Check roles assigned to a user
SELECT 
    u.rolname as user_name,
    r.rolname as assigned_role
FROM pg_roles u
JOIN pg_auth_members m ON u.oid = m.member
JOIN pg_roles r ON m.roleid = r.oid
WHERE u.rolname = 'YOUR_USER@DOMAIN.COM';
```

## 📊 Validation Checklist

- [ ] Role `{db}_{schema}_reader` created
- [ ] Role `{db}_{schema}_writer` created  
- [ ] Role `{db}_{schema}_admin` created
- [ ] Role `{db}_monitor` created
- [ ] Role `{db}_{schema}_analyst` created
- [ ] USAGE permissions granted to reader
- [ ] CREATE permissions granted to admin
- [ ] Writer → reader inheritance functional
- [ ] Admin → writer inheritance functional
- [ ] PostgreSQL native roles assigned to monitor
- [ ] Read tests successful
- [ ] Write tests successful (writer/admin)
- [ ] Create tests successful (admin only)

## 🎉 Complete Validation

If all checklist items are checked, your standard roles system works perfectly!

---

*For more detailed tests, see [ROLE_TESTING.md](./ROLE_TESTING.md)*