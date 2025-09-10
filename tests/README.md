# Test Suite Documentation

## 🧪 Test Overview

This directory contains comprehensive tests for the Cloud SQL PostgreSQL Manager application, including unit tests, integration tests, and test utilities.

**Current Status: ✅ 67 tests passing (100% success rate)**

## 📁 Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                # Pytest configuration and shared fixtures
├── pytest.ini                # Pytest settings
├── requirements-test.txt      # Test dependencies
├── README.md                  # This file
├── unit/                      # Unit tests
│   ├── __init__.py
│   ├── test_database_validator.py
│   └── test_schema_manager.py
├── integration/               # Integration tests
│   ├── __init__.py
│   ├── test_health_endpoints.py
│   ├── test_schema_endpoints.py
│   ├── test_database_endpoints.py
│   └── test_role_endpoints.py
├── fixtures/                  # Test data fixtures
└── utils/                     # Test utilities
```

## 🚀 Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install -r tests/requirements-test.txt
```

### Run All Tests

```bash
python -m pytest tests/ -v --tb=short
```

**Current Results:**
```
===================================== 67 passed, 34 warnings in 31.59s =====================================
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Tests with coverage
pytest tests/ -v --cov=fastapi.app --cov-report=html
```

### Run Tests with Markers

```bash
# Run only unit tests
pytest -m unit -v

# Run only integration tests
pytest -m integration -v

# Run slow tests
pytest -m slow -v
```

## 📋 Test Categories

### Unit Tests (`tests/unit/`) - 25 tests

Test individual components and services in isolation:

- **`test_database_validator.py`**: Tests for `DatabaseValidator` service (15 tests)
  - Role existence validation
  - Schema/database name validation with PostgreSQL rules
  - IAM user identification
  - Service account normalization
  - Error handling for invalid inputs

- **`test_schema_manager.py`**: Tests for `SchemaManager` service (10 tests)
  - Schema creation with owner validation
  - Schema listing and table listing
  - Owner change operations
  - Connection error handling
  - Context manager protocol support

**Features:**
- Mocked dependencies with proper context manager protocol
- Fast execution (< 1 second per test)
- Isolated testing with realistic PostgreSQL identifiers
- Comprehensive coverage including edge cases

### Integration Tests (`tests/integration/`) - 42 tests

Test API endpoints and service interactions:

- **`test_health_endpoints.py`**: Health check endpoint tests (5 tests)
  - Service health validation
  - Response structure verification
  - Content type validation
  - Query parameter handling

- **`test_schema_endpoints.py`**: Schema management endpoint tests (8 tests)
  - Schema creation with validation
  - Error handling for invalid schema names
  - Service error scenarios
  - Content type and method validation

- **`test_database_endpoints.py`**: Database management endpoint tests (11 tests)
  - Schema listing and table listing
  - Database health checks
  - PostgreSQL inheritance operations
  - Validation error handling
  - Service error scenarios

- **`test_role_endpoints.py`**: Role management endpoint tests (8 tests)
  - Role initialization and assignment
  - Role revocation and listing
  - User listing with roles
  - Role status checking
  - Validation and service error handling

**Features:**
- Real HTTP requests with FastAPI test client
- End-to-end testing with mocked external services
- Response validation with Pydantic models
- Comprehensive error handling scenarios
- Realistic test data with PostgreSQL-compliant identifiers

## 🔧 Test Configuration

### Pytest Configuration (`pytest.ini`)

- **Test discovery**: Automatically finds test files
- **Output options**: Verbose output with short tracebacks
- **Markers**: Categorize tests (unit, integration, slow, etc.)
- **Warnings**: Filter out deprecation warnings
- **Timeout**: 300 seconds maximum per test

### Fixtures (`conftest.py`)

Common test fixtures available to all tests:

- **`client`**: FastAPI test client
- **`mock_connection`**: Mock database connection
- **`mock_cursor`**: Mock database cursor
- **`mock_*_manager`**: Mock service managers
- **`sample_*_config`**: Sample configuration data
- **`test_*`**: Test data fixtures

## 📊 Test Coverage

The test suite achieves comprehensive coverage with **67 tests passing**:

- **Unit Tests**: 25 tests covering all service methods and validation logic
- **Integration Tests**: 42 tests covering all API endpoints and workflows
- **Error Handling**: All error scenarios tested (validation, service, authentication, business logic)
- **Edge Cases**: Boundary conditions, invalid inputs, and PostgreSQL identifier validation
- **Pydantic V2**: Full validation with `@field_validator` and empty field prevention
- **Mocking**: Complete external dependency mocking (database, Google Cloud, Firestore)

### Coverage Reports

Generate coverage reports:

```bash
# HTML report
pytest tests/ --cov=fastapi.app --cov-report=html
open htmlcov/index.html

# Terminal report
pytest tests/ --cov=fastapi.app --cov-report=term-missing

# XML report (for CI/CD)
pytest tests/ --cov=fastapi.app --cov-report=xml
```

## 🏷️ Test Markers

Use markers to categorize and filter tests:

```python
@pytest.mark.unit
def test_database_validator():
    pass

@pytest.mark.integration
def test_api_endpoint():
    pass

@pytest.mark.slow
def test_performance():
    pass

@pytest.mark.database
def test_real_database():
    pass
```

## 🔍 Test Data

### Sample Data Fixtures

The test suite includes realistic sample data with PostgreSQL compliance:

- **Project configurations**: Valid GCP project settings with `test_database` (not `test-database`)
- **IAM users**: Service account examples (`user@project.iam.gserviceaccount.com`)
- **Schema data**: Database schema information (`test_schema`, `app_schema`)
- **Role data**: PostgreSQL role definitions with proper naming conventions
- **Table data**: Database table metadata with realistic structures

### Mock Data

All external dependencies are mocked with proper protocols:

- **Database connections**: Mocked with context manager protocol (`__enter__`, `__exit__`)
- **Google Cloud services**: Mocked API responses (Secret Manager, IAM)
- **Firestore**: Mocked document operations with realistic data structures
- **IAM**: Mocked user validation and service account normalization
- **Service managers**: Complete mocking of `SchemaManager`, `UserManager`, `RolePermissionManager`

## 🚨 Error Testing

The test suite includes comprehensive error testing covering all scenarios:

- **Validation errors**: Invalid input data, empty fields, wrong types
- **Service errors**: Database connection failures, SQL execution errors
- **Authentication errors**: IAM permission issues, invalid service accounts
- **Network errors**: Connection timeouts, API failures
- **Business logic errors**: Domain-specific failures (schema not found, role not found)
- **Pydantic V2 errors**: Field validation failures with proper error messages

## 📈 Performance Testing

Performance tests are included for:

- **Response times**: API endpoint performance
- **Database operations**: Query execution times
- **Memory usage**: Service memory consumption
- **Concurrent requests**: Load testing

Run performance tests:

```bash
pytest tests/ --benchmark-only
```

## 🔄 Continuous Integration

The test suite is integrated with GitHub Actions:

- **Automated testing**: Runs on every push and PR
- **Multiple Python versions**: Tests on Python 3.11 and 3.12
- **Code quality checks**: Linting, formatting, type checking
- **Security scanning**: Safety and Bandit checks
- **Coverage reporting**: Codecov integration

## 📝 Writing New Tests

### Unit Test Template

```python
import pytest
from unittest.mock import Mock, patch
from fastapi.app.services.your_service import YourService

class TestYourService:
    """Test cases for YourService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = YourService()
    
    def test_method_success(self, mock_dependency):
        """Test successful method execution."""
        # Arrange
        mock_dependency.return_value = expected_result
        
        # Act
        result = self.service.method()
        
        # Assert
        assert result["success"] is True
        assert result["data"] == expected_data
```

### Integration Test Template

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

class TestYourEndpoints:
    """Test cases for your endpoints."""
    
    def test_endpoint_success(self, client, sample_data):
        """Test successful endpoint execution."""
        # Arrange
        request_data = sample_data
        
        with patch('fastapi.app.routers.your_router.your_service') as mock_service:
            mock_service.method.return_value = {
                "success": True,
                "data": expected_data
            }
            
            # Act
            response = client.post("/your/endpoint", json=request_data)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
```

## 🐛 Debugging Tests

### Debug Mode

Run tests in debug mode:

```bash
pytest tests/ -v -s --pdb
```

### Verbose Output

Get detailed test output:

```bash
pytest tests/ -v -vv
```

### Test Specific Function

Run a specific test function:

```bash
pytest tests/unit/test_database_validator.py::TestDatabaseValidator::test_role_exists_true -v
```

## 📚 Best Practices

1. **Test Isolation**: Each test should be independent
2. **Mock External Dependencies**: Don't rely on external services
3. **Realistic Data**: Use realistic test data
4. **Error Scenarios**: Test both success and failure cases
5. **Clear Assertions**: Use descriptive assertion messages
6. **Documentation**: Document complex test scenarios
7. **Performance**: Keep tests fast and efficient
8. **Maintenance**: Keep tests up to date with code changes