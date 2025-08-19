import pytest
import os
import sys
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables for testing"""
    with patch.dict(os.environ, {
        "SECRET_KEY": "test-secret-key-for-testing-only",
        "DATABASE_URL": "sqlite:///:memory:",
        "MAIL_USERNAME": "test@example.com",
        "MAIL_PASSWORD": "test-password",
        "MAIL_FROM": "test@example.com",
        "MAIL_PORT": "587",
        "MAIL_SERVER": "smtp.gmail.com",
        "MAIL_TLS": "True",
        "MAIL_SSL": "False"
    }):
        yield


@pytest.fixture(autouse=True)
def mock_email_service():
    """Mock email service to prevent actual emails during testing"""
    from unittest.mock import AsyncMock
    with patch('app.services.email_service.AsyncEmailSender') as mock:
        mock.return_value.__aenter__ = AsyncMock()
        mock.return_value.__aexit__ = AsyncMock()
        yield mock


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """Clean up test database file after all tests"""
    yield
    # Remove test database file after all tests
    test_db_path = "./test.db"
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except OSError:
            pass  # Ignore errors if file is already removed


# Test data fixtures
@pytest.fixture
def valid_user_data():
    """Valid user registration data"""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "phone_number": "+1234567890"
    }


@pytest.fixture
def valid_login_data():
    """Valid login data"""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }


@pytest.fixture
def valid_user_update_data():
    """Valid user update data"""
    return {
        "email": "updated@example.com",
        "phone_number": "+9999999999"
    }


# Error response fixtures
@pytest.fixture
def error_responses():
    """Common error response patterns"""
    return {
        "validation_error": 422,
        "not_found": 404,
        "unauthorized": 401,
        "forbidden": 403,
        "bad_request": 400,
        "internal_server_error": 500
    }


# Test markers
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "auth: marks tests as authentication tests"
    )
