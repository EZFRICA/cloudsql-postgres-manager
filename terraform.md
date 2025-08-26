# Terraform Documentation - Cloud SQL with Secret Manager

## Overview

This documentation presents a complete Terraform workflow for creating and configuring a Cloud SQL instance securely. The process follows security best practices by using Secret Manager to store passwords and enabling IAM authentication.

## Workflow Architecture

1. **Generate a secure password**
2. **Create a Cloud SQL instance with IAM authentication enabled**
3. **Store the password in Secret Manager**
4. **Create a database in the instance**
5. **Add IAM users and grant permissions to connect to the instance**

---

## 1. Generate a Secure Password

### Objective
Automatically generate a robust password for the Cloud SQL instance.

### Terraform Code

```hcl
# Generate a random password
resource "random_password" "db_password" {
  length  = 16
  special = true
  upper   = true
  lower   = true
  numeric = true
}

# Alternative with custom special characters
resource "random_password" "db_password_custom" {
  length      = 26
  special     = true
  min_special = 2
  min_upper   = 2
  min_lower   = 2
  min_numeric = 2
}
```

### Explanations
- `length`: Password length (minimum recommended: 12 characters)
- `special`: Includes special characters (!@#$%^&*)
- `upper/lower/numeric`: Forces inclusion of uppercase, lowercase, and numbers
- `min_*`: Minimum number of each character type

---

## 2. Create a Cloud SQL Instance with IAM Authentication

### Objective
Deploy a Cloud SQL PostgreSQL instance with the generated password and **IAM authentication enabled**.

### Terraform Code

```hcl
# Cloud SQL Instance with IAM authentication enabled
resource "google_sql_database_instance" "main_instance" {
  name             = "my-sql-instance"
  database_version = "POSTGRES_14"
  region          = "europe-west1"
  
  settings {
    tier = "db-f1-micro"
    
    # CRITICAL: Enable IAM authentication
    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
    
    # Backup configuration
    backup_configuration {
      enabled                        = true
      start_time                    = "03:00"
      point_in_time_recovery_enabled = true
    }
    
    # Network configuration
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
      require_ssl     = true
    }
    
    # Maintenance window
    maintenance_window {
      day          = 7
      hour         = 3
      update_track = "stable"
    }
  }
  
  # Deletion protection
  deletion_protection = true
}

# Root user with generated password
resource "google_sql_user" "root_user" {
  name     = "postgres"
  instance = google_sql_database_instance.main_instance.name
  password = random_password.db_password.result
}
```

### ⚠️ IMPORTANT: Enabling IAM Authentication

**You MUST enable IAM authentication on the Cloud SQL instance before adding IAM users.** This is done using the database flag:

```hcl
database_flags {
  name  = "cloudsql.iam_authentication"
  value = "on"
}
```

### Key Points
- **Database Version**: Specify a stable version
- **Tier**: Choose based on your performance needs
- **Backup**: Always enable automatic backups
- **SSL**: Force encrypted connections
- **IAM Flag**: Essential for IAM user authentication
- **Protection**: Enable `deletion_protection` in production

---

## 3. Store Password in Secret Manager

### Objective
Store the password securely and make it accessible to authorized applications.

### Terraform Code

```hcl
# Create the secret
resource "google_secret_manager_secret" "db_password" {
  secret_id = "cloudsql-password"
  
  labels = {
    environment = "production"
    service     = "database"
  }
  
  replication {
    user_managed {
      replicas {
        location = "europe-west1"
      }
      replicas {
        location = "europe-west4"
      }
    }
  }
}

# Secret version with the password
resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# Access policy for the secret
resource "google_secret_manager_secret_iam_member" "db_password_accessor" {
  secret_id = google_secret_manager_secret.db_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_sa.email}"
}
```

### Best Practices
- **Replication**: Configure multi-region replication for high availability
- **Labels**: Use labels to organize your secrets
- **Permissions**: Grant access only to necessary services
- **Rotation**: Plan regular password rotation

---

## 4. Create a Database

### Objective
Create one or more databases in the Cloud SQL instance.

### Terraform Code

```hcl
# Main application database
resource "google_sql_database" "app_database" {
  name     = "my-application"
  instance = google_sql_database_instance.main_instance.name
  charset  = "UTF8"
  collation = "en_US.UTF8"
}

# Test database (optional)
resource "google_sql_database" "test_database" {
  name     = "my-application-test"
  instance = google_sql_database_instance.main_instance.name
  charset  = "UTF8"
  collation = "en_US.UTF8"
}

```

### Considerations
- **Charset and Collation**: Define according to your linguistic needs
- **Dedicated Users**: Create specific users per application
- **Environments**: Separate development, test, and production databases

---

## 5. Configure IAM Users and Permissions

### Objective
Configure IAM authentication to allow users and services to access Cloud SQL.

### Terraform Code

```hcl
# Service Account for the application
resource "google_service_account" "app_sa" {
  account_id   = "cloudsql-app"
  display_name = "Cloud SQL Application Service Account"
  description  = "Service Account for Cloud SQL access"
}

# IAM user for Cloud SQL (only works if IAM auth is enabled)

resource "google_sql_user" "iam_service_account_user" {
  # Note: for Postgres only, GCP requires omitting the ".gserviceaccount.com" suffix
  # from the service account email due to length limits on database usernames.
  name     = trimsuffix(google_service_account.app_sa.email, ".gserviceaccount.com")
  instance = google_sql_database_instance.main.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
  
  # This resource depends on IAM authentication being enabled
  depends_on = [google_sql_database_instance.main_instance]
}

# IAM permissions for Cloud SQL
resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.app_sa.email}"
}

resource "google_project_iam_member" "cloudsql_instance_user" {
  project = var.project_id
  role    = "roles/cloudsql.instanceUser"
  member  = "serviceAccount:${google_service_account.app_sa.email}"
}

# Human IAM user (optional)
resource "google_sql_user" "developer_user" {
  name     = "developer@mycompany.com"
  instance = google_sql_database_instance.main_instance.name
  type     = "CLOUD_IAM_USER"
  
  # This also requires IAM authentication to be enabled
  depends_on = [google_sql_database_instance.main_instance]
}

# Grant IAM permissions to the human user
resource "google_project_iam_member" "developer_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "user:developer@mycompany.com"
}
```

### Essential IAM Roles

| Role | Description | Usage |
|------|-------------|--------|
| `roles/cloudsql.client` | Connect to Cloud SQL instances | Applications |
| `roles/cloudsql.instanceUser` | Access data via IAM | Service Accounts |
| `roles/cloudsql.admin` | Full administration | DevOps/DBA |
| `roles/secretmanager.secretAccessor` | Read secrets | Applications |

### ⚠️ Prerequisites for IAM Users

**Before you can add IAM users to Cloud SQL, you MUST:**

1. **Enable IAM authentication** on the instance using database flags
2. **Wait for the instance to be ready** (use `depends_on`)
3. **Grant appropriate IAM roles** at the project level

**Without the IAM authentication flag, adding IAM users will fail!**

---

## Useful Outputs

```hcl
# Output information
output "database_connection_name" {
  description = "Cloud SQL instance connection name"
  value       = google_sql_database_instance.main.connection_name
}

output "service_account_email" {
  description = "Service Account email"
  value       = google_service_account.app_sa.email
}

output "secret_id" {
  description = "Secret ID containing the password"
  value       = google_secret_manager_secret.db_password.secret_id
  sensitive   = true
}

output "database_name" {
  description = "Database name"
  value       = google_sql_database.app_db.name
}

output "iam_auth_enabled" {
  description = "Confirms IAM authentication is enabled"
  value       = "IAM authentication enabled via database flags"
}
```

---

## Terraform Commands

```bash
# Initialize
terraform init

# Plan
terraform plan -var="project_id=my-gcp-project"

# Apply
terraform apply -var="project_id=my-gcp-project"

```

---

## Security and Best Practices

### ✅ Do
- Use automatically generated passwords
- Enable SSL/TLS for all connections
- Configure automatic backups
- Use Secret Manager for passwords
- **Enable IAM authentication before adding IAM users**
- Apply principle of least privilege
- Enable deletion protection

### ❌ Don't
- Store passwords in plain text
- Use weak passwords
- Expose the instance on the Internet without protection
- Grant overly broad permissions
- Forget to configure backups
- **Try to add IAM users without enabling IAM authentication**

### 🔄 Maintenance
- Plan password rotation
- Monitor access logs
- Regularly update versions
- Audit IAM permissions

---

## Troubleshooting IAM Users

### Common Error: "IAM authentication is not enabled"

**Problem**: Trying to create IAM users without enabling IAM authentication.

**Solution**: Ensure the database flag is set:
```hcl
database_flags {
  name  = "cloudsql.iam_authentication"
  value = "on"
}
```

### Connection Issues

**For applications connecting with IAM authentication:**
1. Ensure the service account has `roles/cloudsql.client`
2. Use the Cloud SQL Auth Proxy or configure private IP
3. The database user name must match the service account email exactly