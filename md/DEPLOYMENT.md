# Deployment Guide

## 🚀 Deployment Overview

This guide covers deploying the Cloud SQL PostgreSQL Manager in various environments with proper configuration and monitoring.

## 📋 Prerequisites

### System Requirements
- **Python**: 3.11+
- **Memory**: 512MB minimum, 2GB recommended
- **CPU**: 1 core minimum, 2 cores recommended
- **Storage**: 1GB for application, additional for logs

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

## 🐳 Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Build and Run
```bash
# Build image
docker build -t cloudsql-postgres-manager:latest .

# Run container
docker run -d \
  --name cloudsql-manager \
  -p 8080:8080 \
  --env-file .env \
  cloudsql-postgres-manager:latest
```

### Docker Compose
```yaml
version: '3.8'

services:
  cloudsql-manager:
    build: .
    ports:
      - "8080:8080"
    environment:
      - APP_NAME=Cloud SQL PostgreSQL Manager
      - LOG_LEVEL=INFO
      - CONNECTION_POOL_SIZE=10
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
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
  --memory 2Gi \
  --cpu 2 \
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
            cpu: "2"
            memory: "2Gi"
          requests:
            cpu: "1"
            memory: "1Gi"
```

## ☸️ Kubernetes Deployment

### Namespace
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cloudsql-manager
```

### ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cloudsql-manager-config
  namespace: cloudsql-manager
data:
  APP_NAME: "Cloud SQL PostgreSQL Manager"
  LOG_LEVEL: "INFO"
  CONNECTION_POOL_SIZE: "10"
  ALLOWED_REGIONS: "europe-west1,us-central1,asia-southeast1"
```

### Secret
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: cloudsql-manager-secrets
  namespace: cloudsql-manager
type: Opaque
data:
  # Base64 encoded values
  SECRET_PROJECT_ID: eW91ci1wcm9qZWN0LWlk
  FIRESTORE_PROJECT_ID: eW91ci1wcm9qZWN0LWlk
```

### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudsql-postgres-manager
  namespace: cloudsql-manager
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cloudsql-postgres-manager
  template:
    metadata:
      labels:
        app: cloudsql-postgres-manager
    spec:
      containers:
      - name: cloudsql-postgres-manager
        image: gcr.io/YOUR_PROJECT_ID/cloudsql-postgres-manager:latest
        ports:
        - containerPort: 8080
        envFrom:
        - configMapRef:
            name: cloudsql-manager-config
        - secretRef:
            name: cloudsql-manager-secrets
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: cloudsql-postgres-manager-service
  namespace: cloudsql-manager
spec:
  selector:
    app: cloudsql-postgres-manager
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

### HorizontalPodAutoscaler
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: cloudsql-postgres-manager-hpa
  namespace: cloudsql-manager
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cloudsql-postgres-manager
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
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

### Network Security
```yaml
# NetworkPolicy for Kubernetes
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cloudsql-manager-netpol
  namespace: cloudsql-manager
spec:
  podSelector:
    matchLabels:
      app: cloudsql-postgres-manager
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 5432  # PostgreSQL
    - protocol: TCP
      port: 443   # HTTPS for Google APIs
```

## 📊 Monitoring and Observability

### Prometheus Metrics
```yaml
# ServiceMonitor for Prometheus
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: cloudsql-postgres-manager
  namespace: cloudsql-manager
spec:
  selector:
    matchLabels:
      app: cloudsql-postgres-manager
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### Grafana Dashboard
```json
{
  "dashboard": {
    "title": "Cloud SQL PostgreSQL Manager",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Database Connection Pool",
        "type": "graph",
        "targets": [
          {
            "expr": "cloudsql_connection_pool_active",
            "legendFormat": "Active Connections"
          }
        ]
      }
    ]
  }
}
```

### Logging Configuration
```yaml
# Fluentd configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: cloudsql-manager
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/cloudsql-postgres-manager*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      format json
    </source>
    
    <match kubernetes.**>
      @type elasticsearch
      host elasticsearch.logging.svc.cluster.local
      port 9200
      index_name cloudsql-manager
    </match>
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
# View application logs
kubectl logs -f deployment/cloudsql-postgres-manager -n cloudsql-manager

# Filter error logs
kubectl logs deployment/cloudsql-postgres-manager -n cloudsql-manager | grep ERROR

# View specific pod logs
kubectl logs -f pod/cloudsql-postgres-manager-xxx -n cloudsql-manager
```

## 📈 Performance Tuning

### Database Connection Optimization
```bash
# Optimize connection pool
CONNECTION_POOL_SIZE=20
CONNECTION_POOL_MAX_OVERFLOW=40
CONNECTION_TIMEOUT=30
```

### Memory Optimization
```bash
# Increase memory limits
MEMORY_LIMIT=4Gi
MEMORY_REQUEST=2Gi
```

### CPU Optimization
```bash
# Increase CPU limits
CPU_LIMIT=2000m
CPU_REQUEST=1000m
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