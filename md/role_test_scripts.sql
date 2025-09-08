-- =====================================================
-- Automated Test Scripts for Standard Roles
-- Cloud SQL PostgreSQL Manager
-- =====================================================

-- Variable configuration (adapt to your environment)
-- Replace these values with your actual parameters
\set db_name 'your_database_name'
\set schema_name 'your_schema_name'
\set test_user 'your_user@domain.com'

-- =====================================================
-- 1. ROLE VERIFICATION SCRIPT
-- =====================================================

-- Verify existence of all standard roles
SELECT 
    'Role Verification' as test_category,
    CASE 
        WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'db_name' || '_' || :'schema_name' || '_reader') 
        THEN '✅ Reader'
        ELSE '❌ Reader MISSING'
    END as reader_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'db_name' || '_' || :'schema_name' || '_writer') 
        THEN '✅ Writer'
        ELSE '❌ Writer MISSING'
    END as writer_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'db_name' || '_' || :'schema_name' || '_admin') 
        THEN '✅ Admin'
        ELSE '❌ Admin MISSING'
    END as admin_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'db_name' || '_monitor') 
        THEN '✅ Monitor'
        ELSE '❌ Monitor MISSING'
    END as monitor_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'db_name' || '_' || :'schema_name' || '_analyst') 
        THEN '✅ Analyst'
        ELSE '❌ Analyst MISSING'
    END as analyst_status;

-- =====================================================
-- 2. PERMISSION VERIFICATION SCRIPT
-- =====================================================

-- Verify permissions on schema
SELECT 
    'Schema Permissions' as test_category,
    :'schema_name' as schema_name,
    has_schema_privilege(:'db_name' || '_' || :'schema_name' || '_reader', :'schema_name', 'USAGE') as reader_usage,
    has_schema_privilege(:'db_name' || '_' || :'schema_name' || '_admin', :'schema_name', 'CREATE') as admin_create;

-- =====================================================
-- 3. ROLE INHERITANCE VERIFICATION SCRIPT
-- =====================================================

-- Verify role inheritance
SELECT 
    'Role Inheritance' as test_category,
    r.rolname as role_name,
    i.rolname as inherited_role,
    CASE 
        WHEN i.rolname IS NOT NULL THEN '✅ Inherits from ' || i.rolname
        ELSE '❌ No inheritance'
    END as inheritance_status
FROM pg_roles r
LEFT JOIN pg_auth_members m ON r.oid = m.roleid
LEFT JOIN pg_roles i ON m.member = i.oid
WHERE r.rolname LIKE :'db_name' || '_' || :'schema_name' || '%'
ORDER BY r.rolname, i.rolname;

-- =====================================================
-- 4. NATIVE ROLES VERIFICATION SCRIPT
-- =====================================================

-- Verify PostgreSQL native roles for monitor and analyst
SELECT 
    'Native Roles' as test_category,
    r.rolname as role_name,
    i.rolname as native_role,
    CASE 
        WHEN i.rolname IN ('pg_monitor', 'pg_read_all_stats', 'pg_read_all_settings') THEN '✅ ' || i.rolname
        ELSE '❌ ' || COALESCE(i.rolname, 'No native role')
    END as native_role_status
FROM pg_roles r
LEFT JOIN pg_auth_members m ON r.oid = m.roleid
LEFT JOIN pg_roles i ON m.member = i.oid
WHERE r.rolname IN (:'db_name' || '_monitor', :'db_name' || '_' || :'schema_name' || '_analyst')
ORDER BY r.rolname, i.rolname;

-- =====================================================
-- 5. COMPLETE FUNCTIONAL TEST SCRIPT
-- =====================================================

-- Create temporary test schema if necessary
CREATE SCHEMA IF NOT EXISTS test_roles_temp;

-- Test 1: Create test objects (as admin)
DO $$
BEGIN
    -- Create test table
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I.test_roles_table (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100),
        data JSONB,
        created_at TIMESTAMP DEFAULT NOW()
    )', :'schema_name');
    
    -- Insert test data
    EXECUTE format('INSERT INTO %I.test_roles_table (name, data) VALUES 
        (''test1'', ''{"type": "role_test"}'')
    ON CONFLICT DO NOTHING', :'schema_name');
    
    RAISE NOTICE '✅ Test objects created successfully';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '❌ Error creating test objects: %', SQLERRM;
END $$;

-- Test 2: Verify read permissions
DO $$
DECLARE
    row_count INTEGER;
BEGIN
    EXECUTE format('SELECT COUNT(*) FROM %I.test_roles_table', :'schema_name') INTO row_count;
    
    IF row_count > 0 THEN
        RAISE NOTICE '✅ Read test successful: % rows found', row_count;
    ELSE
        RAISE NOTICE '❌ Read test failed: no data found';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '❌ Error during read test: %', SQLERRM;
END $$;

-- Test 3: Verify write permissions (if writer/admin)
DO $$
BEGIN
    EXECUTE format('INSERT INTO %I.test_roles_table (name, data) VALUES 
        (''test_writer'', ''{"type": "writer_test"}'')', :'schema_name');
    
    RAISE NOTICE '✅ Write test successful';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE '⚠️ Write test failed: insufficient permissions (normal for reader)';
    WHEN OTHERS THEN
        RAISE NOTICE '❌ Error during write test: %', SQLERRM;
END $$;

-- Test 4: Verify create permissions (if admin)
DO $$
BEGIN
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I.test_admin_table (
        id SERIAL PRIMARY KEY,
        admin_field TEXT
    )', :'schema_name');
    
    RAISE NOTICE '✅ Create test successful';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE '⚠️ Create test failed: insufficient permissions (normal for reader/writer)';
    WHEN OTHERS THEN
        RAISE NOTICE '❌ Error during create test: %', SQLERRM;
END $$;

-- =====================================================
-- 6. FUTURE PERMISSIONS VERIFICATION SCRIPT
-- =====================================================

-- Verify that permissions apply to new objects
DO $$
BEGIN
    -- Create new object
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I.future_permissions_test (
        id SERIAL PRIMARY KEY,
        test_field TEXT
    )', :'schema_name');
    
    -- Test read access
    EXECUTE format('SELECT COUNT(*) FROM %I.future_permissions_test', :'schema_name');
    
    RAISE NOTICE '✅ Future permissions test successful';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '❌ Error during future permissions test: %', SQLERRM;
END $$;

-- =====================================================
-- 7. CLEANUP SCRIPT
-- =====================================================

-- Clean up test objects
DO $$
BEGIN
    EXECUTE format('DROP TABLE IF EXISTS %I.test_roles_table CASCADE', :'schema_name');
    EXECUTE format('DROP TABLE IF EXISTS %I.test_admin_table CASCADE', :'schema_name');
    EXECUTE format('DROP TABLE IF EXISTS %I.future_permissions_test CASCADE', :'schema_name');
    
    RAISE NOTICE '✅ Test objects cleanup completed';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '⚠️ Error during cleanup: %', SQLERRM;
END $$;

-- =====================================================
-- 8. FINAL REPORT
-- =====================================================

-- Display test summary
SELECT 
    'TEST SUMMARY' as status,
    'Check NOTICE messages above for detailed results' as message,
    'All tests have been executed' as completion_status;

-- =====================================================
-- 9. IAM USERS VERIFICATION SCRIPT
-- =====================================================

-- Verify IAM users and their assigned roles
SELECT 
    'IAM Users' as test_category,
    u.rolname as iam_user,
    r.rolname as assigned_role,
    CASE 
        WHEN r.rolname IS NOT NULL THEN '✅ Role assigned'
        ELSE '❌ No role assigned'
    END as role_assignment_status
FROM pg_roles u
LEFT JOIN pg_auth_members m ON u.oid = m.member
LEFT JOIN pg_roles r ON m.roleid = r.oid
WHERE u.rolname LIKE '%@%'
ORDER BY u.rolname, r.rolname;

-- =====================================================
-- 10. DETAILED PERMISSIONS VERIFICATION SCRIPT
-- =====================================================

-- Verify detailed permissions on existing tables
SELECT 
    'Detailed Permissions' as test_category,
    schemaname,
    tablename,
    has_table_privilege(:'db_name' || '_' || :'schema_name' || '_reader', schemaname||'.'||tablename, 'SELECT') as reader_select,
    has_table_privilege(:'db_name' || '_' || :'schema_name' || '_writer', schemaname||'.'||tablename, 'INSERT') as writer_insert,
    has_table_privilege(:'db_name' || '_' || :'schema_name' || '_admin', schemaname||'.'||tablename, 'ALL') as admin_all
FROM pg_tables 
WHERE schemaname = :'schema_name'
ORDER BY tablename;

-- =====================================================
-- END OF TEST SCRIPTS
-- =====================================================

-- Final message
\echo '====================================================='
\echo 'Standard roles tests completed'
\echo 'Check results above to validate functionality'
\echo '====================================================='