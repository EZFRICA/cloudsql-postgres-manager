# Components Documentation

## ⚠️ Important Notice

**The components in the `components/` directory are available for users but are NOT integrated in the functional codebase.**

These components were developed as reusable utilities that users can utilize, but they are not currently integrated into the main application's functional code. They are kept as available features for user implementation.

## 🧩 Component System Architecture

The component system provides reusable business logic components that can be shared across different services and routers. **Note: These components are available for users but not integrated in the functional codebase.**

## 📋 Component Overview

| Component | Purpose | Usage Status |
|-----------|---------|--------------|
| `ValidationHelper` | Input validation and sanitization | ⚠️ Available but not integrated |
| `ErrorHandler` | Centralized error handling | ⚠️ Available but not integrated |
| `ServiceOperations` | Common service operation patterns | ⚠️ Available but not integrated |
| `DatabaseOperations` | Database-specific operations | ⚠️ Available but not integrated |
| `LoggingHelper` | Structured logging utilities | ⚠️ Available but not integrated |
| `BaseResponse` | Standardized response formats | ⚠️ Available but not integrated |

## ✅ ValidationHelper

**Purpose**: Centralized input validation and data sanitization.  
**Status**: ⚠️ **Available for users but not integrated in functional code**

### Key Features
- Request validation
- Data sanitization
- Type checking
- Business rule validation

### Methods
```python
def validate_request_data(data, schema)
def sanitize_input(input_string)
def validate_email(email)
def validate_schema_name(schema_name)
def validate_database_name(database_name)
```

### Usage Example
```python
from app.components.validation_helpers import ValidationHelper

# Validate request data
validation_result = ValidationHelper.validate_request_data(
    request_data, 
    SchemaCreateRequest
)

if not validation_result["valid"]:
    return ErrorResponse.validation_error(validation_result["errors"])
```

## 🚨 ErrorHandler

**Purpose**: Centralized error handling and response formatting.  
**Status**: ⚠️ **Available for users but not integrated in functional code**

### Key Features
- Consistent error responses
- Error categorization
- Security-conscious error messages
- Logging integration

### Error Types
- **Validation Errors**: Input validation failures
- **Authentication Errors**: IAM/permission issues
- **Database Errors**: Connection/query failures
- **Business Logic Errors**: Domain-specific failures
- **System Errors**: Unexpected failures

### Methods
```python
def handle_validation_error(errors)
def handle_database_error(error)
def handle_authentication_error(error)
def handle_business_logic_error(error)
def handle_system_error(error)
```

### Usage Example
```python
from app.components.error_handlers import ErrorHandler

try:
    result = service.operation()
except ValidationError as e:
    return ErrorHandler.handle_validation_error(e.errors)
except DatabaseError as e:
    return ErrorHandler.handle_database_error(e)
```

## ⚙️ ServiceOperations

**Purpose**: Common service operation patterns and utilities.  
**Status**: ⚠️ **Available for users but not integrated in functional code**

### Key Features
- Operation execution patterns
- Retry logic
- Timeout handling
- Result formatting

### Methods
```python
def execute_with_retry(operation, max_retries=3)
def execute_with_timeout(operation, timeout=30)
def format_service_response(success, data, message)
def handle_service_exception(exception)
```

### Usage Example
```python
from app.components.service_operations import ServiceOperations

# Execute operation with retry
result = ServiceOperations.execute_with_retry(
    lambda: database_operation(),
    max_retries=3
)

# Format response
response = ServiceOperations.format_service_response(
    success=True,
    data=result,
    message="Operation completed successfully"
)
```

## 🗄️ DatabaseOperations

**Purpose**: Database-specific operations and utilities.  
**Status**: ⚠️ **Available for users but not integrated in functional code**

### Key Features
- SQL query execution
- Transaction management
- Connection handling
- Query optimization

### Methods
```python
def execute_query(connection, query, params=None)
def execute_transaction(connection, operations)
def get_connection_stats(connection)
def optimize_query(query)
```

### Usage Example
```python
from app.components.database_operations import DatabaseOperations

# Execute query with parameters
result = DatabaseOperations.execute_query(
    connection,
    "SELECT * FROM schemas WHERE name = %s",
    (schema_name,)
)

# Execute transaction
DatabaseOperations.execute_transaction(connection, [
    "CREATE SCHEMA test_schema",
    "GRANT USAGE ON SCHEMA test_schema TO test_user"
])
```

## 📝 LoggingHelper

**Purpose**: Structured logging utilities and formatting.  
**Status**: ⚠️ **Available for users but not integrated in functional code**

### Key Features
- Structured JSON logging
- Correlation ID tracking
- Performance metrics
- Security event logging

### Methods
```python
def log_request_start(request_id, endpoint, user)
def log_request_end(request_id, duration, status)
def log_database_operation(operation, duration, success)
def log_security_event(event_type, details)
def log_performance_metric(metric_name, value)
```

### Usage Example
```python
from app.components.logging_helpers import LoggingHelper

# Log request start
LoggingHelper.log_request_start(
    request_id="req-123",
    endpoint="/schemas/create",
    user="service@project.iam"
)

# Log performance metric
LoggingHelper.log_performance_metric(
    "schema_creation_time",
    1.23
)
```

## 📤 BaseResponse

**Purpose**: Standardized response formats for all endpoints.  
**Status**: ⚠️ **Available for users but not integrated in functional code**

### Response Types
- **SuccessResponse**: Successful operations
- **ErrorResponse**: Error conditions
- **ValidationResponse**: Validation results
- **HealthResponse**: Health check results

### Methods
```python
def success(data, message, execution_time)
def error(error_type, message, details)
def validation_error(errors)
def health_check(status, metrics)
```

### Usage Example
```python
from app.components.base_responses import SuccessResponse, ErrorResponse

# Success response
return SuccessResponse(
    data={"schema_name": "test_schema"},
    message="Schema created successfully",
    execution_time=1.23
)

# Error response
return ErrorResponse(
    error_type="validation_error",
    message="Invalid schema name",
    details={"field": "schema_name", "error": "Must be alphanumeric"}
)
```

## 🔄 Component Integration

**Note**: This section describes the theoretical integration of components, but they are not used in the current application.

### 1. Request Processing Flow (Theoretical)
```
Router → ValidationHelper → Service → DatabaseOperations
  ↓
ErrorHandler ← LoggingHelper
```

### 2. Error Handling Flow (Theoretical)
```
Exception → ErrorHandler → LoggingHelper → BaseResponse
```

### 3. Service Operation Flow (Theoretical)
```
ServiceOperations → DatabaseOperations → LoggingHelper
```

## 🧪 Testing Components

### Unit Testing
Each component can be tested independently:

```python
def test_validation_helper():
    # Test validation logic
    result = ValidationHelper.validate_schema_name("test_schema")
    assert result["valid"] == True

def test_error_handler():
    # Test error handling
    response = ErrorHandler.handle_validation_error(["Invalid input"])
    assert response["error_type"] == "validation_error"
```

### Integration Testing
Components are tested together:

```python
def test_request_processing():
    # Test full request flow
    request_data = {"schema_name": "test"}
    validation = ValidationHelper.validate_request_data(request_data)
    if not validation["valid"]:
        return ErrorHandler.handle_validation_error(validation["errors"])
```

## 📊 Component Metrics

### ValidationHelper Metrics
- Validation success rate
- Average validation time
- Validation error types

### ErrorHandler Metrics
- Error handling frequency
- Error type distribution
- Response time

### ServiceOperations Metrics
- Operation success rate
- Retry attempts
- Timeout occurrences

### DatabaseOperations Metrics
- Query execution time
- Transaction success rate
- Connection utilization

## 🔧 Configuration

### Component Configuration
Components can be configured through environment variables:

```bash
# Validation settings
MAX_SCHEMA_NAME_LENGTH=63
ALLOWED_SCHEMA_CHARS=alphanumeric_underscore

# Error handling
INCLUDE_STACK_TRACES=false
SANITIZE_ERROR_MESSAGES=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
ENABLE_CORRELATION_IDS=true
```

### Component Dependencies
Components are designed to be loosely coupled:

```python
# Component initialization
validation_helper = ValidationHelper()
error_handler = ErrorHandler()
service_operations = ServiceOperations()
database_operations = DatabaseOperations()
logging_helper = LoggingHelper()
```

## 🚀 Best Practices

**Note**: These best practices are theoretical since the components are not used in the current application.

### 1. **Component Usage (Theoretical)**
- Use components consistently across services
- Follow the established patterns
- Handle errors appropriately

### 2. **Error Handling (Theoretical)**
- Always use ErrorHandler for error responses
- Log errors with appropriate context
- Sanitize error messages for security

### 3. **Validation (Theoretical)**
- Validate all inputs using ValidationHelper
- Use appropriate validation schemas
- Provide clear validation error messages

### 4. **Logging (Theoretical)**
- Use LoggingHelper for structured logging
- Include correlation IDs for request tracking
- Log performance metrics consistently