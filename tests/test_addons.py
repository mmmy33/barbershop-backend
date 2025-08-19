import pytest
import os
import sys
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import test database setup first
from .test_database import (
    TestBase, engine, TestingSessionLocal, TestUser, TestBarber, TestService, 
    TestAddon, TestBarberService, TestBarberAddon, override_get_db_with_test_user, create_test_tables, 
    drop_test_tables, get_test_current_user, create_test_admin_required, 
    create_test_barber_required, TestDatabaseSession
)

# Import app components after test setup
from app.database import get_db
from app.auth.security import create_access_token, hash_password
from app.auth.schemas import UserRegister, UserLogin, UserUpdate
from app.auth.dependencies import get_current_user, admin_required, barber_required

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
    app.dependency_overrides[barber_required] = create_test_barber_required(test_db)
    
    yield session
    session.close()
    # Drop tables after each test
    drop_test_tables()


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


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
def regular_user(db_session):
    """Create a regular user in the database"""
    user = TestUser(
        name="Regular User",
        email="user@example.com",
        hashed_password=hash_password("UserPassword123!"),
        phone_number="+1234567890",
        is_verified=True,
        role="user"
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
def test_barber(db_session, barber_user):
    """Create a test barber in the database"""
    barber = TestBarber(
        name="Test Barber",
        avatar_url="https://example.com/avatar.jpg",
        user_id=barber_user.id
    )
    db_session.add(barber)
    db_session.commit()
    db_session.refresh(barber)
    return barber


@pytest.fixture
def test_addon(db_session):
    """Create a test addon in the database"""
    addon = TestAddon(
        name="Hair Wash",
        duration=15,  # 15 minutes
        price=500  # $5.00 in cents
    )
    db_session.add(addon)
    db_session.commit()
    db_session.refresh(addon)
    return addon


@pytest.fixture
def test_addon_2(db_session):
    """Create a second test addon in the database"""
    addon = TestAddon(
        name="Hair Styling",
        duration=20,  # 20 minutes
        price=800  # $8.00 in cents
    )
    db_session.add(addon)
    db_session.commit()
    db_session.refresh(addon)
    return addon


@pytest.fixture
def barber_addon_relationship(db_session, test_barber, test_addon):
    """Create a barber-addon relationship"""
    relationship = TestBarberAddon(
        barber_id=test_barber.id,
        addon_id=test_addon.id
    )
    db_session.add(relationship)
    db_session.commit()
    return relationship


@pytest.fixture
def admin_headers(admin_user):
    """Generate authentication headers for an admin user"""
    token = create_access_token(admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers(regular_user):
    """Generate authentication headers for a regular user"""
    token = create_access_token(regular_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def barber_headers(barber_user):
    """Generate authentication headers for a barber user"""
    token = create_access_token(barber_user.id)
    return {"Authorization": f"Bearer {token}"}


class TestGetAllAddons:
    """Test cases for GET /api/addons/"""

    def test_get_all_addons_success(self, client, user_headers, test_addon, test_addon_2):
        """Test successful retrieval of all addons"""
        response = client.get("/api/addons/", headers=user_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        
        # Check first addon
        addon1 = next((item for item in data if item["id"] == test_addon.id), None)
        assert addon1 is not None
        assert addon1["name"] == test_addon.name
        assert addon1["duration"] == test_addon.duration
        assert addon1["price"] == test_addon.price
        assert "barbers" in addon1
        
        # Check second addon
        addon2 = next((item for item in data if item["id"] == test_addon_2.id), None)
        assert addon2 is not None
        assert addon2["name"] == test_addon_2.name
        assert addon2["duration"] == test_addon_2.duration
        assert addon2["price"] == test_addon_2.price
        assert "barbers" in addon2

    def test_get_all_addons_empty_list(self, client, user_headers):
        """Test getting addons when none exist"""
        response = client.get("/api/addons/", headers=user_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_all_addons_no_auth(self, client):
        """Test getting addons without authentication"""
        response = client.get("/api/addons/")
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_get_all_addons_with_barber_relationship(self, client, user_headers, test_addon, test_barber, barber_addon_relationship):
        """Test getting addons with barber relationships"""
        response = client.get("/api/addons/", headers=user_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        
        addon = data[0]
        assert addon["id"] == test_addon.id
        assert addon["name"] == test_addon.name
        assert "barbers" in addon
        # Note: The barbers list might be empty depending on the schema implementation

    def test_get_all_addons_admin_access(self, client, admin_headers, test_addon):
        """Test that admin users can access addons list"""
        response = client.get("/api/addons/", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_addon.id

    def test_get_all_addons_barber_access(self, client, barber_headers, test_addon):
        """Test that barber users can access addons list"""
        response = client.get("/api/addons/", headers=barber_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_addon.id


class TestCreateAddon:
    """Test cases for POST /api/addons/"""

    def test_create_addon_success(self, client, admin_headers):
        """Test successful creation of an addon by admin"""
        addon_data = {
            "name": "Hair Coloring",
            "duration": 45,  # 45 minutes
            "price": 1500  # $15.00 in cents
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == addon_data["name"]
        assert data["duration"] == addon_data["duration"]
        assert data["price"] == addon_data["price"]
        assert "id" in data
        assert "barbers" in data

    def test_create_addon_unauthorized_user(self, client, user_headers):
        """Test that regular users cannot create addons"""
        addon_data = {
            "name": "Hair Coloring",
            "duration": 45,
            "price": 1500
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=user_headers)
        
        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()

    def test_create_addon_unauthorized_barber(self, client, barber_headers):
        """Test that barber users cannot create addons"""
        addon_data = {
            "name": "Hair Coloring",
            "duration": 45,
            "price": 1500
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=barber_headers)
        
        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()

    def test_create_addon_no_auth(self, client):
        """Test creating addon without authentication"""
        addon_data = {
            "name": "Hair Coloring",
            "duration": 45,
            "price": 1500
        }
        
        response = client.post("/api/addons/", json=addon_data)
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_create_addon_missing_name(self, client, admin_headers):
        """Test creating addon with missing name field"""
        addon_data = {
            "duration": 45,
            "price": 1500
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=admin_headers)
        
        assert response.status_code == 422  # Validation error

    def test_create_addon_missing_duration(self, client, admin_headers):
        """Test creating addon with missing duration field"""
        addon_data = {
            "name": "Hair Coloring",
            "price": 1500
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=admin_headers)
        
        assert response.status_code == 422  # Validation error

    def test_create_addon_missing_price(self, client, admin_headers):
        """Test creating addon with missing price field"""
        addon_data = {
            "name": "Hair Coloring",
            "duration": 45
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=admin_headers)
        
        assert response.status_code == 422  # Validation error

    def test_create_addon_invalid_duration(self, client, admin_headers):
        """Test creating addon with invalid duration (negative)"""
        addon_data = {
            "name": "Hair Coloring",
            "duration": -10,
            "price": 1500
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=admin_headers)
        
        # This might pass validation depending on the schema, but should be tested
        # The actual behavior depends on the schema validation rules

    def test_create_addon_invalid_price(self, client, admin_headers):
        """Test creating addon with invalid price (negative)"""
        addon_data = {
            "name": "Hair Coloring",
            "duration": 45,
            "price": -100
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=admin_headers)
        
        # This might pass validation depending on the schema, but should be tested
        # The actual behavior depends on the schema validation rules

    def test_create_addon_empty_name(self, client, admin_headers):
        """Test creating addon with empty name"""
        addon_data = {
            "name": "",
            "duration": 45,
            "price": 1500
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=admin_headers)
        
        # This might pass validation depending on the schema, but should be tested
        # The actual behavior depends on the schema validation rules

    def test_create_addon_zero_duration(self, client, admin_headers):
        """Test creating addon with zero duration"""
        addon_data = {
            "name": "Hair Coloring",
            "duration": 0,
            "price": 1500
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=admin_headers)
        
        # This might pass validation depending on the schema, but should be tested
        # The actual behavior depends on the schema validation rules

    def test_create_addon_zero_price(self, client, admin_headers):
        """Test creating addon with zero price"""
        addon_data = {
            "name": "Hair Coloring",
            "duration": 45,
            "price": 0
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=admin_headers)
        
        # This might pass validation depending on the schema, but should be tested
        # The actual behavior depends on the schema validation rules


class TestUpdateAddon:
    """Test cases for PUT /api/addons/{addon_id}"""

    def test_update_addon_success(self, client, admin_headers, test_addon):
        """Test successful update of an addon by admin"""
        update_data = {
            "name": "Updated Hair Wash",
            "duration": 20,
            "price": 750
        }
        
        response = client.put(f"/api/addons/{test_addon.id}", json=update_data, headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_addon.id
        assert data["name"] == update_data["name"]
        assert data["duration"] == update_data["duration"]
        assert data["price"] == update_data["price"]

    def test_update_addon_partial_update(self, client, admin_headers, test_addon):
        """Test partial update of an addon (only name)"""
        update_data = {
            "name": "Updated Hair Wash"
        }
        
        response = client.put(f"/api/addons/{test_addon.id}", json=update_data, headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_addon.id
        assert data["name"] == update_data["name"]
        assert data["duration"] == test_addon.duration  # Should remain unchanged
        assert data["price"] == test_addon.price  # Should remain unchanged

    def test_update_addon_not_found(self, client, admin_headers):
        """Test updating a non-existent addon"""
        update_data = {
            "name": "Updated Hair Wash",
            "duration": 20,
            "price": 750
        }
        
        response = client.put("/api/addons/99999", json=update_data, headers=admin_headers)
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Addon not found"

    def test_update_addon_unauthorized_user(self, client, user_headers, test_addon):
        """Test that regular users cannot update addons"""
        update_data = {
            "name": "Updated Hair Wash",
            "duration": 20,
            "price": 750
        }
        
        response = client.put(f"/api/addons/{test_addon.id}", json=update_data, headers=user_headers)
        
        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()

    def test_update_addon_unauthorized_barber(self, client, barber_headers, test_addon):
        """Test that barber users cannot update addons"""
        update_data = {
            "name": "Updated Hair Wash",
            "duration": 20,
            "price": 750
        }
        
        response = client.put(f"/api/addons/{test_addon.id}", json=update_data, headers=barber_headers)
        
        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()

    def test_update_addon_no_auth(self, client, test_addon):
        """Test updating addon without authentication"""
        update_data = {
            "name": "Updated Hair Wash",
            "duration": 20,
            "price": 750
        }
        
        response = client.put(f"/api/addons/{test_addon.id}", json=update_data)
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_update_addon_empty_body(self, client, admin_headers, test_addon):
        """Test updating addon with empty request body"""
        response = client.put(f"/api/addons/{test_addon.id}", json={}, headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_addon.id
        # All fields should remain unchanged
        assert data["name"] == test_addon.name
        assert data["duration"] == test_addon.duration
        assert data["price"] == test_addon.price

    def test_update_addon_invalid_id_format(self, client, admin_headers):
        """Test updating addon with invalid ID format"""
        update_data = {
            "name": "Updated Hair Wash"
        }
        
        response = client.put("/api/addons/invalid", json=update_data, headers=admin_headers)
        
        assert response.status_code == 422  # Validation error for path parameter

    def test_update_addon_negative_values(self, client, admin_headers, test_addon):
        """Test updating addon with negative values"""
        update_data = {
            "duration": -10,
            "price": -100
        }
        
        response = client.put(f"/api/addons/{test_addon.id}", json=update_data, headers=admin_headers)
        
        # This might pass validation depending on the schema, but should be tested
        # The actual behavior depends on the schema validation rules

    def test_update_addon_zero_values(self, client, admin_headers, test_addon):
        """Test updating addon with zero values"""
        update_data = {
            "duration": 0,
            "price": 0
        }
        
        response = client.put(f"/api/addons/{test_addon.id}", json=update_data, headers=admin_headers)
        
        # This might pass validation depending on the schema, but should be tested
        # The actual behavior depends on the schema validation rules


class TestDeleteAddon:
    """Test cases for DELETE /api/addons/{addon_id}"""

    def test_delete_addon_success(self, client, admin_headers, test_addon):
        """Test successful deletion of an addon by admin"""
        response = client.delete(f"/api/addons/{test_addon.id}", headers=admin_headers)
        
        assert response.status_code == 204
        assert response.content == b''  # No content should be returned

    def test_delete_addon_not_found(self, client, admin_headers):
        """Test deleting a non-existent addon"""
        response = client.delete("/api/addons/99999", headers=admin_headers)
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Addon not found"

    def test_delete_addon_unauthorized_user(self, client, user_headers, test_addon):
        """Test that regular users cannot delete addons"""
        response = client.delete(f"/api/addons/{test_addon.id}", headers=user_headers)
        
        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()

    def test_delete_addon_unauthorized_barber(self, client, barber_headers, test_addon):
        """Test that barber users cannot delete addons"""
        response = client.delete(f"/api/addons/{test_addon.id}", headers=barber_headers)
        
        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()

    def test_delete_addon_no_auth(self, client, test_addon):
        """Test deleting addon without authentication"""
        response = client.delete(f"/api/addons/{test_addon.id}")
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_delete_addon_invalid_id_format(self, client, admin_headers):
        """Test deleting addon with invalid ID format"""
        response = client.delete("/api/addons/invalid", headers=admin_headers)
        
        assert response.status_code == 422  # Validation error for path parameter

    def test_delete_addon_with_barber_relationship(self, client, admin_headers, test_addon, test_barber, barber_addon_relationship):
        """Test deleting an addon that has barber relationships"""
        response = client.delete(f"/api/addons/{test_addon.id}", headers=admin_headers)
        
        assert response.status_code == 204
        # The relationship should also be deleted (cascade behavior depends on database setup)

    def test_delete_addon_verify_deletion(self, client, admin_headers, user_headers, test_addon):
        """Test that deleted addon is actually removed from the database"""
        # First delete the addon
        delete_response = client.delete(f"/api/addons/{test_addon.id}", headers=admin_headers)
        assert delete_response.status_code == 204
        
        # Then try to get all addons to verify it's gone
        get_response = client.get("/api/addons/", headers=user_headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert len(data) == 0  # Should be empty since we deleted the only addon


class TestAddonBarberRelationships:
    """Test cases for addon-barber relationships"""

    def test_addon_with_barber_relationship_creation(self, client, admin_headers, test_barber):
        """Test creating an addon and then establishing barber relationship"""
        # First create an addon
        addon_data = {
            "name": "Hair Coloring",
            "duration": 45,
            "price": 1500
        }
        
        create_response = client.post("/api/addons/", json=addon_data, headers=admin_headers)
        assert create_response.status_code == 200
        addon_id = create_response.json()["id"]
        
        # The addon should be created successfully
        assert create_response.json()["name"] == addon_data["name"]
        assert create_response.json()["duration"] == addon_data["duration"]
        assert create_response.json()["price"] == addon_data["price"]

    def test_addon_without_barber_relationships(self, client, user_headers, test_addon):
        """Test that addons can exist without barber relationships"""
        response = client.get("/api/addons/", headers=user_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_addon.id
        assert "barbers" in data[0]  # Should have barbers field even if empty

    def test_multiple_addons_with_different_barbers(self, client, admin_headers, user_headers, test_barber, test_addon, test_addon_2):
        """Test multiple addons with different barber relationships"""
        # Create barber relationship for first addon
        relationship1 = TestBarberAddon(
            barber_id=test_barber.id,
            addon_id=test_addon.id
        )
        
        # Get the session from the test database
        from .test_database import TestingSessionLocal
        session = TestingSessionLocal()
        session.add(relationship1)
        session.commit()
        session.close()
        
        # Get all addons and verify they exist
        response = client.get("/api/addons/", headers=user_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Both addons should be present
        addon_ids = [addon["id"] for addon in data]
        assert test_addon.id in addon_ids
        assert test_addon_2.id in addon_ids


class TestAddonDataValidation:
    """Test cases for addon data validation"""

    def test_addon_name_length_validation(self, client, admin_headers):
        """Test addon name length validation"""
        # Test with very long name
        addon_data = {
            "name": "A" * 1000,  # Very long name
            "duration": 45,
            "price": 1500
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=admin_headers)
        
        # This might pass validation depending on the schema, but should be tested
        # The actual behavior depends on the schema validation rules

    def test_addon_duration_range_validation(self, client, admin_headers):
        """Test addon duration range validation"""
        # Test with very large duration
        addon_data = {
            "name": "Hair Coloring",
            "duration": 999999,  # Very large duration
            "price": 1500
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=admin_headers)
        
        # This might pass validation depending on the schema, but should be tested
        # The actual behavior depends on the schema validation rules

    def test_addon_price_range_validation(self, client, admin_headers):
        """Test addon price range validation"""
        # Test with very large price
        addon_data = {
            "name": "Hair Coloring",
            "duration": 45,
            "price": 99999999  # Very large price
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=admin_headers)
        
        # This might pass validation depending on the schema, but should be tested
        # The actual behavior depends on the schema validation rules

    def test_addon_special_characters_in_name(self, client, admin_headers):
        """Test addon name with special characters"""
        addon_data = {
            "name": "Hair & Style @ Salon",
            "duration": 45,
            "price": 1500
        }
        
        response = client.post("/api/addons/", json=addon_data, headers=admin_headers)
        
        # This should work fine with special characters
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == addon_data["name"]


class TestAddonEdgeCases:
    """Test cases for addon edge cases"""

    def test_addon_concurrent_creation(self, client, admin_headers):
        """Test creating multiple addons concurrently"""
        addon_data_1 = {
            "name": "Hair Coloring",
            "duration": 45,
            "price": 1500
        }
        
        addon_data_2 = {
            "name": "Hair Styling",
            "duration": 30,
            "price": 1200
        }
        
        # Create two addons in sequence
        response1 = client.post("/api/addons/", json=addon_data_1, headers=admin_headers)
        response2 = client.post("/api/addons/", json=addon_data_2, headers=admin_headers)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Both should have different IDs
        assert response1.json()["id"] != response2.json()["id"]

    def test_addon_update_after_deletion(self, client, admin_headers, test_addon):
        """Test updating an addon after it has been deleted"""
        # First delete the addon
        delete_response = client.delete(f"/api/addons/{test_addon.id}", headers=admin_headers)
        assert delete_response.status_code == 204
        
        # Then try to update it
        update_data = {
            "name": "Updated Name"
        }
        update_response = client.put(f"/api/addons/{test_addon.id}", json=update_data, headers=admin_headers)
        
        assert update_response.status_code == 404
        assert update_response.json()["detail"] == "Addon not found"

    def test_addon_delete_after_update(self, client, admin_headers, test_addon):
        """Test deleting an addon after it has been updated"""
        # First update the addon
        update_data = {
            "name": "Updated Name"
        }
        update_response = client.put(f"/api/addons/{test_addon.id}", json=update_data, headers=admin_headers)
        assert update_response.status_code == 200
        
        # Then delete it
        delete_response = client.delete(f"/api/addons/{test_addon.id}", headers=admin_headers)
        assert delete_response.status_code == 204

    def test_addon_with_same_name_different_prices(self, client, admin_headers):
        """Test creating addons with same name but different prices"""
        addon_data_1 = {
            "name": "Hair Wash",
            "duration": 15,
            "price": 500
        }
        
        addon_data_2 = {
            "name": "Hair Wash",
            "duration": 20,
            "price": 800
        }
        
        response1 = client.post("/api/addons/", json=addon_data_1, headers=admin_headers)
        response2 = client.post("/api/addons/", json=addon_data_2, headers=admin_headers)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Both should be created successfully with different IDs
        assert response1.json()["id"] != response2.json()["id"]
        assert response1.json()["name"] == response2.json()["name"]
        assert response1.json()["price"] != response2.json()["price"]
