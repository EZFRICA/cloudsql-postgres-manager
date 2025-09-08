# Standard Roles Testing Guide

## 📋 Overview

This guide provides comprehensive instructions for testing and verifying the proper functioning of standard roles defined in the `standard_roles.py` plugin. The tests cover all role types: reader, writer, admin, monitor, and analyst.

## 🎯 Testing Objectives

- ✅ Verify correct role creation
- ✅ Validate permissions granted to each role
- ✅ Test inheritance between roles
- ✅ Confirm permissions on existing and future objects
- ✅ Validate PostgreSQL native roles

## 🏗️ Standard Roles Architecture

### Role Hierarchy

```
{db}_{schema}_admin
    ↓ inherits from
{db}_{schema}_writer
    ↓ inherits from
{db}_{schema}_reader

{db}_{schema}_analyst
    ↓ inherits from
{db}_{schema}_reader

{db}_monitor (database-level role)
```

### Role Types

1. **Reader** : Read-only access
2. **Writer** : Write access (inherits from reader)
3. **Admin** : Full administrative access (inherits from writer)
4. **Monitor** : Monitoring access with PostgreSQL native roles
5. **Analyst** : Analytics access (inherits from reader + stats)

## 🚀 Prerequisites

### 1. Database Connection

```bash
# Connect with an IAM user
gcloud sql connect YOUR_INSTANCE --user=USER@DOMAIN.COM --database=DB_NAME

# Or direct connection
psql "host=YOUR_IP dbname=DB_NAME user=USER@DOMAIN.COM sslmode=require"
```

### 2. Test Schema

Ensure you have a test schema available:

```sql
-- Create a test schema if necessary
CREATE SCHEMA IF NOT EXISTS test_schema;
```

## 📝 Tests by Role Type

### 1. Reader Role Tests

#### 1.1 Creation Verification

```sql
-- Verify role existence
SELECT rolname, rolsuper, rolinherit, rolcreaterole, rolcreatedb, rolcanlogin
FROM pg_roles 
WHERE rolname = 'DB_NAME_test_schema_reader';

-- Verify schema permissions
SELECT 
    has_schema_privilege('DB_NAME_test_schema_reader', 'test_schema', 'USAGE') as usage_perm;
```

#### 1.2 Read Permission Tests

```sql
-- Create test objects (as admin)
CREATE TABLE test_schema.reader_test_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO test_schema.reader_test_table (name, data) VALUES 
    ('test1', '{"type": "reader_test"}'),
    ('test2', '{"type": "permission_test"}');

-- Read tests (should succeed)
SELECT * FROM test_schema.reader_test_table;
SELECT COUNT(*) FROM test_schema.reader_test_table;
SELECT name, data FROM test_schema.reader_test_table WHERE id = 1;

-- Write tests (should fail)
-- These commands should generate permission errors
INSERT INTO test_schema.reader_test_table (name) VALUES ('should_fail');
UPDATE test_schema.reader_test_table SET name = 'updated' WHERE id = 1;
DELETE FROM test_schema.reader_test_table WHERE id = 1;
```

#### 1.3 Future Permissions Tests

```sql
-- Create new objects (as admin)
CREATE TABLE test_schema.future_reader_test (
    id SERIAL PRIMARY KEY,
    content TEXT
);

-- Verify that reader can read new objects
SELECT * FROM test_schema.future_reader_test;
```

### 2. Writer Role Tests

#### 2.1 Inheritance Verification

```sql
-- Verify that writer inherits from reader
SELECT 
    r.rolname as role_name,
    i.rolname as inherited_role
FROM pg_roles r
JOIN pg_auth_members m ON r.oid = m.roleid
JOIN pg_roles i ON m.member = i.oid
WHERE r.rolname = 'DB_NAME_test_schema_writer';
```

#### 2.2 Write Permission Tests

```sql
-- Insert tests (should succeed)
INSERT INTO test_schema.reader_test_table (name, data) VALUES 
    ('writer_test', '{"type": "writer_insert"}');

-- Update tests (should succeed)
UPDATE test_schema.reader_test_table 
SET data = '{"type": "writer_update"}' 
WHERE name = 'writer_test';

-- Delete tests (should succeed)
DELETE FROM test_schema.reader_test_table 
WHERE name = 'writer_test';

-- Read tests (inherited from reader - should succeed)
SELECT * FROM test_schema.reader_test_table;
```

#### 2.3 Sequence Tests

```sql
-- Create table with sequence (as admin)
CREATE TABLE test_schema.writer_sequence_test (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100)
);

-- Sequence usage tests (should succeed)
INSERT INTO test_schema.writer_sequence_test (name) VALUES 
    ('sequence_test_1'),
    ('sequence_test_2');

-- Verify generated values
SELECT * FROM test_schema.writer_sequence_test;
```

### 3. Admin Role Tests

#### 3.1 Complete Inheritance Verification

```sql
-- Verify writer inheritance
SELECT 
    r.rolname as role_name,
    i.rolname as inherited_role
FROM pg_roles r
JOIN pg_auth_members m ON r.oid = m.roleid
JOIN pg_roles i ON m.member = i.oid
WHERE r.rolname = 'DB_NAME_test_schema_admin';
```

#### 3.2 Administrative Permission Tests

```sql
-- Test 1: Table creation
CREATE TABLE test_schema.admin_test_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Test 2: Index creation
CREATE INDEX idx_admin_name ON test_schema.admin_test_table(name);
CREATE INDEX idx_admin_data ON test_schema.admin_test_table USING GIN(data);

-- Test 3: Structure modification
ALTER TABLE test_schema.admin_test_table 
ADD COLUMN description TEXT DEFAULT 'Admin created';

-- Test 4: View creation
CREATE VIEW test_schema.admin_test_view AS 
SELECT name, created_at FROM test_schema.admin_test_table;

-- Test 5: Function creation
CREATE OR REPLACE FUNCTION test_schema.admin_test_function()
RETURNS TEXT AS $$
BEGIN
    RETURN 'Admin function created successfully';
END;
$$ LANGUAGE plpgsql;

-- Test 6: Custom type creation
CREATE TYPE test_schema.admin_status AS ENUM ('active', 'inactive', 'pending');

-- Test 7: Custom sequence creation
CREATE SEQUENCE test_schema.admin_test_seq START 1000;

-- Test 8: Constraint management
ALTER TABLE test_schema.admin_test_table 
ADD CONSTRAINT chk_name_not_empty CHECK (name IS NOT NULL AND name != '');
```

#### 3.3 Complete CRUD Operations Tests

```sql
-- Data insertion
INSERT INTO test_schema.admin_test_table (name, data) VALUES 
    ('admin_test1', '{"type": "admin_test", "level": "full"}'),
    ('admin_test2', '{"type": "permission_test", "status": "complete"}');

-- Data reading
SELECT * FROM test_schema.admin_test_table;

-- Data update
UPDATE test_schema.admin_test_table 
SET description = 'Updated by admin' 
WHERE name = 'admin_test1';

-- Data deletion
DELETE FROM test_schema.admin_test_table 
WHERE name = 'admin_test2';
```

### 4. Monitor Role Tests

#### 4.1 Native Roles Verification

```sql
-- Verify native role assignment
SELECT 
    r.rolname as role_name,
    i.rolname as native_role
FROM pg_roles r
JOIN pg_auth_members m ON r.oid = m.roleid
JOIN pg_roles i ON m.member = i.oid
WHERE r.rolname = 'DB_NAME_monitor';
```

#### 4.2 Monitoring Permission Tests

```sql
-- Test 1: System statistics access
SELECT 
    datname,
    numbackends,
    xact_commit,
    xact_rollback
FROM pg_stat_database 
WHERE datname = current_database();

-- Test 2: Table statistics access
SELECT 
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del
FROM pg_stat_user_tables 
WHERE schemaname = 'test_schema';

-- Test 3: System parameters access
SELECT name, setting, unit, context 
FROM pg_settings 
WHERE name LIKE '%log%' 
LIMIT 10;

-- Test 4: Monitoring views access
SELECT 
    pid,
    usename,
    application_name,
    state,
    query_start
FROM pg_stat_activity 
WHERE state = 'active';
```

### 5. Analyst Role Tests

#### 5.1 Inheritance Verification

```sql
-- Verify reader and native role inheritance
SELECT 
    r.rolname as role_name,
    i.rolname as inherited_role
FROM pg_roles r
JOIN pg_auth_members m ON r.oid = m.roleid
JOIN pg_roles i ON m.member = i.oid
WHERE r.rolname = 'DB_NAME_test_schema_analyst';
```

#### 5.2 Analytics Permission Tests

```sql
-- Test 1: Data reading (inherited from reader)
SELECT * FROM test_schema.admin_test_table;

-- Test 2: Statistics access (native role)
SELECT 
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_live_tup,
    n_dead_tup
FROM pg_stat_user_tables 
WHERE schemaname = 'test_schema';

-- Test 3: Complex analytical queries
SELECT 
    name,
    COUNT(*) as count,
    AVG(LENGTH(data::text)) as avg_data_length
FROM test_schema.admin_test_table 
GROUP BY name;

-- Test 4: Metadata access
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'test_schema';
```

## 🧹 Test Cleanup

### Complete Cleanup Script

```sql
-- Remove all created test objects
DROP FUNCTION IF EXISTS test_schema.admin_test_function();
DROP VIEW IF EXISTS test_schema.admin_test_view;
DROP TABLE IF EXISTS test_schema.admin_test_table CASCADE;
DROP TABLE IF EXISTS test_schema.reader_test_table CASCADE;
DROP TABLE IF EXISTS test_schema.writer_sequence_test CASCADE;
DROP TABLE IF EXISTS test_schema.future_reader_test CASCADE;
DROP SEQUENCE IF EXISTS test_schema.admin_test_seq;
DROP TYPE IF EXISTS test_schema.admin_status;

-- Verify cleanup
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'test_schema';
```

## 📊 Automatic Verification Script

### Complete Test Script

```sql
-- Automatic role verification script
DO $$
DECLARE
    test_result TEXT := '';
    error_count INTEGER := 0;
BEGIN
    -- Test 1: Verify role existence
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'DB_NAME_test_schema_reader') THEN
        test_result := test_result || '❌ Reader role missing\n';
        error_count := error_count + 1;
    ELSE
        test_result := test_result || '✅ Reader role created\n';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'DB_NAME_test_schema_writer') THEN
        test_result := test_result || '❌ Writer role missing\n';
        error_count := error_count + 1;
    ELSE
        test_result := test_result || '✅ Writer role created\n';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'DB_NAME_test_schema_admin') THEN
        test_result := test_result || '❌ Admin role missing\n';
        error_count := error_count + 1;
    ELSE
        test_result := test_result || '✅ Admin role created\n';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'DB_NAME_monitor') THEN
        test_result := test_result || '❌ Monitor role missing\n';
        error_count := error_count + 1;
    ELSE
        test_result := test_result || '✅ Monitor role created\n';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'DB_NAME_test_schema_analyst') THEN
        test_result := test_result || '❌ Analyst role missing\n';
        error_count := error_count + 1;
    ELSE
        test_result := test_result || '✅ Analyst role created\n';
    END IF;
    
    -- Test 2: Verify schema permissions
    IF NOT has_schema_privilege('DB_NAME_test_schema_reader', 'test_schema', 'USAGE') THEN
        test_result := test_result || '❌ USAGE permission missing for reader\n';
        error_count := error_count + 1;
    ELSE
        test_result := test_result || '✅ USAGE permission granted to reader\n';
    END IF;
    
    IF NOT has_schema_privilege('DB_NAME_test_schema_admin', 'test_schema', 'CREATE') THEN
        test_result := test_result || '❌ CREATE permission missing for admin\n';
        error_count := error_count + 1;
    ELSE
        test_result := test_result || '✅ CREATE permission granted to admin\n';
    END IF;
    
    -- Display results
    RAISE NOTICE '%', test_result;
    
    IF error_count = 0 THEN
        RAISE NOTICE '🎉 All tests passed successfully!';
    ELSE
        RAISE NOTICE '⚠️ % error(s) detected', error_count;
    END IF;
END $$;
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Roles Not Created
```sql
-- Check if roles exist
SELECT rolname FROM pg_roles WHERE rolname LIKE '%test_schema%';
```

#### 2. Missing Permissions
```sql
-- Check schema permissions
SELECT 
    schemaname,
    has_schema_privilege('DB_NAME_test_schema_reader', schemaname, 'USAGE') as usage,
    has_schema_privilege('DB_NAME_test_schema_admin', schemaname, 'CREATE') as create_perm
FROM information_schema.schemata 
WHERE schemaname = 'test_schema';
```

#### 3. Non-Functional Inheritance
```sql
-- Check role inheritance
SELECT 
    r.rolname as role_name,
    i.rolname as inherited_role
FROM pg_roles r
JOIN pg_auth_members m ON r.oid = m.roleid
JOIN pg_roles i ON m.member = i.oid
WHERE r.rolname LIKE '%test_schema%'
ORDER BY r.rolname, i.rolname;
```

## 📈 Success Metrics

### Validation Criteria

- ✅ **100% roles created** : All standard roles are present
- ✅ **Correct permissions** : Each role has appropriate permissions
- ✅ **Functional inheritance** : Roles correctly inherit permissions
- ✅ **Native roles** : Monitor and analyst roles have access to PostgreSQL native roles
- ✅ **Future permissions** : Permissions apply to new objects
- ✅ **Functional tests** : All CRUD tests pass according to permission level

### Test Report

After running the tests, you should get:

```
✅ Reader role created
✅ Writer role created  
✅ Admin role created
✅ Monitor role created
✅ Analyst role created
✅ USAGE permission granted to reader
✅ CREATE permission granted to admin
🎉 All tests passed successfully!
```

## 📚 Additional Resources

- [API.md](./API.md) - Role management endpoints documentation
- [PLUGINS.md](./PLUGINS.md) - Plugin system documentation
- [SERVICES.md](./SERVICES.md) - Role management services documentation
- [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md) - Architecture overview

---

*This testing guide is designed to validate the proper functioning of the `standard_roles.py` plugin and ensure that all standard roles work correctly in your Cloud SQL PostgreSQL environment.*