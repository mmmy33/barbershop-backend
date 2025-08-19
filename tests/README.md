# Authentication Tests

This directory contains comprehensive tests for all FastAPI authentication endpoints in the barbershop backend.

## Test Coverage

The tests cover all authentication endpoints:

- **POST /api/auth/register** - User registration
- **POST /api/auth/verify-email** - Email verification
- **POST /api/auth/login** - User login
- **POST /api/auth/password-reset/request** - Password reset request
- **POST /api/auth/password-reset/confirm** - Password reset confirmation
- **GET /api/auth/me** - Get current user info
- **PUT /api/auth/me** - Update user profile
- **POST /api/auth/admin-only** - Admin-only endpoint
- **GET /api/auth/test-auth** - Test authentication endpoint

## Test Categories

### 1. Success Cases
- Valid registration with email verification
- Successful login with valid credentials
- Email verification with valid code
- Password reset flow
- User profile updates
- Admin access control

### 2. Error Cases
- Invalid credentials
- Unverified user login attempts
- Expired verification codes
- Invalid tokens
- Missing required fields
- Duplicate email addresses

### 3. Validation Testing
- Email format validation
- Password strength validation
- Phone number validation
- Required field validation

### 4. Authentication/Authorization
- JWT token validation
- Admin role requirements
- Unauthorized access attempts
- Token expiration handling

### 5. Edge Cases
- SQL injection attempts
- XSS attempts
- Token tampering
- Email service errors
- Database connection issues

## Running Tests

### Prerequisites
```bash
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Run only authentication tests
pytest tests/test_auth.py -v

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# Run tests excluding slow tests
pytest tests/ -m "not slow" -v

# Run only unit tests
pytest tests/ -m "unit" -v

# Run only integration tests
pytest tests/ -m "integration" -v
```

### Run Specific Test Classes
```bash
# Run only registration tests
pytest tests/test_auth.py::TestRegister -v

# Run only login tests
pytest tests/test_auth.py::TestLogin -v

# Run only admin tests
pytest tests/test_auth.py::TestAdminOnly -v
```

### Run Specific Test Methods
```bash
# Run specific test method
pytest tests/test_auth.py::TestRegister::test_register_success -v

# Run tests matching a pattern
pytest tests/test_auth.py -k "success" -v
```

## Test Structure

### Fixtures
- `db_session`: Fresh database session for each test
- `client`: FastAPI TestClient instance
- `test_user_data`: Sample user data
- `test_user`: Verified user in database
- `admin_user`: Admin user in database
- `unverified_user`: Unverified user in database
- `auth_headers`: Authentication headers for regular user
- `admin_headers`: Authentication headers for admin user

### Test Classes
Each endpoint has its own test class with multiple test methods covering:
- Success scenarios
- Error scenarios
- Edge cases
- Validation testing

### Mocking
- Email service is mocked to prevent actual emails during testing
- Environment variables are mocked for consistent test environment
- Database operations use SQLite for testing

## Test Database

Tests use SQLite in-memory database for isolation and speed:
- Each test gets a fresh database
- No data persists between tests
- No external database dependencies

## Status Codes Tested

- **200**: Successful operations
- **201**: Resource created (registration)
- **400**: Bad request (validation errors, business logic errors)
- **401**: Unauthorized (missing/invalid authentication)
- **403**: Forbidden (insufficient permissions)
- **404**: Not found
- **422**: Validation error (request body/parameters)
- **500**: Internal server error

## Security Testing

The tests include security-focused scenarios:
- JWT token validation
- Password strength requirements
- SQL injection prevention
- XSS prevention
- Authorization checks
- Token expiration handling

## Coverage Report

After running tests with coverage, you can view the HTML report:
```bash
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html in your browser
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:
- No external dependencies
- Fast execution
- Comprehensive coverage
- Clear pass/fail results

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `src` directory is in Python path
2. **Database Errors**: Tests use SQLite, ensure no conflicts with production DB
3. **Email Service Errors**: Email service is mocked, should not cause issues
4. **Environment Variables**: All required env vars are mocked in tests

### Debug Mode
```bash
# Run tests with more verbose output
pytest tests/ -v -s --tb=long

# Run single test with debugger
pytest tests/test_auth.py::TestLogin::test_login_success -v -s --pdb
```

## Adding New Tests

When adding new authentication endpoints:

1. Create a new test class following the existing pattern
2. Include success, error, and edge case tests
3. Add appropriate fixtures if needed
4. Update this README with new endpoint coverage
5. Ensure proper mocking of external dependencies
