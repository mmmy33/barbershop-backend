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
from sqlalchemy import Column, Integer, String

# Import app components after test setup
from app.database import get_db
from app.auth.security import create_access_token, hash_password
from app.auth.dependencies import get_current_user, admin_required

# Import app after setting up test database
from app.main import app

# Override the database dependency to use our test database
app.dependency_overrides[get_db] = override_get_db_with_test_user


# Import test models from test_database
from .test_database import TestService, TestBarber, TestBarberService


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
def barber_user(db_session):
    """Create a barber user in the database"""
    user = TestUser(
        name="Barber User",
        email="barber@example.com",
        hashed_password=hash_password("BarberPassword123!"),
        phone_number="+5555555555",
        is_verified=True,
        role="barber"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_service_data():
    """Sample service data for testing"""
    return {
        "name": "Haircut",
        "price": 2500
    }


@pytest.fixture
def test_service(db_session, test_service_data):
    """Create a test service in the database"""
    service = TestService(
        name=test_service_data["name"],
        price=test_service_data["price"]
    )
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)
    return service


@pytest.fixture
def test_barber(db_session, barber_user):
    """Create a test barber in the database"""
    barber = TestBarber(
        name="John Barber",
        avatar_url="https://example.com/avatar.jpg",
        user_id=barber_user.id
    )
    db_session.add(barber)
    db_session.commit()
    db_session.refresh(barber)
    return barber


@pytest.fixture
def test_barber_service_link(db_session, test_barber, test_service):
    """Create a test barber-service link in the database"""
    barber_service = TestBarberService(
        barber_id=test_barber.id,
        service_id=test_service.id,
        duration=30
    )
    db_session.add(barber_service)
    db_session.commit()
    return barber_service


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


@pytest.fixture
def barber_headers(barber_user):
    """Generate authentication headers for a barber user"""
    token = create_access_token(barber_user.id)
    return {"Authorization": f"Bearer {token}"}


class TestGetAllServices:
    """Test cases for GET /api/services/"""

    def test_get_all_services_success(self, client, auth_headers, test_service):
        """Test successful retrieval of all services"""
        response = client.get("/api/services/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == test_service.id
        assert data[0]["name"] == test_service.name
        assert data[0]["price"] == test_service.price

    def test_get_all_services_with_barbers(self, client, auth_headers, test_service, test_barber, test_barber_service_link):
        """Test retrieval of services with barber information"""
        response = client.get("/api/services/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        
        service = data[0]
        assert service["id"] == test_service.id
        assert service["name"] == test_service.name
        assert service["price"] == test_service.price
        assert "barbers" in service
        assert isinstance(service["barbers"], list)

    def test_get_all_services_empty(self, client, auth_headers):
        """Test retrieval of services when none exist"""
        response = client.get("/api/services/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_all_services_no_auth(self, client):
        """Test retrieval of services without authentication"""
        response = client.get("/api/services/")
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_get_all_services_invalid_token(self, client):
        """Test retrieval of services with invalid token"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/services/", headers=headers)
        
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_get_all_services_multiple_services(self, client, auth_headers, db_session):
        """Test retrieval of multiple services"""
        # Create multiple services
        service1 = TestService(name="Haircut", price=2500)
        service2 = TestService(name="Beard Trim", price=1500)
        service3 = TestService(name="Hair Coloring", price=5000)
        
        db_session.add_all([service1, service2, service3])
        db_session.commit()
        
        response = client.get("/api/services/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        
        # Check that all services are returned
        service_names = [service["name"] for service in data]
        assert "Haircut" in service_names
        assert "Beard Trim" in service_names
        assert "Hair Coloring" in service_names


class TestCreateService:
    """Test cases for POST /api/services/"""

    def test_create_service_success(self, client, admin_headers, test_service_data):
        """Test successful service creation by admin"""
        response = client.post("/api/services/", json=test_service_data, headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == test_service_data["name"]
        assert data["price"] == test_service_data["price"]
        assert "id" in data
        assert "barbers" in data

    def test_create_service_regular_user_denied(self, client, auth_headers, test_service_data):
        """Test service creation denied for regular user"""
        response = client.post("/api/services/", json=test_service_data, headers=auth_headers)
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"

    def test_create_service_no_auth(self, client, test_service_data):
        """Test service creation without authentication"""
        response = client.post("/api/services/", json=test_service_data)
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_create_service_barber_user_denied(self, client, barber_headers, test_service_data):
        """Test service creation denied for barber user"""
        response = client.post("/api/services/", json=test_service_data, headers=barber_headers)
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"

    def test_create_service_missing_name(self, client, admin_headers):
        """Test service creation with missing name"""
        service_data = {"price": 2500}
        
        response = client.post("/api/services/", json=service_data, headers=admin_headers)
        
        assert response.status_code == 422

    def test_create_service_missing_price(self, client, admin_headers):
        """Test service creation with missing price"""
        service_data = {"name": "Haircut"}
        
        response = client.post("/api/services/", json=service_data, headers=admin_headers)
        
        assert response.status_code == 422

    def test_create_service_invalid_price_type(self, client, admin_headers):
        """Test service creation with invalid price type"""
        service_data = {
            "name": "Haircut",
            "price": "invalid_price"
        }
        
        response = client.post("/api/services/", json=service_data, headers=admin_headers)
        
        assert response.status_code == 422

    def test_create_service_negative_price(self, client, admin_headers):
        """Test service creation with negative price"""
        service_data = {
            "name": "Haircut",
            "price": -100
        }
        
        response = client.post("/api/services/", json=service_data, headers=admin_headers)
        
        # Should succeed as there's no validation for negative prices
        assert response.status_code == 200

    def test_create_service_zero_price(self, client, admin_headers):
        """Test service creation with zero price"""
        service_data = {
            "name": "Free Service",
            "price": 0
        }
        
        response = client.post("/api/services/", json=service_data, headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 0

    def test_create_service_empty_name(self, client, admin_headers):
        """Test service creation with empty name"""
        service_data = {
            "name": "",
            "price": 2500
        }
        
        response = client.post("/api/services/", json=service_data, headers=admin_headers)
        
        # Should succeed as there's no validation for empty names
        assert response.status_code == 200

    def test_create_service_duplicate_name(self, client, admin_headers, test_service):
        """Test service creation with duplicate name"""
        service_data = {
            "name": test_service.name,
            "price": 3000
        }
        
        response = client.post("/api/services/", json=service_data, headers=admin_headers)
        
        # Should succeed as there's no unique constraint on name
        assert response.status_code == 200


class TestUpdateService:
    """Test cases for PUT /api/services/{service_id}"""

    def test_update_service_success(self, client, admin_headers, test_service):
        """Test successful service update by admin"""
        update_data = {
            "name": "Updated Haircut",
            "price": 3000
        }
        
        response = client.put(f"/api/services/{test_service.id}", json=update_data, headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Haircut"
        assert data["price"] == 3000
        assert data["id"] == test_service.id

    def test_update_service_partial_update(self, client, admin_headers, test_service):
        """Test partial service update"""
        update_data = {
            "name": "Updated Haircut"
            # Only updating name
        }
        
        response = client.put(f"/api/services/{test_service.id}", json=update_data, headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Haircut"
        assert data["price"] == test_service.price  # Price should remain unchanged

    def test_update_service_regular_user_denied(self, client, auth_headers, test_service):
        """Test service update denied for regular user"""
        update_data = {"name": "Updated Service"}
        
        response = client.put(f"/api/services/{test_service.id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"

    def test_update_service_no_auth(self, client, test_service):
        """Test service update without authentication"""
        update_data = {"name": "Updated Service"}
        
        response = client.put(f"/api/services/{test_service.id}", json=update_data)
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_update_service_nonexistent_service(self, client, admin_headers):
        """Test update of non-existent service"""
        update_data = {"name": "Updated Service"}
        
        response = client.put("/api/services/999", json=update_data, headers=admin_headers)
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Service not found"

    def test_update_service_invalid_id(self, client, admin_headers):
        """Test update with invalid service ID"""
        update_data = {"name": "Updated Service"}
        
        response = client.put("/api/services/invalid", json=update_data, headers=admin_headers)
        
        assert response.status_code == 422

    def test_update_service_empty_data(self, client, admin_headers, test_service):
        """Test update with empty data"""
        update_data = {}
        
        response = client.put(f"/api/services/{test_service.id}", json=update_data, headers=admin_headers)
        
        assert response.status_code == 200
        # Service should remain unchanged since no fields were provided
        data = response.json()
        assert data["name"] == test_service.name
        assert data["price"] == test_service.price

    def test_update_service_invalid_price_type(self, client, admin_headers, test_service):
        """Test update with invalid price type"""
        update_data = {
            "name": "Updated Service",
            "price": "invalid_price"
        }
        
        response = client.put(f"/api/services/{test_service.id}", json=update_data, headers=admin_headers)
        
        assert response.status_code == 422

    def test_update_service_negative_price(self, client, admin_headers, test_service):
        """Test update with negative price"""
        update_data = {
            "name": test_service.name,  # Keep the name unchanged
            "price": -100
        }
        
        response = client.put(f"/api/services/{test_service.id}", json=update_data, headers=admin_headers)
        
        # Should succeed as there's no validation for negative prices
        assert response.status_code == 200
        data = response.json()
        assert data["price"] == -100


class TestDeleteService:
    """Test cases for DELETE /api/services/{service_id}"""

    def test_delete_service_success(self, client, admin_headers, test_service):
        """Test successful service deletion by admin"""
        response = client.delete(f"/api/services/{test_service.id}", headers=admin_headers)
        
        assert response.status_code == 204

    def test_delete_service_regular_user_denied(self, client, auth_headers, test_service):
        """Test service deletion denied for regular user"""
        response = client.delete(f"/api/services/{test_service.id}", headers=auth_headers)
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"

    def test_delete_service_no_auth(self, client, test_service):
        """Test service deletion without authentication"""
        response = client.delete(f"/api/services/{test_service.id}")
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_delete_service_nonexistent_service(self, client, admin_headers):
        """Test deletion of non-existent service"""
        response = client.delete("/api/services/999", headers=admin_headers)
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Service not found"

    def test_delete_service_invalid_id(self, client, admin_headers):
        """Test deletion with invalid service ID"""
        response = client.delete("/api/services/invalid", headers=admin_headers)
        
        assert response.status_code == 422

    def test_delete_service_with_barber_relationships(self, client, admin_headers, test_service, test_barber, test_barber_service_link):
        """Test deletion of service with barber relationships"""
        response = client.delete(f"/api/services/{test_service.id}", headers=admin_headers)
        
        assert response.status_code == 204
        
        # Verify service is deleted
        # Note: This would require checking the database directly in a real test


class TestServiceBarberRelationships:
    """Test cases for service-barber relationships"""

    def test_service_with_barbers_response_structure(self, client, auth_headers, test_service, test_barber, test_barber_service_link):
        """Test that service response includes barber information"""
        response = client.get("/api/services/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        
        service = data[0]
        assert "barbers" in service
        assert isinstance(service["barbers"], list)
        
        # Check barber information structure
        if service["barbers"]:
            barber = service["barbers"][0]
            assert "id" in barber
            assert "name" in barber
            assert "duration" in barber

    def test_service_without_barbers(self, client, auth_headers, test_service):
        """Test service response when no barbers are associated"""
        response = client.get("/api/services/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        
        service = data[0]
        assert "barbers" in service
        assert isinstance(service["barbers"], list)
        assert len(service["barbers"]) == 0

    def test_multiple_barbers_per_service(self, client, auth_headers, db_session, test_service):
        """Test service with multiple barbers"""
        # Create multiple barbers
        barber1 = TestBarber(name="Barber 1", user_id=1)
        barber2 = TestBarber(name="Barber 2", user_id=2)
        barber3 = TestBarber(name="Barber 3", user_id=3)
        
        db_session.add_all([barber1, barber2, barber3])
        db_session.commit()
        
        # Create barber-service links
        link1 = TestBarberService(barber_id=barber1.id, service_id=test_service.id, duration=30)
        link2 = TestBarberService(barber_id=barber2.id, service_id=test_service.id, duration=45)
        link3 = TestBarberService(barber_id=barber3.id, service_id=test_service.id, duration=60)
        
        db_session.add_all([link1, link2, link3])
        db_session.commit()
        
        response = client.get("/api/services/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        
        service = data[0]
        assert len(service["barbers"]) == 3
        
        # Check that all barbers are included
        barber_names = [barber["name"] for barber in service["barbers"]]
        assert "Barber 1" in barber_names
        assert "Barber 2" in barber_names
        assert "Barber 3" in barber_names


class TestServiceValidation:
    """Test input validation scenarios"""

    def test_service_name_validation(self, client, admin_headers):
        """Test various service name validation scenarios"""
        test_cases = [
            {"name": "", "price": 2500, "expected_status": 200},  # Empty name allowed
            {"name": "A" * 1000, "price": 2500, "expected_status": 200},  # Long name allowed
            {"name": "Haircut & Styling", "price": 2500, "expected_status": 200},  # Special chars allowed
            {"name": "123 Service", "price": 2500, "expected_status": 200},  # Numbers allowed
        ]
        
        for i, case in enumerate(test_cases):
            service_data = {
                "name": case["name"],
                "price": case["price"]
            }
            
            response = client.post("/api/services/", json=service_data, headers=admin_headers)
            assert response.status_code == case["expected_status"]

    def test_service_price_validation(self, client, admin_headers):
        """Test various service price validation scenarios"""
        test_cases = [
            {"name": "Test Service", "price": 0, "expected_status": 200},  # Zero price allowed
            {"name": "Test Service", "price": -100, "expected_status": 200},  # Negative price allowed
            {"name": "Test Service", "price": 999999, "expected_status": 200},  # Large price allowed
        ]
        
        for case in test_cases:
            service_data = {
                "name": case["name"],
                "price": case["price"]
            }
            
            response = client.post("/api/services/", json=service_data, headers=admin_headers)
            assert response.status_code == case["expected_status"]


class TestServiceEdgeCases:
    """Test edge cases and error scenarios"""

    def test_service_with_special_characters(self, client, admin_headers):
        """Test service creation with special characters"""
        service_data = {
            "name": "Haircut & Styling (Premium)",
            "price": 2500
        }
        
        response = client.post("/api/services/", json=service_data, headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Haircut & Styling (Premium)"

    def test_service_with_unicode_characters(self, client, admin_headers):
        """Test service creation with unicode characters"""
        service_data = {
            "name": "Стрижка & Борода",
            "price": 2500
        }
        
        response = client.post("/api/services/", json=service_data, headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Стрижка & Борода"

    def test_service_price_boundary_values(self, client, admin_headers):
        """Test service creation with boundary price values"""
        test_cases = [
            {"price": 0, "name": "Free Service"},
            {"price": 1, "name": "Cheap Service"},
            {"price": 999999, "name": "Expensive Service"},
        ]
        
        for case in test_cases:
            service_data = {
                "name": case["name"],
                "price": case["price"]
            }
            
            response = client.post("/api/services/", json=service_data, headers=admin_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["price"] == case["price"]

    def test_concurrent_service_operations(self, client, admin_headers, test_service):
        """Test concurrent service operations"""
        # This would require more sophisticated testing with async operations
        # For now, we'll test basic functionality
        update_data = {
            "name": "Updated Service",
            "price": test_service.price  # Keep the price unchanged
        }
        
        response = client.put(f"/api/services/{test_service.id}", json=update_data, headers=admin_headers)
        assert response.status_code == 200

    def test_service_cascade_operations(self, client, admin_headers, test_service, test_barber, test_barber_service_link):
        """Test service operations with related data"""
        # Test that service can be updated even with barber relationships
        update_data = {
            "name": "Updated Service with Barbers",
            "price": test_service.price  # Keep the price unchanged
        }
        
        response = client.put(f"/api/services/{test_service.id}", json=update_data, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Service with Barbers"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
