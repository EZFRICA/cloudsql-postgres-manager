# API Documentation

## 🌐 API Overview

The Cloud SQL PostgreSQL Manager provides a comprehensive REST API for managing PostgreSQL databases, schemas, roles, and IAM user permissions.

## 📋 API Endpoints

| Endpoint | Method | Purpose | Service |
|----------|--------|---------|---------|
| `/health` | GET | Service health check | Health |
| `/database/schemas` | POST | List database schemas | SchemaManager |
| `/database/tables` | POST | List schema tables | SchemaManager |
| `/database/health` | POST | Database health check | HealthManager |
| `/database/grant-user` | POST | Grant user to postgres | UserManager |
| `/database/revoke-user` | POST | Revoke user from postgres | UserManager |
| `/schemas/create` | POST | Create database schema | SchemaManager |
| `/roles/initialize` | POST | Initialize roles | RoleManager |
| `/roles/assign` | POST | Assign role to user | RolePermissionManager |
| `/roles/revoke` | POST | Revoke role from user | RolePermissionManager |
| `/roles/users` | POST | List users and roles | RolePermissionManager |
| `/roles/list` | POST | List available roles | RoleManager |

## 🏥 Health Endpoints

### GET /health
Basic service health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "0.1.0"
}
```

## 🗄️ Database Endpoints

### POST /database/schemas
List all schemas in a database.

**Request:**
```json
{
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "region": "europe-west1"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Retrieved 3 schemas",
  "schemas": ["public", "app_schema", "analytics_schema"],
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "execution_time_seconds": 0.123
}
```

### POST /database/tables
List all tables in a specific schema.

**Request:**
```json
{
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "schema_name": "app_schema",
  "region": "europe-west1"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Retrieved 5 tables",
  "tables": [
    {
      "table_name": "users",
      "table_type": "BASE TABLE",
      "row_count": 1000,
      "size_bytes": 65536
    },
    {
      "table_name": "orders",
      "table_type": "BASE TABLE",
      "row_count": 5000,
      "size_bytes": 131072
    }
  ],
  "schema_name": "app_schema",
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "execution_time_seconds": 0.456
}
```

### POST /database/health
Check database health and performance.

**Request:**
```json
{
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "region": "europe-west1"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Database is healthy",
  "status": "healthy",
  "connection_time_ms": 45.2,
  "database_info": {
    "version": "PostgreSQL 15.4",
    "uptime": "5 days, 12 hours",
    "active_connections": 8
  },
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "execution_time_seconds": 0.234
}
```

### POST /database/grant-user
Grant IAM user to postgres role.

**Request:**
```json
{
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "username": "service@project.iam.gserviceaccount.com",
  "region": "europe-west1"
}
```

**Response:**
```json
{
  "success": true,
  "message": "User granted to postgres successfully",
  "username": "service@project.iam",
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "execution_time_seconds": 0.345
}
```

### POST /database/revoke-user
Revoke IAM user from postgres role.

**Request:**
```json
{
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "username": "service@project.iam.gserviceaccount.com",
  "region": "europe-west1"
}
```

**Response:**
```json
{
  "success": true,
  "message": "User revoked from postgres successfully",
  "username": "service@project.iam",
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "execution_time_seconds": 0.234
}
```

## 🏗️ Schema Endpoints

### POST /schemas/create
Create a new database schema.

**Request:**
```json
{
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "schema_name": "app_schema",
  "owner": "service@project.iam.gserviceaccount.com",
  "region": "europe-west1"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Schema created successfully",
  "schema_name": "app_schema",
  "owner": "service@project.iam",
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "execution_time_seconds": 0.567
}
```

## 👥 Role Endpoints

### POST /roles/initialize
Initialize roles for a database schema.

**Request:**
```json
{
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "schema_name": "app_schema",
  "force_update": false,
  "region": "europe-west1"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Role initialization completed. Created: 3, Updated: 0, Skipped: 0",
  "roles_created": ["reader_app_schema", "writer_app_schema", "admin_app_schema"],
  "roles_updated": [],
  "roles_skipped": [],
  "total_roles": 3,
  "firebase_document_id": "my-project_my-instance_my-database",
  "execution_time_seconds": 2.345
}
```

### POST /roles/assign
Assign a role to a user.

**Request:**
```json
{
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "schema_name": "app_schema",
  "username": "user@project.iam.gserviceaccount.com",
  "role_name": "reader_app_schema",
  "region": "europe-west1"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Role assigned successfully",
  "username": "user@project.iam",
  "role_name": "reader_app_schema",
  "schema_name": "app_schema",
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "execution_time_seconds": 0.456
}
```

### POST /roles/revoke
Revoke a role from a user.

**Request:**
```json
{
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "schema_name": "app_schema",
  "username": "user@project.iam.gserviceaccount.com",
  "role_name": "reader_app_schema",
  "region": "europe-west1"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Role revoked successfully",
  "username": "user@project.iam",
  "role_name": "reader_app_schema",
  "schema_name": "app_schema",
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "execution_time_seconds": 0.345
}
```

### POST /roles/users
List users and their roles for a schema.

**Request:**
```json
{
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "schema_name": "app_schema",
  "region": "europe-west1"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Retrieved 2 users with roles",
  "users": [
    {
      "username": "user1@project.iam",
      "roles": ["reader_app_schema"],
      "permissions": ["SELECT"]
    },
    {
      "username": "user2@project.iam",
      "roles": ["writer_app_schema"],
      "permissions": ["SELECT", "INSERT", "UPDATE", "DELETE"]
    }
  ],
  "schema_name": "app_schema",
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "execution_time_seconds": 0.678
}
```

### POST /roles/list
List all available roles in a database.

**Request:**
```json
{
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "region": "europe-west1"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Retrieved 5 roles",
  "roles": [
    "reader_app_schema",
    "writer_app_schema",
    "admin_app_schema",
    "analyst_app_schema",
    "custom_role"
  ],
  "project_id": "my-project",
  "instance_name": "my-instance",
  "database_name": "my-database",
  "execution_time_seconds": 0.234
}
```

## 🚨 Error Responses

### Validation Error
```json
{
  "success": false,
  "error_type": "validation_error",
  "message": "Validation failed",
  "details": {
    "field": "schema_name",
    "error": "Must be alphanumeric and start with a letter"
  },
  "execution_time_seconds": 0.001
}
```

### Database Error
```json
{
  "success": false,
  "error_type": "database_error",
  "message": "Database operation failed",
  "details": {
    "error": "Connection timeout",
    "code": "08006"
  },
  "execution_time_seconds": 30.0
}
```

### Authentication Error
```json
{
  "success": false,
  "error_type": "authentication_error",
  "message": "IAM user validation failed",
  "details": {
    "username": "invalid@project.iam",
    "error": "User not found in IAM"
  },
  "execution_time_seconds": 0.123
}
```

## 🔒 Authentication

### Required Headers
```http
Content-Type: application/json
Authorization: Bearer <service-account-token>
```

### Service Account Permissions
- `roles/cloudsql.client` - Connect to Cloud SQL
- `roles/secretmanager.secretAccessor` - Access database passwords
- `roles/iam.serviceAccountTokenCreator` - Validate IAM users
- `roles/datastore.user` - Access Firestore (optional)

## 📊 Rate Limiting

### Limits
- **Requests per minute**: 1000
- **Concurrent connections**: 100
- **Database operations per minute**: 500

### Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## 🧪 Testing

### Test Endpoints
Use the provided test endpoints file for comprehensive testing:

```bash
# Load test endpoints
curl -X POST http://localhost:8080/database/schemas \
  -H "Content-Type: application/json" \
  -d @test_endpoints.json
```

### Validation Testing
```bash
# Test validation
python test_validation.py
```

### Component Testing
```bash
# Test components
python test_components.py
```

## 📈 Monitoring

### Health Checks
- **Service Health**: `GET /health`
- **Database Health**: `POST /database/health`

### Metrics
- Request processing time
- Database connection time
- Error rates by endpoint
- Role operation success rates

### Logging
Structured JSON logging with:
- Request correlation IDs
- Performance metrics
- Error details
- Security events

## 🔧 Configuration

### Environment Variables
```bash
# API settings
API_HOST=0.0.0.0
API_PORT=8080
API_WORKERS=4

# Database settings
CONNECTION_POOL_SIZE=10
CONNECTION_TIMEOUT=30

# Security settings
ALLOWED_REGIONS=europe-west1,us-central1,asia-southeast1
MAX_USERS_PER_REQUEST=100
```

### CORS Configuration
```python
# CORS settings
CORS_ORIGINS = ["https://your-domain.com"]
CORS_METHODS = ["GET", "POST"]
CORS_HEADERS = ["Content-Type", "Authorization"]
```