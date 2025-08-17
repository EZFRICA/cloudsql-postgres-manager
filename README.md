# Cloud SQL PostgreSQL Manager

A comprehensive solution for automating Google Cloud SQL PostgreSQL database management and IAM user permissions across multiple databases in an organization.

## 🎯 Problem Statement

In organizations managing multiple databases, manual database administration becomes increasingly tedious and error-prone. This is especially true when dealing with Google Cloud SQL PostgreSQL instances where you need to:

- **Manually create database instances** for each project/environment
- **Manage database admin passwords** securely across multiple instances
- **Create and configure databases** within each instance
- **Add IAM users and service accounts** with appropriate permissions
- **Grant specific database permissions** to each user (readonly, readwrite, admin)
- **Maintain consistency** across multiple environments (dev, staging, production)

**The Challenge**: As your organization grows, managing dozens of PostgreSQL instances manually becomes:
- ❌ **Time-consuming**: Hours spent on repetitive database setup tasks
- ❌ **Error-prone**: Manual permission grants can lead to security issues
- ❌ **Inconsistent**: Different administrators may set up databases differently
- ❌ **Hard to audit**: No centralized way to track who has access to what
- ❌ **Difficult to scale**: Adding new databases requires manual intervention

## 💡 Solution Overview

This solution provides a complete automation framework for Google Cloud SQL PostgreSQL management using **Terraform** for infrastructure and **FastAPI/Flask** for dynamic user permission management.

### 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI/Flask │    │   Terraform     │    │   Cloud SQL     │
│   Application   │    │ Infrastructure  │    │   PostgreSQL    │
│                 │    │                 │    │                 │
│ - User Mgmt     │◄──►│ - VPC           │◄──►│ - Instances     │
│ - Permissions   │    │ - Service Acct  │    │ - Databases     │
│ - Pub/Sub       │    │ - Secret Mgmt   │    │ - Users         │
└─────────────────┘    │ - Cloud SQL     │    └─────────────────┘
                       └─────────────────┘
```

## 🚀 Solution Components

### 1. Terraform Infrastructure Automation

**Module 1: Cloud SQL Instance Creation**
- ✅ **Automated instance provisioning** with configurable machine types
- ✅ **Secure password management** - root passwords stored in Secret Manager
- ✅ **Network configuration** with private IP addresses
- ✅ **Backup and maintenance** windows configured automatically

**Module 2: Database and User Management**
- ✅ **Database creation** within instances
- ✅ **IAM user and service account** creation with proper roles
- ✅ **Role assignment** (`roles/cloudsql.instanceUser`, `roles/cloudsql.client`)
- ✅ **Multi-environment support** (dev, staging, production)

### 2. FastAPI/Flask Application

**Dynamic Permission Management**
- ✅ **RESTful API** for managing user permissions
- ✅ **Three permission levels**: readonly, readwrite, admin
- ✅ **Pub/Sub integration** for event-driven updates
- ✅ **Automatic schema creation** if needed
- ✅ **Comprehensive logging** and error handling

## 📋 Prerequisites

- Google Cloud Platform account with billing enabled
- Google Cloud SDK installed and configured
- Terraform >= 1.0 installed
- Python 3.8+ (for local development)

## 🎯 Real Usage Scenario

### Step 1: Infrastructure Setup with Terraform

```bash
# 1. Clone the repository
git clone <repository-url>
cd cloudsql-postgres-manager

# 2. Configure GCP project
export PROJECT_ID="your-gcp-project"
gcloud config set project $PROJECT_ID

# 3. Enable required APIs
gcloud services enable sqladmin.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable resourcemanager.googleapis.com

# 4. Initialize and deploy infrastructure
terraform init
terraform plan
terraform apply
```

**What Terraform automatically creates:**
- ✅ **Cloud SQL PostgreSQL instance** with private networking
- ✅ **Secret Manager secret** for secure postgres user password storage
- ✅ **Service account** with necessary IAM permissions
- ✅ **VPC and networking** resources
- ✅ **Databases** within the instance
- ✅ **IAM users and service accounts** with `roles/cloudsql.instanceUser` and `roles/cloudsql.client`

### Step 2: Verify Infrastructure

```bash
# Check created resources
gcloud sql instances list
gcloud sql databases list --instance=postgres-production-instance
gcloud secrets list

# Get connection details
terraform output
```

### Step 3: Deploy FastAPI/Flask Application

```bash
# Option 1: Local deployment
cd fastapi
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Option 2: Docker deployment
docker build -t postgres-manager ./fastapi
docker run -p 8080:8080 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json \
  postgres-manager
```

### Step 4: Manage IAM User Permissions

#### Basic User Management
```bash
# Create JSON file with user data
cat > user-management.json << 'EOF'
{
  "project_id": "your-gcp-project",
  "instance_name": "postgres-production-instance",
  "database_name": "app_db",
  "region": "europe-west1",
  "schema_name": "app_schema",
  "iam_users": [
    {
      "name": "app-service@your-gcp-project.iam.gserviceaccount.com",
      "permission_level": "readwrite"
    },
    {
      "name": "analytics-service@your-gcp-project.iam.gserviceaccount.com", 
      "permission_level": "readonly"
    },
    {
      "name": "admin-service@your-gcp-project.iam.gserviceaccount.com",
      "permission_level": "admin"
    }
  ]
}
EOF

# Call API to manage users
curl -X POST http://localhost:8080/manage-users \
  -H "Content-Type: application/json" \
  -d @user-management.json
```

### Step 5: Verify Permissions

```bash
# Connect to database to verify permissions
gcloud sql connect postgres-production-instance --user=postgres

# In PostgreSQL, check users and their permissions
\du
SELECT * FROM information_schema.role_table_grants;
```

## 📁 Project Structure

```
cloudsql-postgres-manager/
├── fastapi/                    # FastAPI application
│   ├── app/
│   │   ├── main.py            # Main application code
│   │   ├── models.py          # Pydantic models
│   │   ├── services/          # Business logic
│   │   └── utils/             # Utilities
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile            # Container configuration
├── flask/                     # Flask application (alternative)
│   ├── app/
│   │   ├── main.py           # Main application code
│   │   ├── services/         # Business logic
│   │   └── utils/            # Utilities
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile           # Container configuration
└── README.md               # This file
```

## 🔧 Configuration

### Environment Variables

The FastAPI/Flask service uses the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level | `INFO` |
| `SECRET_NAME_SUFFIX` | Secret name suffix | `postgres-password` |
| `DB_ADMIN_USER` | PostgreSQL admin user | `postgres` |

### Terraform Variables

Key variables for Terraform configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `project_id` | GCP Project ID | Required |
| `region` | GCP Region | `us-central1` |
| `instance_name` | Cloud SQL instance name | `postgres-dev-instance` |
| `machine_type` | Instance machine type | `db-f1-micro` |

## 🛠️ API Endpoints

### Health Check
```http
GET /health
```

### Direct User Management
```http
POST /manage-users
Content-Type: application/json

{
  "project_id": "your-gcp-project",
  "instance_name": "postgres-production-instance",
  "database_name": "app_db",
  "region": "europe-west1",
  "schema_name": "app_schema",
  "iam_users": [
    {
      "name": "user@project.iam.gserviceaccount.com",
      "permission_level": "readonly"
    }
  ]
}
```

### Pub/Sub Integration
```http
POST /pubsub
Content-Type: application/json

{
  "message": {
    "data": "base64-encoded-json-data",
    "attributes": {},
    "messageId": "message-id",
    "publishTime": "timestamp"
  }
}
```

## 🔐 Permission Levels

The service supports three permission levels:

1. **readonly**: SELECT permissions only
2. **readwrite**: SELECT, INSERT, UPDATE, DELETE permissions
3. **admin**: Full database administration permissions

## 🚀 Deployment Options

### Local Development

```bash
# Install dependencies
pip install -r fastapi/requirements.txt

# Run locally
cd fastapi
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Docker Deployment

```bash
# Build image
docker build -t postgres-manager ./fastapi

# Run container
docker run -p 8080:8080 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json \
  postgres-manager
```

### Google Cloud Run

```bash
# Deploy to Cloud Run
gcloud run deploy postgres-manager \
  --source ./fastapi \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated
```

## 🔍 Monitoring and Logging

### Logging

The application uses structured logging with the following levels:
- `INFO`: General application information
- `WARNING`: Warning messages
- `ERROR`: Error messages with stack traces
- `DEBUG`: Detailed debugging information

### Health Checks

The `/health` endpoint provides:
- Service status
- Version information
- Basic connectivity checks

## 🔒 Security

### IAM Permissions

The cloud run service account requires the following roles:
- `roles/cloudsql.client`
- `roles/cloudsql.instanceUser`
- `roles/secretmanager.secretAccessor`
- `roles/browser`

### Network Security

- VPC with private subnets
- Private IP addresses for database connections (PSA or PSC)
- Cloud Run need VPC Serverless Connectors or Direct VPC egress

## 🧪 Testing

### Integration Tests

```bash
# Test with sample data
curl -X POST http://localhost:8080/manage-users \
  -H "Content-Type: application/json" \
  -d @test-data.json
```

## 📚 Documentation

### API Documentation

Once the service is running, visit:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

### Customization and Extensions

The project includes a `pseudocode/` directory with examples and guides for customizing the default behavior:

- **`pseudocode/README.md`**: Overview of customization approaches
- **`pseudocode/revoke_object_permissions.md`**: Examples for custom permission revocation logic

These pseudocode examples demonstrate how to:
- Implement role-based permission strategies
- Add audit trails and logging
- Create conditional permission logic
- Integrate with external systems
- Optimize performance for specific use cases

See the `pseudocode/` directory for detailed implementation examples and best practices.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the logs for debugging information

## 🔄 Version History

- **v0.1.0**: Initial release with FastAPI/Flask service and Terraform/Pulumi infrastructure

---

**Note**: This solution is designed for production use but should be thoroughly tested in your specific environment before deployment.