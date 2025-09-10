# Services Documentation

## 🏗️ Service Layer Architecture

The service layer contains the core business logic organized into specialized services, each with a single responsibility.

## 📋 Service Overview

| Service | Responsibility | Dependencies |
|---------|---------------|--------------|
| `ConnectionManager` | Database connection pooling and management | None |
| `SchemaManager` | Schema creation, listing, and table operations | `ConnectionManager` |
| `RoleManager` | Role initialization and plugin management | `ConnectionManager`, `FirestoreRoleRegistryManager` |
| `UserManager` | IAM user validation and operations | `ConnectionManager` |
| `RolePermissionManager` | Role assignments and permissions | `ConnectionManager`, `SchemaManager`, `UserManager` |
| `HealthManager` | Database health monitoring | `ConnectionManager` |
| `DatabaseValidator` | Centralized database validation utilities | None |
| `FirestoreRoleRegistryManager` | Firestore role registry management | None |

## 🔌 ConnectionManager

**Purpose**: High-performance database connection management with pooling.

### Key Features
- Connection pooling with configurable sizes
- Automatic connection recovery
- Connection health monitoring
- Transaction management

### Methods
```python
def get_connection(project_id, region, instance_name, database_name)
def execute_sql_safely(cursor, sql, params=None)
def close()
def get_pool_stats()
```

### Configuration
```python
CONNECTION_POOL_SIZE = 10
CONNECTION_POOL_MAX_OVERFLOW = 20
CONNECTION_TIMEOUT = 30
```

## 🗄️ SchemaManager

**Purpose**: Database schema and table management operations.

### Key Features
- Schema creation with owner validation
- Schema listing and metadata
- Table listing with statistics
- Ownership management

### Methods
```python
def create_schema(project_id, region, instance_name, database_name, schema_name, owner=None)
def list_schemas(project_id, region, instance_name, database_name)
def list_tables(project_id, region, instance_name, database_name, schema_name)
def change_schema_owner(connection, schema_name, new_owner)
def role_exists(cursor, role_name)
```

### Schema Creation Flow
1. Validate schema name and database name
2. Check if schema already exists
3. Validate owner (if provided)
4. Grant role to postgres (if needed)
5. Create schema with appropriate ownership
6. Return success/failure response

## 👥 RoleManager

**Purpose**: PostgreSQL role initialization and plugin-based role management.

### Key Features
- Plugin-based role definitions
- Role versioning and checksums
- Firestore registry integration
- Idempotent role operations

### Methods
```python
def initialize_roles(project_id, instance_name, database_name, region, schema_name, force_update=False)
def get_role_status(project_id, instance_name, database_name)
def load_plugin(plugin_module_path)
def list_roles(project_id, region, instance_name, database_name)
```

### Role Initialization Flow
1. Load standard and custom plugins
2. Get role definitions for schema
3. Validate role definitions
4. Create/update roles in database
5. Update Firestore registry
6. Return operation results

## 👤 UserManager

**Purpose**: IAM user validation and user-related operations.

### Key Features
- IAM user validation
- Service account name normalization
- User permission verification
- Grant/revoke operations

### Methods
```python
def normalize_service_account_name(email)
def validate_iam_permissions(project_id, users)
def get_users_and_roles(project_id, region, instance_name, database_name, schema_name)
def grant_user_to_postgres(project_id, region, instance_name, database_name, username)
def revoke_user_from_postgres(project_id, region, instance_name, database_name, username)
```

### IAM Validation Flow
1. Normalize service account email
2. Validate IAM permissions
3. Check user existence in database
4. Perform requested operations
5. Return operation results

## 🔐 RolePermissionManager

**Purpose**: Role assignment and permission management operations.

### Key Features
- Role assignment to users
- Permission revocation
- Role validation
- Transaction safety

### Methods
```python
def assign_role(project_id, region, instance_name, database_name, schema_name, username, role_name)
def revoke_role(project_id, region, instance_name, database_name, schema_name, username, role_name)
def get_users_and_roles(project_id, region, instance_name, database_name, schema_name)
```

### Role Assignment Flow
1. Validate user and role existence
2. Check current permissions
3. Execute role assignment
4. Verify assignment success
5. Return operation results

## 🏥 HealthManager

**Purpose**: Database health monitoring and diagnostics.

### Key Features
- Connection health checks
- Database performance metrics
- Uptime monitoring
- Connection timing

### Methods
```python
def check_database_health(project_id, region, instance_name, database_name)
```

### Health Check Flow
1. Establish database connection
2. Measure connection time
3. Query database information
4. Calculate uptime and metrics
5. Return health status

## 🔄 Service Interactions

### 1. Schema Creation with Owner
```
SchemaManager → ConnectionManager → PostgreSQL
     ↓
UserManager (validate owner)
     ↓
RolePermissionManager (grant permissions)
```

### 2. Role Initialization
```
RoleManager → PluginRegistry → RoleDefinitions
     ↓
ConnectionManager → PostgreSQL
     ↓
FirestoreRoleRegistryManager → Firestore
```

### 3. User Permission Assignment
```
RolePermissionManager → UserManager (validate user)
     ↓
SchemaManager (check schema)
     ↓
ConnectionManager → PostgreSQL
```

## 🧪 Testing Services

### Unit Testing
Each service can be tested independently with mocked dependencies:

```python
def test_schema_manager():
    with patch('app.services.schema_manager.ConnectionManager'):
        manager = SchemaManager(ConnectionManager())
        # Test methods
```

### Integration Testing
Services are tested together with real database connections:

```python
def test_schema_creation_integration():
    # Test with real database
    result = schema_manager.create_schema(...)
    assert result["success"] == True
```

## 📊 Service Metrics

### ConnectionManager Metrics
- Active connections
- Pool utilization
- Connection errors
- Average connection time

### SchemaManager Metrics
- Schema creation success rate
- Average creation time
- Validation errors

### RoleManager Metrics
- Role initialization time
- Plugin loading success
- Registry update success

### HealthManager Metrics
- Health check response time
- Database uptime
- Connection performance

## 🔧 Configuration

### Service Configuration
Each service can be configured through environment variables:

```bash
# Connection Manager
CONNECTION_POOL_SIZE=10
CONNECTION_POOL_MAX_OVERFLOW=20

# Role Manager
FIRESTORE_PROJECT_ID=your-project
FIRESTORE_COLLECTION=role_registries

# Health Manager
HEALTH_CHECK_TIMEOUT=30
```

## 🔍 DatabaseValidator

**Purpose**: Centralized database validation utilities to avoid duplication across managers.

### Key Features
- Role existence validation
- Schema existence validation
- Database existence validation
- IAM user validation
- User role retrieval
- Service account name normalization

### Methods
```python
def role_exists(cursor, role_name)
def schema_exists(cursor, schema_name)
def database_exists(cursor, database_name)
def is_iam_user(cursor, username)
def get_user_roles(cursor, username, schema_prefix=None)
def normalize_service_account_name(username)
def validate_schema_name(schema_name)
def validate_database_name(database_name)
```

### Usage Example
```python
from app.services.database_validator import DatabaseValidator

# Check if role exists
if DatabaseValidator.role_exists(cursor, "my_role"):
    # Role exists, proceed with operation
    pass

# Validate IAM user
if DatabaseValidator.is_iam_user(cursor, "user@project.iam"):
    # Valid IAM user, proceed with operation
    pass
```

## 🔥 FirestoreRoleRegistryManager

**Purpose**: Firestore-based role registry management for tracking role initialization state.

### Key Features
- Role registry document management
- Role initialization state tracking
- Role definition storage and retrieval
- Creation history tracking
- Version control and checksums

### Methods
```python
def get_registry_document(project_id, instance_name, database_name)
def create_registry_document(project_id, instance_name, database_name, roles_definitions)
def update_registry_document(project_id, instance_name, database_name, updates)
def delete_registry_document(project_id, instance_name, database_name)
```

### Usage Example
```python
from app.services.firebase import FirestoreRoleRegistryManager

firestore_manager = FirestoreRoleRegistryManager()

# Get role registry
registry = firestore_manager.get_registry_document(
    "my-project", "my-instance", "my-database"
)

# Create new registry
firestore_manager.create_registry_document(
    "my-project", "my-instance", "my-database", roles_definitions
)
```

### Service Dependencies
Services are initialized with their dependencies:

```python
# Service initialization
connection_manager = ConnectionManager()
schema_manager = SchemaManager(connection_manager)
role_manager = RoleManager()
user_manager = UserManager(connection_manager)
health_manager = HealthManager(connection_manager)
database_validator = DatabaseValidator()
firestore_manager = FirestoreRoleRegistryManager()
```