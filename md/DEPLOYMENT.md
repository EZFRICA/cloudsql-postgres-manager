# Deployment Guide

## 🚀 Deployment Overview

This guide covers deploying the Cloud SQL PostgreSQL Manager on Google Cloud Run with proper configuration and monitoring.

## 📋 Prerequisites

### System Requirements
- **Python**: 3.11+
- **Memory**: 512MB minimum for Cloud Run
- **CPU**: 1 core minimum for Cloud Run

### Google Cloud Requirements
- **Cloud SQL**: PostgreSQL 13+ instances
- **Secret Manager**: For database credentials
- **IAM**: Service account with required permissions
- **Firestore**: For role registry (optional)

## 🔧 Configuration

### Environment Variables

#### Application Settings
```bash
# Basic configuration
APP_NAME=Cloud SQL PostgreSQL Manager
APP_VERSION=0.1.0
DEBUG=false
LOG_LEVEL=INFO

# API configuration
API_HOST=0.0.0.0
API_PORT=8080
API_WORKERS=4
```

#### Database Settings
```bash
# Connection settings
CONNECTION_POOL_SIZE=10
CONNECTION_POOL_MAX_OVERFLOW=20
CONNECTION_TIMEOUT=30
CONNECTION_RETRY_ATTEMPTS=3

# Secret Manager
SECRET_NAME_SUFFIX=postgres-password
SECRET_PROJECT_ID=your-project-id
```

#### Security Settings
```bash
# IAM and permissions
ALLOWED_REGIONS=europe-west1,us-central1,asia-southeast1
MAX_USERS_PER_REQUEST=100
VALIDATE_IAM_USERS=true

# CORS settings
CORS_ORIGINS=https://your-domain.com,https://admin.your-domain.com
CORS_METHODS=GET,POST,PUT,DELETE
CORS_HEADERS=Content-Type,Authorization
```

#### Firestore Settings (Optional)
```bash
# Firestore configuration
FIRESTORE_PROJECT_ID=your-project-id
FIRESTORE_COLLECTION=role_registries
FIRESTORE_CACHE_TTL=3600
```

#### Monitoring Settings
```bash
# Logging
LOG_FORMAT=json
LOG_CORRELATION_IDS=true
LOG_PERFORMANCE_METRICS=true

# Health checks
HEALTH_CHECK_TIMEOUT=30
HEALTH_CHECK_INTERVAL=60
```

## 🐳 Dockerfile pour Cloud Run

### Dockerfile
```dockerfile
# Use official Python image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security
RUN adduser --disabled-password --gecos "" myuser

# Copy the rest of the application code
COPY . .

# Change ownership to non-root user
RUN chown -R myuser:myuser /app

# Switch to non-root user
USER myuser

# Expose the port used by FastAPI
EXPOSE 8080

# Command to start the FastAPI application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"] 
```

## ☁️ Google Cloud Run

### Build and Push
```bash
# Configure gcloud
gcloud config set project YOUR_PROJECT_ID

# Build and push to Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/cloudsql-postgres-manager

# Or use Artifact Registry
gcloud builds submit --tag europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/cloudsql-manager/cloudsql-postgres-manager
```

### Deploy to Cloud Run
```bash
# Deploy with environment variables
gcloud run deploy cloudsql-postgres-manager \
  --image gcr.io/YOUR_PROJECT_ID/cloudsql-postgres-manager \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 10 \
  --set-env-vars "LOG_LEVEL=INFO,CONNECTION_POOL_SIZE=10"
```

### Cloud Run Service Configuration
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: cloudsql-postgres-manager
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/execution-environment: gen2
    spec:
      containerConcurrency: 100
      timeoutSeconds: 300
      containers:
      - image: gcr.io/YOUR_PROJECT_ID/cloudsql-postgres-manager
        ports:
        - containerPort: 8080
        env:
        - name: LOG_LEVEL
          value: "INFO"
        - name: CONNECTION_POOL_SIZE
          value: "10"
        resources:
          limits:
            cpu: "1"
            memory: "512Mi"
          requests:
            cpu: "1"
            memory: "512Mi"
```


## 🔒 Security Configuration

### Service Account
```bash
# Create service account
gcloud iam service-accounts create cloudsql-manager-sa \
  --display-name="Cloud SQL Manager Service Account"

# Grant required permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:cloudsql-manager-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:cloudsql-manager-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:cloudsql-manager-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:cloudsql-manager-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

### Cloud Run Security
```bash
# Configure Cloud Run security
# Enable VPC connector for private database access
gcloud run services update cloudsql-postgres-manager \
  --vpc-connector=projects/YOUR_PROJECT_ID/locations/europe-west1/connectors/YOUR_CONNECTOR \
  --vpc-egress=private-ranges-only

# Configure IAM for Cloud Run
gcloud run services add-iam-policy-binding cloudsql-postgres-manager \
  --member="user:admin@your-domain.com" \
  --role="roles/run.invoker"
```

## 📊 Monitoring and Observability

### Cloud Monitoring
```bash
# Enable Cloud Monitoring for Cloud Run
gcloud services enable monitoring.googleapis.com

# View metrics in Cloud Console
# Go to: Monitoring > Metrics Explorer
# Filter by: cloud_run_revision
```

### Cloud Logging
```bash
# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=cloudsql-postgres-manager" --limit=50

# Stream logs in real-time
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=cloudsql-postgres-manager"
```

### Alerting
```bash
# Create alert policy for error rate
gcloud alpha monitoring policies create --policy-from-file=alert-policy.yaml
```

### Alert Policy Example
```yaml
# alert-policy.yaml
displayName: "Cloud SQL Manager High Error Rate"
conditions:
  - displayName: "Error rate > 5%"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND resource.labels.service_name="cloudsql-postgres-manager" AND severity>=ERROR'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 0.05
      duration: 300s
notificationChannels:
  - "projects/YOUR_PROJECT_ID/notificationChannels/YOUR_CHANNEL_ID"
```

## 🧪 Testing Deployment

### Health Checks
```bash
# Test service health
curl http://localhost:8080/health

# Test database health
curl -X POST http://localhost:8080/database/health \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "your-project",
    "instance_name": "your-instance",
    "database_name": "your-database",
    "region": "europe-west1"
  }'
```

### Load Testing
```bash
# Install hey
go install github.com/rakyll/hey@latest

# Run load test
hey -n 1000 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -d '{"project_id":"test","instance_name":"test","database_name":"test","region":"europe-west1"}' \
  http://localhost:8080/database/schemas
```

### Integration Testing
```bash
# Run integration tests
pytest tests/integration/ -v

# Run with coverage
pytest --cov=app --cov-report=html tests/
```

## 🔄 CI/CD Pipeline

### GitHub Actions
```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest
    
    - name: Run tests
      run: pytest tests/
    
    - name: Build and push
      run: |
        gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/cloudsql-postgres-manager
    
    - name: Deploy to Cloud Run
      run: |
        gcloud run deploy cloudsql-postgres-manager \
          --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/cloudsql-postgres-manager \
          --platform managed \
          --region europe-west1 \
          --allow-unauthenticated
```

## 🚨 Troubleshooting

### Common Issues

#### Connection Pool Exhaustion
```bash
# Check connection pool status
curl http://localhost:8080/health

# Increase pool size
export CONNECTION_POOL_SIZE=20
```

#### IAM Permission Errors
```bash
# Check service account permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:cloudsql-manager-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com"
```

#### Database Connection Issues
```bash
# Test database connectivity
gcloud sql connect YOUR_INSTANCE --user=postgres --database=YOUR_DATABASE
```

### Log Analysis
```bash
# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=cloudsql-postgres-manager" --limit=100

# Filter error logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=cloudsql-postgres-manager AND severity>=ERROR" --limit=50

# Stream logs in real-time
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=cloudsql-postgres-manager"
```

## 📈 Performance Tuning

### Database Connection Optimization
```bash
# Optimize connection pool
CONNECTION_POOL_SIZE=20
CONNECTION_POOL_MAX_OVERFLOW=40
CONNECTION_TIMEOUT=30
```

### Cloud Run Optimization
```bash
# Optimize Cloud Run settings
gcloud run services update cloudsql-postgres-manager \
  --memory=1Gi \
  --cpu=1 \
  --max-instances=20 \
  --concurrency=100
```

## 🔄 Backup and Recovery

### Database Backups
```bash
# Create database backup
gcloud sql backups create --instance=YOUR_INSTANCE

# Restore from backup
gcloud sql backups restore BACKUP_ID --instance=YOUR_INSTANCE
```

### Application State Backup
```bash
# Backup Firestore data
gcloud firestore export gs://YOUR_BUCKET/backup-$(date +%Y%m%d)

# Restore Firestore data
gcloud firestore import gs://YOUR_BUCKET/backup-20240101
```