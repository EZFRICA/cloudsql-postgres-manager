# Cloud SQL PostgreSQL Manager

A complete solution for managing Google Cloud SQL PostgreSQL instances, databases, and IAM user permissions with FastAPI/Flask service and Terraform infrastructure.

## 🚀 Features

- **FastAPI/Flask Service**: RESTful API for managing PostgreSQL instances and IAM user permissions
- **Terraform Infrastructure**: Complete infrastructure as code for GCP resources
- **IAM User Management**: Automated creation and permission management for IAM users
- **Secret Management**: Secure password storage using Google Secret Manager
- **Pub/Sub Integration**: Event-driven architecture for automated user management
- **Multi-Environment Support**: Separate configurations for dev, staging, and production

## 📋 Prerequisites

- Google Cloud Platform account with billing enabled
- Google Cloud SDK installed and configured
- Terraform >= 1.0 installed
- Python 3.8+ (for local development)

## 🏗️ Architecture

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

## 🎯 Real Usage Scenario

### Step 1: Create Infrastructure with Terraform

```bash
# 1. Clone the repository
git clone <repository-url>
cd cloudsql-postgres-manager

# 2. Configure GCP project
export PROJECT_ID="your-gcp-project"
gcloud config set project $PROJECT_ID

# 3. Enable required APIs



# 6. Deploy infrastructure
terraform init
terraform plan
terraform apply
```

**What Terraform will create for you:**
- ✅ Cloud SQL PostgreSQL instance
- ✅ Secret Manager secret for database password
- ✅ Service account with necessary permissions
- ✅ VPC and networking resources
- ✅ Databases when you need

### Step 2: Verify Your Infrastructure

```bash
# Check what was created
gcloud sql instances list
gcloud sql databases list --instance=postgres-production-instance
gcloud secrets list

# Get connection details
terraform output
```

### Step 3: Deploy FastAPI/Flask Application

```bash
# Option 1: Local deployment
cd ../../fastapi
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080

# Option 2: Docker deployment
docker build -t postgres-manager .
docker run -p 8080:8080 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json \
  postgres-manager
```

### Step 4: Call API to Manage IAM Users

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
│   ├── main.py                # Main application code
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile            # Container configuration
├── flask/                     # Flask application (alternative)
│   ├── main.py               # Main application code
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
| `DB_POSTGRES_USER` | PostgreSQL admin user | `postgres` |

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
uvicorn main:app --reload --host 0.0.0.0 --port 8080
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
- Firewall rules for Cloud SQL and FastAPI/Flask
- Private IP addresses for database connections
- Cloud Run need VPC Serverless Connectors or Direct VPC egress

## 🧪 Testing

### Unit Tests

```bash
# Run tests
python -m pytest tests/
```

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


## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the logs for debugging information

## 🔄 Version History

- **v1.0.0**: Initial release with FastAPI service and Terraform infrastructure
- **v1.1.0**: Added Pub/Sub integration and enhanced IAM management
- **v1.2.0**: Multi-environment support and improved security
- **v1.3.0**: Added Flask service and complete usage scenario

---

**Note**: This solution is designed for production use but should be thoroughly tested in your specific environment before deployment.