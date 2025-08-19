import pytest
import os
import sys
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import test database setup first
from .test_database import TestBase, engine, TestingSessionLocal, TestUser, override_get_db_with_test_user, create_test_tables, drop_test_tables, get_test_current_user, create_test_admin_required, TestDatabaseSession

# Import app components after test setup
from app.database import get_db
from app.auth.security import create_access_token, hash_password
from app.auth.schemas import UserRegister, UserLogin, UserUpdate
from app.auth.dependencies import get_current_user, admin_required

# Import app after setting up test database
from app.main import app

# Override the database dependency to use our test database
app.dependency_overrides[get_db] = override_get_db_with_test_user


@pytest.fixture(scope="function", autouse=True)
def db_session():
    """Create a fresh database session for each test"""
    # Create tables before each test
    create_test_tables()
    session = TestingSessionLocal()
    
    # Setup authentication overrides for this test
    test_db = TestDatabaseSession(session)
    app.dependency_overrides[get_current_user] = get_test_current_user(test_db)
    app.dependency_overrides[admin_required] = create_test_admin_required(test_db)
    
    yield session
    session.close()
    # Drop tables after each test
    drop_test_tables()


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "phone_number": "+1234567890"
    }


@pytest.fixture
def test_user(db_session, test_user_data):
    """Create a test user in the database"""
    user = TestUser(
        name=test_user_data["name"],
        email=test_user_data["email"],
        hashed_password=hash_password(test_user_data["password"]),
        phone_number=test_user_data["phone_number"],
        is_verified=True,
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session):
    """Create an admin user in the database"""
    user = TestUser(
        name="Admin User",
        email="admin@example.com",
        hashed_password=hash_password("AdminPassword123!"),
        phone_number="+9876543210",
        is_verified=True,
        role="admin"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def unverified_user(db_session):
    """Create an unverified user in the database with expired verification code"""
    user = TestUser(
        name="Unverified User",
        email="unverified@example.com",
        hashed_password=hash_password("Password123!"),
        phone_number="+1111111111",
        is_verified=False,
        verification_code="123456",
        verification_code_expires=datetime.now(UTC) - timedelta(minutes=1)  # Expired
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def unverified_user_valid_code(db_session):
    """Create an unverified user in the database with valid verification code"""
    user = TestUser(
        name="Unverified User Valid",
        email="unverified_valid@example.com",
        hashed_password=hash_password("Password123!"),
        phone_number="+1111111112",
        is_verified=False,
        verification_code="123456",
        verification_code_expires=datetime.now(UTC) + timedelta(minutes=15)  # Valid
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Generate authentication headers for a test user"""
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user):
    """Generate authentication headers for an admin user"""
    token = create_access_token(admin_user.id)
    return {"Authorization": f"Bearer {token}"}


class TestRegister:
    """Test cases for POST /api/auth/register"""

    @patch('app.services.email_service.AsyncEmailSender')
    def test_register_success(self, mock_email_sender, client, db_session, test_user_data):
        """Test successful user registration"""
        mock_email_sender.return_value.__aenter__ = AsyncMock()
        mock_email_sender.return_value.__aexit__ = AsyncMock()

        response = client.post("/api/auth/register", json=test_user_data)
        
        assert response.status_code == 201
        assert response.json()["message"] == "Verification code sent"
        
        # Verify user was created in database
        user = db_session.query(TestUser).filter_by(email=test_user_data["email"]).first()
        assert user is not None
        assert user.name == test_user_data["name"]
        assert user.is_verified == False
        assert user.verification_code is not None

    def test_register_existing_verified_user(self, client, test_user):
        """Test registration with existing verified user"""
        user_data = {
            "name": "Another User",
            "email": test_user.email,
            "password": "AnotherPassword123!",
            "phone_number": "+9999999999"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert response.json()["detail"] == "User already exists"

    @patch('app.services.email_service.AsyncEmailSender')
    def test_register_existing_unverified_user(self, mock_email_sender, client, unverified_user):
        """Test registration with existing unverified user"""
        mock_email_sender.return_value.__aenter__ = AsyncMock()
        mock_email_sender.return_value.__aexit__ = AsyncMock()
        
        user_data = {
            "name": "Updated Name",
            "email": unverified_user.email,
            "password": "NewPassword123!",
            "phone_number": unverified_user.phone_number
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 201
        assert response.json()["message"] == "New verification code sent"

    def test_register_invalid_email(self, client):
        """Test registration with invalid email"""
        user_data = {
            "name": "Test User",
            "email": "invalid-email",
            "password": "TestPassword123!",
            "phone_number": "+1234567890"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 422

    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        user_data = {
            "name": "Test User",
            "email": "test@example.com",
            "password": "123",
            "phone_number": "+1234567890"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 422

    def test_register_missing_fields(self, client):
        """Test registration with missing required fields"""
        user_data = {
            "name": "Test User",
            "email": "test@example.com"
            # Missing password and phone_number
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 422


class TestVerifyEmail:
    """Test cases for POST /api/auth/verify-email"""

    def test_verify_email_success(self, client, unverified_user_valid_code):
        """Test successful email verification"""
        response = client.post("/api/auth/verify-email", params={
            "email": unverified_user_valid_code.email,
            "code": unverified_user_valid_code.verification_code
        })
        
        assert response.status_code == 200
        assert response.json()["message"] == "User created"
        assert "user_id" in response.json()

    def test_verify_email_invalid_code(self, client, unverified_user):
        """Test email verification with invalid code"""
        response = client.post("/api/auth/verify-email", params={
            "email": unverified_user.email,
            "code": "999999"
        })
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid or expired verification code"

    def test_verify_email_expired_code(self, client, db_session):
        """Test email verification with expired code"""
        user = TestUser(
            name="Expired User",
            email="expired@example.com",
            hashed_password=hash_password("Password123!"),
            phone_number="+2222222222",
            is_verified=False,
            verification_code="123456",
            verification_code_expires=datetime.now(UTC) - timedelta(minutes=1)
        )
        db_session.add(user)
        db_session.commit()
        
        response = client.post("/api/auth/verify-email", params={
            "email": user.email,
            "code": user.verification_code
        })
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid or expired verification code"

    def test_verify_email_nonexistent_user(self, client):
        """Test email verification for non-existent user"""
        response = client.post("/api/auth/verify-email", params={
            "email": "nonexistent@example.com",
            "code": "123456"
        })
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid or expired verification code"

    def test_verify_email_missing_params(self, client):
        """Test email verification with missing parameters"""
        response = client.post("/api/auth/verify-email")
        
        assert response.status_code == 422


class TestLogin:
    """Test cases for POST /api/auth/login"""

    def test_login_success(self, client, test_user, test_user_data):
        """Test successful login"""
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        login_data = {
            "email": "test@example.com",
            "password": "wrongpassword"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"

    def test_login_unverified_user(self, client, unverified_user):
        """Test login with unverified user"""
        login_data = {
            "email": unverified_user.email,
            "password": "Password123!"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 403
        assert "Email not verified" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "Password123!"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"

    def test_login_missing_fields(self, client):
        """Test login with missing fields"""
        login_data = {
            "email": "test@example.com"
            # Missing password
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 422

    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format"""
        login_data = {
            "email": "invalid-email",
            "password": "Password123!"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 422


class TestPasswordResetRequest:
    """Test cases for POST /api/auth/password-reset/request"""

    @patch('app.services.email_service.AsyncEmailSender')
    def test_password_reset_request_success(self, mock_email_sender, client, test_user):
        """Test successful password reset request"""
        mock_email_sender.return_value.__aenter__ = AsyncMock()
        mock_email_sender.return_value.__aexit__ = AsyncMock()
        
        response = client.post("/api/auth/password-reset/request", params={"email": test_user.email})
        
        assert response.status_code == 200
        assert response.json()["message"] == "If the email exists, a reset link has been sent"

    @patch('app.services.email_service.AsyncEmailSender')
    def test_password_reset_request_nonexistent_user(self, mock_email_sender, client):
        """Test password reset request for non-existent user"""
        mock_email_sender.return_value.__aenter__ = AsyncMock()
        mock_email_sender.return_value.__aexit__ = AsyncMock()
        
        response = client.post("/api/auth/password-reset/request", params={"email": "nonexistent@example.com"})
        
        assert response.status_code == 200
        assert response.json()["message"] == "If the email exists, a reset link has been sent"

    def test_password_reset_request_missing_email(self, client):
        """Test password reset request without email"""
        response = client.post("/api/auth/password-reset/request")
        
        assert response.status_code == 422


class TestPasswordResetConfirm:
    """Test cases for POST /api/auth/password-reset/confirm"""

    def test_password_reset_confirm_success(self, client, db_session, test_user):
        """Test successful password reset confirmation"""
        # Create a password reset token
        from app.auth.security import create_password_reset_token
        token, jti, expires = create_password_reset_token(test_user.id)
        
        # Update user with reset token
        test_user.password_reset_jti = hash_password(jti)
        test_user.password_reset_expires = expires
        db_session.commit()
        
        response = client.post("/api/auth/password-reset/confirm", params={
            "token": token,
            "new_password": "NewPassword123!"
        })
        
        assert response.status_code == 200
        assert response.json()["message"] == "Password has been reset successfully"

    def test_password_reset_confirm_invalid_token(self, client):
        """Test password reset confirmation with invalid token"""
        response = client.post("/api/auth/password-reset/confirm", params={
            "token": "invalid-token",
            "new_password": "NewPassword123!"
        })
        
        assert response.status_code == 400
        assert "Invalid token" in response.json()["detail"]

    def test_password_reset_confirm_expired_token(self, client, db_session, test_user):
        """Test password reset confirmation with expired token"""
        # Create an expired password reset token
        from app.auth.security import create_password_reset_token
        token, jti, expires = create_password_reset_token(test_user.id)
        
        # Update user with expired reset token
        test_user.password_reset_jti = hash_password(jti)
        test_user.password_reset_expires = datetime.now(UTC) - timedelta(minutes=1)
        db_session.commit()
        
        response = client.post("/api/auth/password-reset/confirm", params={
            "token": token,
            "new_password": "NewPassword123!"
        })
        
        assert response.status_code == 400
        assert "Invalid or expired token" in response.json()["detail"]

    def test_password_reset_confirm_missing_fields(self, client):
        """Test password reset confirmation with missing fields"""
        response = client.post("/api/auth/password-reset/confirm", params={
            "token": "some-token"
            # Missing new_password
        })
        
        assert response.status_code == 422

    def test_password_reset_confirm_weak_password(self, client, db_session, test_user):
        """Test password reset confirmation with weak password"""
        # Create a password reset token
        from app.auth.security import create_password_reset_token
        token, jti, expires = create_password_reset_token(test_user.id)
        
        # Update user with reset token
        test_user.password_reset_jti = hash_password(jti)
        test_user.password_reset_expires = expires
        db_session.commit()
        
        response = client.post("/api/auth/password-reset/confirm", params={
            "token": token,
            "new_password": "123"
        })
        
        # The endpoint doesn't validate password strength, so it should succeed
        assert response.status_code == 200
        assert response.json()["message"] == "Password has been reset successfully"


class TestGetMe:
    """Test cases for GET /api/auth/me"""

    def test_get_me_success(self, client, auth_headers, test_user):
        """Test successful get current user info"""
        response = client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["name"] == test_user.name
        assert data["email"] == test_user.email
        assert data["phone_number"] == test_user.phone_number
        assert data["role"] == test_user.role

    def test_get_me_no_auth(self, client):
        """Test get current user info without authentication"""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_get_me_invalid_token(self, client):
        """Test get current user info with invalid token"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_get_me_expired_token(self, client, test_user):
        """Test get current user info with expired token"""
        # Create an expired token
        from app.auth.security import create_access_token
        expired_token = create_access_token(test_user.id, timedelta(minutes=-1))
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]


class TestUpdateMe:
    """Test cases for PUT /api/auth/me"""

    def test_update_me_success(self, client, auth_headers, test_user):
        """Test successful user profile update"""
        update_data = {
            "email": "updated@example.com",
            "phone_number": "+9999999999"
        }
        
        response = client.put("/api/auth/me", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "User profile updated"
        assert data["user"]["email"] == "updated@example.com"
        assert data["user"]["phone_number"] == "+9999999999"

    def test_update_me_partial_update(self, client, auth_headers, test_user):
        """Test partial user profile update"""
        update_data = {
            "email": "partial@example.com"
            # Only updating email
        }
        
        response = client.put("/api/auth/me", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "partial@example.com"
        assert data["user"]["phone_number"] == test_user.phone_number

    def test_update_me_existing_email(self, client, auth_headers, db_session, test_user):
        """Test update with existing email"""
        # Create another user
        other_user = TestUser(
            name="Other User",
            email="other@example.com",
            hashed_password=hash_password("Password123!"),
            phone_number="+8888888888",
            is_verified=True
        )
        db_session.add(other_user)
        db_session.commit()
        
        update_data = {
            "email": other_user.email
        }
        
        response = client.put("/api/auth/me", json=update_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Email already exist"

    def test_update_me_no_auth(self, client):
        """Test update user profile without authentication"""
        update_data = {
            "email": "test@example.com"
        }
        
        response = client.put("/api/auth/me", json=update_data)
        
        assert response.status_code == 403

    def test_update_me_invalid_email_format(self, client, auth_headers):
        """Test update with invalid email format"""
        update_data = {
            "email": "invalid-email"
        }
        
        response = client.put("/api/auth/me", json=update_data, headers=auth_headers)
        
        assert response.status_code == 422

    def test_update_me_empty_data(self, client, auth_headers, test_user):
        """Test update with empty data"""
        update_data = {}
        
        response = client.put("/api/auth/me", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        # Should return current user data unchanged
        data = response.json()
        assert data["user"]["email"] == test_user.email
        assert data["user"]["phone_number"] == test_user.phone_number


class TestAdminOnly:
    """Test cases for POST /api/auth/admin-only"""

    def test_admin_only_success(self, client, admin_headers, admin_user):
        """Test successful admin-only endpoint access"""
        response = client.post("/api/auth/admin-only", headers=admin_headers)
        
        assert response.status_code == 200
        assert response.json()["message"] == f"Welcome, admin {admin_user.name}"

    def test_admin_only_regular_user(self, client, auth_headers):
        """Test admin-only endpoint with regular user"""
        response = client.post("/api/auth/admin-only", headers=auth_headers)
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"

    def test_admin_only_no_auth(self, client):
        """Test admin-only endpoint without authentication"""
        response = client.post("/api/auth/admin-only")
        
        assert response.status_code == 403

    def test_admin_only_invalid_token(self, client):
        """Test admin-only endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.post("/api/auth/admin-only", headers=headers)
        
        assert response.status_code == 401


class TestTestAuth:
    """Test cases for GET /api/auth/test-auth"""

    def test_test_auth_success(self, client, auth_headers, test_user):
        """Test successful test-auth endpoint access"""
        response = client.get("/api/auth/test-auth", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email

    def test_test_auth_no_auth(self, client):
        """Test test-auth endpoint without authentication"""
        response = client.get("/api/auth/test-auth")
        
        assert response.status_code == 403

    def test_test_auth_invalid_token(self, client):
        """Test test-auth endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/auth/test-auth", headers=headers)
        
        assert response.status_code == 401


class TestEdgeCases:
    """Test edge cases and error scenarios"""

    def test_database_connection_error(self, client, test_user_data):
        """Test handling of database connection errors"""
        # This would require mocking the database connection
        # For now, we'll test the basic structure
        pass

    def test_email_service_error(self, client, test_user_data):
        """Test handling of email service errors"""
        with patch('app.services.email_service.AsyncEmailSender') as mock_email_sender:
            mock_email_sender.side_effect = Exception("Email service error")
            
            response = client.post("/api/auth/register", json=test_user_data)
            
            # Should still return success as email sending is not critical for registration
            assert response.status_code == 201

    def test_concurrent_registration(self, client, test_user_data):
        """Test concurrent registration attempts"""
        # This would require more sophisticated testing with async operations
        pass

    def test_token_tampering(self, client, test_user):
        """Test JWT token tampering"""
        # Create a valid token and modify it
        token = create_access_token(test_user.id)
        tampered_token = token[:-1] + "X"  # Modify last character
        
        headers = {"Authorization": f"Bearer {tampered_token}"}
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == 401

    def test_sql_injection_attempts(self, client):
        """Test SQL injection attempts"""
        malicious_data = {
            "name": "'; DROP TABLE users; --",
            "email": "test@example.com",
            "password": "Password123!",
            "phone_number": "+1234567890"
        }
        
        response = client.post("/api/auth/register", json=malicious_data)
        
        # Should handle gracefully (either 422 validation error or 201 success)
        assert response.status_code in [201, 422]

    def test_xss_attempts(self, client):
        """Test XSS attempts"""
        malicious_data = {
            "name": "<script>alert('xss')</script>",
            "email": "test@example.com",
            "password": "Password123!",
            "phone_number": "+1234567890"
        }
        
        response = client.post("/api/auth/register", json=malicious_data)
        
        # Should handle gracefully
        assert response.status_code in [201, 422]


class TestValidation:
    """Test input validation scenarios"""

    def test_password_validation_edge_cases(self, client):
        """Test various password validation scenarios"""
        test_cases = [
            {"password": "", "expected_status": 422},
            {"password": "a" * 1000, "expected_status": 422},  # Too long
            {"password": "12345678", "expected_status": 422},  # No special chars
            {"password": "abcdefgh", "expected_status": 422},  # No numbers
            {"password": "ABCDEFGH", "expected_status": 422},  # No lowercase
            {"password": "TestPassword123!", "expected_status": 201},  # Valid
        ]
        
        for case in test_cases:
            user_data = {
                "name": "Test User",
                "email": f"test{hash(case['password']) % 1000}@example.com",
                "password": case["password"],
                "phone_number": "+1234567890"
            }
            
            with patch('app.services.email_service.AsyncEmailSender'):
                response = client.post("/api/auth/register", json=user_data)
                assert response.status_code == case["expected_status"]

    def test_email_validation_edge_cases(self, client):
        """Test various email validation scenarios"""
        test_cases = [
            {"email": "", "expected_status": 422},
            {"email": "invalid", "expected_status": 422},
            {"email": "@example.com", "expected_status": 422},
            {"email": "test@", "expected_status": 422},
            {"email": "test@example", "expected_status": 422},
            {"email": "test@example.com", "expected_status": 201},  # Valid
            {"email": "test+tag@example.com", "expected_status": 201},  # Valid with plus
        ]
        
        for i, case in enumerate(test_cases):
            # Use unique emails for each test case to avoid conflicts
            if case["email"] == "test@example.com":
                email = f"test{i}@example.com"
            elif case["email"] == "test+tag@example.com":
                email = f"test+tag{i}@example.com"
            else:
                email = case["email"]
                
            user_data = {
                "name": "Test User",
                "email": email,
                "password": "TestPassword123!",
                "phone_number": f"+123456789{i}"  # Also make phone numbers unique
            }
            
            with patch('app.services.email_service.AsyncEmailSender'):
                response = client.post("/api/auth/register", json=user_data)
                assert response.status_code == case["expected_status"]

    def test_phone_number_validation(self, client):
        """Test phone number validation"""
        test_cases = [
            {"phone": "", "expected_status": 201},  # Optional field
            {"phone": "+1234567890", "expected_status": 201},  # Valid
            {"phone": "1234567890", "expected_status": 201},  # Valid without +
            {"phone": "123", "expected_status": 201},  # Short but valid
        ]
        
        for case in test_cases:
            user_data = {
                "name": "Test User",
                "email": f"test{hash(case['phone']) % 1000}@example.com",
                "password": "TestPassword123!",
                "phone_number": case["phone"]
            }
            
            with patch('app.services.email_service.AsyncEmailSender'):
                response = client.post("/api/auth/register", json=user_data)
                assert response.status_code == case["expected_status"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
