# Cloud SQL PostgreSQL Manager - Documentation

## 📚 Documentation Overview

This directory contains comprehensive documentation for the Cloud SQL PostgreSQL Manager, a modular FastAPI service for managing PostgreSQL databases, schemas, roles, and IAM user permissions in Google Cloud SQL.

## 📖 Documentation Structure

### 🏗️ Architecture Documentation
- **[ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md)** - High-level system architecture and design principles
- **[SERVICES.md](./SERVICES.md)** - Detailed documentation of all services and their responsibilities
- **[COMPONENTS.md](./COMPONENTS.md)** - Component system documentation and reusable business logic
- **[PLUGINS.md](./PLUGINS.md)** - Plugin system documentation for extensible role management

### 🌐 API Documentation
- **[API.md](./API.md)** - Complete API endpoint documentation with examples
- **[test_endpoints.json](./test_endpoints.json)** - Test endpoints and sample requests

### 🚀 Deployment Documentation
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Comprehensive deployment guide for various environments

## 🎯 Quick Start

### 1. Architecture Understanding
Start with [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md) to understand the system design and components.

### 2. Service Details
Read [SERVICES.md](./SERVICES.md) to understand each service's responsibilities and interactions.

### 3. API Usage
Check [API.md](./API.md) for endpoint documentation and examples.

### 4. Deployment
Follow [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment instructions.

## 🏗️ System Architecture

The system follows a **modular microservices architecture** with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Layer     │    │  Service Layer  │    │ Component Layer │
│                 │    │                 │    │                 │
│ • Health Router │    │ • ConnectionMgr │    │ • Validation    │
│ • Database Router│    │ • SchemaMgr    │    │ • ErrorHandler  │
│ • Schema Router │    │ • RoleMgr       │    │ • ServiceOps    │
│ • Role Router   │    │ • UserMgr       │    │ • DatabaseOps   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 Key Features

### Database Management
- **Schema Operations**: Create, list, and manage database schemas
- **Table Management**: List tables with metadata and statistics
- **Health Monitoring**: Comprehensive database health checks
- **Connection Pooling**: High-performance connection management

### Role-Based Access Control
- **Plugin System**: Extensible role definitions with versioning
- **Permission Levels**: `readonly`, `readwrite`, `admin` with granular control
- **IAM Integration**: Seamless Google Cloud IAM user management
- **Role Registry**: Firestore-based role tracking and history

### Security & Validation
- **Input Validation**: Comprehensive request validation
- **IAM Validation**: Service account and permission verification
- **SQL Injection Protection**: Parameterized queries and sanitization
- **Error Handling**: Secure error responses without information leakage

## 📋 Service Overview

| Service | Purpose | Key Features |
|---------|---------|--------------|
| **ConnectionManager** | Database connection pooling | High-performance, automatic recovery |
| **SchemaManager** | Schema and table operations | Creation, listing, ownership management |
| **RoleManager** | Role initialization and management | Plugin system, versioning, Firestore integration |
| **UserManager** | IAM user operations | Validation, normalization, permission checks |
| **RolePermissionManager** | Role assignments | User-role mapping, permission management |
| **HealthManager** | System monitoring | Health checks, performance metrics |

## 🔌 Plugin System

The system includes an extensible plugin architecture for role management:

- **StandardRolePlugin**: Built-in role definitions
- **CustomRolePlugin**: Custom role implementations
- **PluginRegistry**: Plugin management and loading
- **Version Control**: Role versioning and updates

## 🌐 API Endpoints

### Database Management
- `POST /database/schemas` - List database schemas
- `POST /database/tables` - List schema tables
- `POST /database/health` - Database health check

### Schema Management
- `POST /schemas/create` - Create database schema

### Role Management
- `POST /roles/initialize` - Initialize roles
- `POST /roles/assign` - Assign role to user
- `POST /roles/revoke` - Revoke role from user
- `POST /roles/list` - List available roles

## 🚀 Deployment Options

### Local Development
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Docker
```bash
docker build -t cloudsql-postgres-manager .
docker run -p 8080:8080 cloudsql-postgres-manager
```

### Google Cloud Run
```bash
gcloud run deploy cloudsql-postgres-manager \
  --image gcr.io/PROJECT_ID/cloudsql-postgres-manager \
  --platform managed \
  --region europe-west1
```

### Kubernetes
```bash
kubectl apply -f k8s/
```

## 🧪 Testing

### Unit Tests
```bash
pytest tests/unit/
```

### Integration Tests
```bash
pytest tests/integration/
```

### API Testing
```bash
python test_validation.py
```

## 📊 Monitoring

### Health Checks
- **Service Health**: `GET /health`
- **Database Health**: `POST /database/health`

### Metrics
- Request processing time
- Database connection metrics
- Error rates by endpoint
- Role operation success rates

### Logging
Structured JSON logging with correlation IDs and performance metrics.

## 🔒 Security

### Authentication
- Google Cloud IAM integration
- Service account validation
- Permission verification

### Data Protection
- Secret Manager for credentials
- Parameterized queries
- Input validation and sanitization

### Error Security
- Sanitized error messages
- No sensitive data in logs
- Structured error responses

## 📈 Performance

### Connection Pooling
- High-performance connection management
- Configurable pool sizes
- Automatic connection recovery

### Scalability
- Modular design for independent scaling
- Plugin-based extensibility
- Component reusability

## 🤝 Contributing

1. Read the architecture documentation
2. Understand the service responsibilities
3. Follow the component patterns
4. Add comprehensive tests
5. Update documentation

## 📞 Support

- **Documentation**: This directory
- **API Docs**: http://localhost:8080/docs
- **Issues**: GitHub Issues
- **Email**: support@your-org.com

## 📄 License

This project is licensed under the MIT License.

---

## 🔄 Documentation Updates

This documentation is maintained alongside the codebase. When making changes:

1. Update relevant documentation files
2. Ensure examples are current
3. Test all code examples
4. Update version numbers
5. Review for accuracy and completeness

For questions or suggestions about the documentation, please open an issue or submit a pull request.