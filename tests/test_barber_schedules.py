import pytest
import os
import sys
from datetime import datetime, timedelta, time, UTC
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import test database setup first
from .test_database import (
    TestBase, engine, TestingSessionLocal, TestUser, TestBarber, TestService, 
    TestAddon, TestBarberService, TestBarberAddon, TestBarberSchedule, TestBarberUnavailableTime,
    override_get_db_with_test_user, create_test_tables, drop_test_tables, 
    get_test_current_user, create_test_admin_required, create_test_barber_required, 
    TestDatabaseSession
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


class TestBarberSchedules:
    """Test cases for barber schedule management endpoints"""

    def test_create_schedule_success(self, client, admin_headers, test_barber):
        """Test successful creation of a barber schedule"""
        schedule_data = {
            "day_of_week": 1,  # Monday
            "start_time": "09:00",
            "end_time": "18:00"
        }
        
        response = client.post(
            f"/api/barbers/{test_barber.id}/schedules/",
            json=schedule_data,
            headers=admin_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["barber_id"] == test_barber.id
        assert data["day_of_week"] == 1
        assert data["start_time"] == "09:00:00"
        assert data["end_time"] == "18:00:00"
        assert "id" in data

    def test_create_schedule_invalid_barber(self, client, admin_headers):
        """Test creating schedule for non-existent barber"""
        schedule_data = {
            "day_of_week": 1,
            "start_time": "09:00",
            "end_time": "18:00"
        }
        
        response = client.post(
            "/api/barbers/999/schedules/",
            json=schedule_data,
            headers=admin_headers
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Barber not found"

    def test_create_schedule_invalid_time_range(self, client, admin_headers, test_barber):
        """Test creating schedule with invalid time range (start >= end)"""
        schedule_data = {
            "day_of_week": 1,
            "start_time": "18:00",
            "end_time": "09:00"
        }
        
        response = client.post(
            f"/api/barbers/{test_barber.id}/schedules/",
            json=schedule_data,
            headers=admin_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "time_validation" in str(data)

    def test_create_schedule_invalid_day_of_week(self, client, admin_headers, test_barber):
        """Test creating schedule with invalid day of week"""
        schedule_data = {
            "day_of_week": 7,  # Invalid day
            "start_time": "09:00",
            "end_time": "18:00"
        }
        
        response = client.post(
            f"/api/barbers/{test_barber.id}/schedules/",
            json=schedule_data,
            headers=admin_headers
        )
        
        assert response.status_code == 422

    def test_create_schedule_unauthorized(self, client, user_headers, test_barber):
        """Test creating schedule without admin privileges"""
        schedule_data = {
            "day_of_week": 1,
            "start_time": "09:00",
            "end_time": "18:00"
        }
        
        response = client.post(
            f"/api/barbers/{test_barber.id}/schedules/",
            json=schedule_data,
            headers=user_headers
        )
        
        assert response.status_code == 403

    def test_get_barber_schedules_success(self, client, user_headers, test_barber, db_session):
        """Test successful retrieval of barber schedules"""
        # Create a test schedule
        schedule = TestBarberSchedule(
            barber_id=test_barber.id,
            day_of_week=1,
            start_time="09:00",
            end_time="18:00"
        )
        db_session.add(schedule)
        db_session.commit()
        
        response = client.get(
            f"/api/barbers/{test_barber.id}/schedules/",
            headers=user_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["barber_id"] == test_barber.id
        assert data[0]["day_of_week"] == 1
        assert data[0]["start_time"] == "09:00:00"
        assert data[0]["end_time"] == "18:00:00"

    def test_get_barber_schedules_empty(self, client, user_headers, test_barber):
        """Test getting schedules for barber with no schedules"""
        response = client.get(
            f"/api/barbers/{test_barber.id}/schedules/",
            headers=user_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_barber_schedules_invalid_barber(self, client, user_headers):
        """Test getting schedules for non-existent barber"""
        response = client.get(
            "/api/barbers/999/schedules/",
            headers=user_headers
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Barber not found"

    def test_get_schedule_by_id_success(self, client, user_headers, test_barber, db_session):
        """Test successful retrieval of specific schedule by ID"""
        # Create a test schedule
        schedule = TestBarberSchedule(
            barber_id=test_barber.id,
            day_of_week=1,
            start_time="09:00",
            end_time="18:00"
        )
        db_session.add(schedule)
        db_session.commit()
        db_session.refresh(schedule)
        
        response = client.get(
            f"/api/barbers/schedules/{schedule.id}",
            headers=user_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == schedule.id
        assert data["barber_id"] == test_barber.id
        assert data["day_of_week"] == 1
        assert data["start_time"] == "09:00:00"
        assert data["end_time"] == "18:00:00"

    def test_get_schedule_by_id_not_found(self, client, user_headers):
        """Test getting non-existent schedule by ID"""
        response = client.get(
            "/api/barbers/schedules/999",
            headers=user_headers
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Schedule entry not found"

    def test_update_schedule_success(self, client, admin_headers, test_barber, db_session):
        """Test successful update of barber schedule"""
        # Create a test schedule
        schedule = TestBarberSchedule(
            barber_id=test_barber.id,
            day_of_week=1,
            start_time="09:00",
            end_time="18:00"
        )
        db_session.add(schedule)
        db_session.commit()
        db_session.refresh(schedule)
        
        update_data = {
            "start_time": "10:00",
            "end_time": "19:00"
        }
        
        response = client.patch(
            f"/api/barbers/schedules/{schedule.id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == schedule.id
        assert data["start_time"] == "10:00:00"
        assert data["end_time"] == "19:00:00"
        assert data["day_of_week"] == 1  # Should remain unchanged

    def test_update_schedule_partial(self, client, admin_headers, test_barber, db_session):
        """Test partial update of barber schedule"""
        # Create a test schedule
        schedule = TestBarberSchedule(
            barber_id=test_barber.id,
            day_of_week=1,
            start_time="09:00",
            end_time="18:00"
        )
        db_session.add(schedule)
        db_session.commit()
        db_session.refresh(schedule)
        
        update_data = {
            "start_time": "10:00"
        }
        
        response = client.patch(
            f"/api/barbers/schedules/{schedule.id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["start_time"] == "10:00:00"
        assert data["end_time"] == "18:00:00"  # Should remain unchanged

    def test_update_schedule_invalid_time_range(self, client, admin_headers, test_barber, db_session):
        """Test updating schedule with invalid time range"""
        # Create a test schedule
        schedule = TestBarberSchedule(
            barber_id=test_barber.id,
            day_of_week=1,
            start_time="09:00",
            end_time="18:00"
        )
        db_session.add(schedule)
        db_session.commit()
        db_session.refresh(schedule)
        
        update_data = {
            "start_time": "19:00",
            "end_time": "18:00"
        }
        
        response = client.patch(
            f"/api/barbers/schedules/{schedule.id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "time_validation" in str(data)

    def test_update_schedule_not_found(self, client, admin_headers):
        """Test updating non-existent schedule"""
        update_data = {
            "start_time": "10:00"
        }
        
        response = client.patch(
            "/api/barbers/schedules/999",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Schedule entry not found"

    def test_update_schedule_unauthorized(self, client, user_headers, test_barber, db_session):
        """Test updating schedule without admin privileges"""
        # Create a test schedule
        schedule = TestBarberSchedule(
            barber_id=test_barber.id,
            day_of_week=1,
            start_time="09:00",
            end_time="18:00"
        )
        db_session.add(schedule)
        db_session.commit()
        db_session.refresh(schedule)
        
        update_data = {
            "start_time": "10:00"
        }
        
        response = client.patch(
            f"/api/barbers/schedules/{schedule.id}",
            json=update_data,
            headers=user_headers
        )
        
        assert response.status_code == 403

    def test_delete_schedule_success(self, client, admin_headers, test_barber, db_session):
        """Test successful deletion of barber schedule"""
        # Create a test schedule
        schedule = TestBarberSchedule(
            barber_id=test_barber.id,
            day_of_week=1,
            start_time="09:00",
            end_time="18:00"
        )
        db_session.add(schedule)
        db_session.commit()
        db_session.refresh(schedule)
        
        response = client.delete(
            f"/api/barbers/schedules/{schedule.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 204

    def test_delete_schedule_not_found(self, client, admin_headers):
        """Test deleting non-existent schedule"""
        response = client.delete(
            "/api/barbers/schedules/999",
            headers=admin_headers
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Schedule entry not found"

    def test_delete_schedule_unauthorized(self, client, user_headers, test_barber, db_session):
        """Test deleting schedule without admin privileges"""
        # Create a test schedule
        schedule = TestBarberSchedule(
            barber_id=test_barber.id,
            day_of_week=1,
            start_time="09:00",
            end_time="18:00"
        )
        db_session.add(schedule)
        db_session.commit()
        db_session.refresh(schedule)
        
        response = client.delete(
            f"/api/barbers/schedules/{schedule.id}",
            headers=user_headers
        )
        
        assert response.status_code == 403


class TestBarberUnavailableTimes:
    """Test cases for barber unavailable times management endpoints"""

    def test_create_unavailable_time_success(self, client, admin_headers, test_barber):
        """Test successful creation of barber unavailable time"""
        unavailable_data = {
            "start_time": "2025-06-15T10:00:00+03:00",
            "end_time": "2025-06-15T12:00:00+03:00",
            "reason": "Lunch break"
        }
        
        response = client.post(
            f"/api/barbers/{test_barber.id}/unavailable-times/",
            json=unavailable_data,
            headers=admin_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["barber_id"] == test_barber.id
        assert data["reason"] == "Lunch break"
        assert "id" in data
        # Check that times are properly parsed
        assert "2025-06-15T10:00:00" in data["start_time"]
        assert "2025-06-15T12:00:00" in data["end_time"]

    def test_create_unavailable_time_without_reason(self, client, admin_headers, test_barber):
        """Test creating unavailable time without reason"""
        unavailable_data = {
            "start_time": "2025-06-15T10:00:00+03:00",
            "end_time": "2025-06-15T12:00:00+03:00"
        }
        
        response = client.post(
            f"/api/barbers/{test_barber.id}/unavailable-times/",
            json=unavailable_data,
            headers=admin_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["barber_id"] == test_barber.id
        assert data["reason"] is None

    def test_create_unavailable_time_invalid_barber(self, client, admin_headers):
        """Test creating unavailable time for non-existent barber"""
        unavailable_data = {
            "start_time": "2025-06-15T10:00:00+03:00",
            "end_time": "2025-06-15T12:00:00+03:00",
            "reason": "Lunch break"
        }
        
        response = client.post(
            "/api/barbers/999/unavailable-times/",
            json=unavailable_data,
            headers=admin_headers
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Barber not found"

    def test_create_unavailable_time_invalid_datetime_range(self, client, admin_headers, test_barber):
        """Test creating unavailable time with invalid datetime range"""
        unavailable_data = {
            "start_time": "2025-06-15T12:00:00+03:00",
            "end_time": "2025-06-15T10:00:00+03:00",
            "reason": "Invalid range"
        }
        
        response = client.post(
            f"/api/barbers/{test_barber.id}/unavailable-times/",
            json=unavailable_data,
            headers=admin_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "datetime_validation" in str(data)

    def test_create_unavailable_time_unauthorized(self, client, user_headers, test_barber):
        """Test creating unavailable time without admin privileges"""
        unavailable_data = {
            "start_time": "2025-06-15T10:00:00+03:00",
            "end_time": "2025-06-15T12:00:00+03:00",
            "reason": "Lunch break"
        }
        
        response = client.post(
            f"/api/barbers/{test_barber.id}/unavailable-times/",
            json=unavailable_data,
            headers=user_headers
        )
        
        assert response.status_code == 403

    def test_get_barber_unavailable_times_success(self, client, user_headers, test_barber, db_session):
        """Test successful retrieval of barber unavailable times"""
        # Create a test unavailable time
        unavailable_time = TestBarberUnavailableTime(
            barber_id=test_barber.id,
            start_time=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC),
            reason="Lunch break"
        )
        db_session.add(unavailable_time)
        db_session.commit()
        
        response = client.get(
            f"/api/barbers/{test_barber.id}/unavailable-times/",
            headers=user_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["barber_id"] == test_barber.id
        assert data[0]["reason"] == "Lunch break"

    def test_get_barber_unavailable_times_empty(self, client, user_headers, test_barber):
        """Test getting unavailable times for barber with none"""
        response = client.get(
            f"/api/barbers/{test_barber.id}/unavailable-times/",
            headers=user_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_barber_unavailable_times_invalid_barber(self, client, user_headers):
        """Test getting unavailable times for non-existent barber"""
        response = client.get(
            "/api/barbers/999/unavailable-times/",
            headers=user_headers
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Barber not found"

    def test_get_unavailable_time_by_id_success(self, client, admin_headers, test_barber, db_session):
        """Test successful retrieval of specific unavailable time by ID"""
        # Create a test unavailable time
        unavailable_time = TestBarberUnavailableTime(
            barber_id=test_barber.id,
            start_time=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC),
            reason="Lunch break"
        )
        db_session.add(unavailable_time)
        db_session.commit()
        db_session.refresh(unavailable_time)
        
        response = client.get(
            f"/api/barbers/unavailable-times/{unavailable_time.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == unavailable_time.id
        assert data["barber_id"] == test_barber.id
        assert data["reason"] == "Lunch break"

    def test_get_unavailable_time_by_id_not_found(self, client, admin_headers):
        """Test getting non-existent unavailable time by ID"""
        response = client.get(
            "/api/barbers/unavailable-times/999",
            headers=admin_headers
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Unavailable time entry not found"

    def test_update_unavailable_time_success(self, client, admin_headers, test_barber, db_session):
        """Test successful update of barber unavailable time"""
        # Create a test unavailable time
        unavailable_time = TestBarberUnavailableTime(
            barber_id=test_barber.id,
            start_time=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC),
            reason="Lunch break"
        )
        db_session.add(unavailable_time)
        db_session.commit()
        db_session.refresh(unavailable_time)
        
        update_data = {
            "start_time": "2025-06-15T11:00:00+03:00",
            "end_time": "2025-06-15T13:00:00+03:00",
            "reason": "Extended lunch break"
        }
        
        response = client.patch(
            f"/api/barbers/unavailable-times/{unavailable_time.id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == unavailable_time.id
        assert data["reason"] == "Extended lunch break"
        assert "2025-06-15T11:00:00" in data["start_time"]
        assert "2025-06-15T13:00:00" in data["end_time"]

    def test_update_unavailable_time_partial(self, client, admin_headers, test_barber, db_session):
        """Test partial update of barber unavailable time"""
        # Create a test unavailable time
        unavailable_time = TestBarberUnavailableTime(
            barber_id=test_barber.id,
            start_time=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC),
            reason="Lunch break"
        )
        db_session.add(unavailable_time)
        db_session.commit()
        db_session.refresh(unavailable_time)
        
        update_data = {
            "reason": "Updated reason"
        }
        
        response = client.patch(
            f"/api/barbers/unavailable-times/{unavailable_time.id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["reason"] == "Updated reason"
        # Other fields should remain unchanged

    def test_update_unavailable_time_invalid_datetime_range(self, client, admin_headers, test_barber, db_session):
        """Test updating unavailable time with invalid datetime range"""
        # Create a test unavailable time
        unavailable_time = TestBarberUnavailableTime(
            barber_id=test_barber.id,
            start_time=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC),
            reason="Lunch break"
        )
        db_session.add(unavailable_time)
        db_session.commit()
        db_session.refresh(unavailable_time)
        
        update_data = {
            "start_time": "2025-06-15T13:00:00+03:00",
            "end_time": "2025-06-15T12:00:00+03:00"
        }
        
        response = client.patch(
            f"/api/barbers/unavailable-times/{unavailable_time.id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "datetime_validation" in str(data)

    def test_update_unavailable_time_not_found(self, client, admin_headers):
        """Test updating non-existent unavailable time"""
        update_data = {
            "reason": "Updated reason"
        }
        
        response = client.patch(
            "/api/barbers/unavailable-times/999",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Unavailable time entry not found"

    def test_get_unavailable_time_by_id_unauthorized(self, client, user_headers):
        """Test getting unavailable time by ID without admin privileges"""
        response = client.get(
            "/api/barbers/unavailable-times/999",
            headers=user_headers
        )
        
        assert response.status_code == 403

    def test_update_unavailable_time_unauthorized(self, client, user_headers, test_barber, db_session):
        """Test updating unavailable time without admin privileges"""
        # Create a test unavailable time
        unavailable_time = TestBarberUnavailableTime(
            barber_id=test_barber.id,
            start_time=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC),
            reason="Lunch break"
        )
        db_session.add(unavailable_time)
        db_session.commit()
        db_session.refresh(unavailable_time)
        
        update_data = {
            "reason": "Updated reason"
        }
        
        response = client.patch(
            f"/api/barbers/unavailable-times/{unavailable_time.id}",
            json=update_data,
            headers=user_headers
        )
        
        assert response.status_code == 403

    def test_delete_unavailable_time_success(self, client, admin_headers, test_barber, db_session):
        """Test successful deletion of barber unavailable time"""
        # Create a test unavailable time
        unavailable_time = TestBarberUnavailableTime(
            barber_id=test_barber.id,
            start_time=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC),
            reason="Lunch break"
        )
        db_session.add(unavailable_time)
        db_session.commit()
        db_session.refresh(unavailable_time)
        
        response = client.delete(
            f"/api/barbers/unavailable-times/{unavailable_time.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 204

    def test_delete_unavailable_time_not_found(self, client, admin_headers):
        """Test deleting non-existent unavailable time"""
        response = client.delete(
            "/api/barbers/unavailable-times/999",
            headers=admin_headers
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Unavailable time entry not found"

    def test_delete_unavailable_time_unauthorized(self, client, user_headers, test_barber, db_session):
        """Test deleting unavailable time without admin privileges"""
        # Create a test unavailable time
        unavailable_time = TestBarberUnavailableTime(
            barber_id=test_barber.id,
            start_time=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC),
            end_time=datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC),
            reason="Lunch break"
        )
        db_session.add(unavailable_time)
        db_session.commit()
        db_session.refresh(unavailable_time)
        
        response = client.delete(
            f"/api/barbers/unavailable-times/{unavailable_time.id}",
            headers=user_headers
        )
        
        assert response.status_code == 403


class TestBarberScheduleValidation:
    """Test cases for schedule validation and conflicts"""

    def test_schedule_time_validation_edge_cases(self, client, admin_headers, test_barber):
        """Test edge cases for schedule time validation"""
        # Test same start and end time
        schedule_data = {
            "day_of_week": 1,
            "start_time": "09:00",
            "end_time": "09:00"
        }
        
        response = client.post(
            f"/api/barbers/{test_barber.id}/schedules/",
            json=schedule_data,
            headers=admin_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "time_validation" in str(data)

    def test_unavailable_time_datetime_validation_edge_cases(self, client, admin_headers, test_barber):
        """Test edge cases for unavailable time datetime validation"""
        # Test same start and end datetime
        unavailable_data = {
            "start_time": "2025-06-15T10:00:00+03:00",
            "end_time": "2025-06-15T10:00:00+03:00",
            "reason": "Same time"
        }
        
        response = client.post(
            f"/api/barbers/{test_barber.id}/unavailable-times/",
            json=unavailable_data,
            headers=admin_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "datetime_validation" in str(data)

    def test_schedule_day_of_week_boundaries(self, client, admin_headers, test_barber):
        """Test day of week boundary values"""
        # Test valid boundary values
        valid_days = [0, 6]  # Sunday and Saturday
        for day in valid_days:
            schedule_data = {
                "day_of_week": day,
                "start_time": "09:00",
                "end_time": "18:00"
            }
            
            response = client.post(
                f"/api/barbers/{test_barber.id}/schedules/",
                json=schedule_data,
                headers=admin_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["day_of_week"] == day

    def test_unavailable_time_reason_length_validation(self, client, admin_headers, test_barber):
        """Test unavailable time reason length validation"""
        # Test reason that's too long (over 255 characters)
        long_reason = "A" * 256
        unavailable_data = {
            "start_time": "2025-06-15T10:00:00+03:00",
            "end_time": "2025-06-15T12:00:00+03:00",
            "reason": long_reason
        }
        
        response = client.post(
            f"/api/barbers/{test_barber.id}/unavailable-times/",
            json=unavailable_data,
            headers=admin_headers
        )
        
        assert response.status_code == 422

    def test_multiple_schedules_same_day(self, client, admin_headers, test_barber):
        """Test creating multiple schedules for the same day"""
        # Create first schedule
        schedule1_data = {
            "day_of_week": 1,
            "start_time": "09:00",
            "end_time": "12:00"
        }
        
        response1 = client.post(
            f"/api/barbers/{test_barber.id}/schedules/",
            json=schedule1_data,
            headers=admin_headers
        )
        
        assert response1.status_code == 201
        
        # Create second schedule for same day
        schedule2_data = {
            "day_of_week": 1,
            "start_time": "13:00",
            "end_time": "18:00"
        }
        
        response2 = client.post(
            f"/api/barbers/{test_barber.id}/schedules/",
            json=schedule2_data,
            headers=admin_headers
        )
        
        assert response2.status_code == 201
        
        # Verify both schedules exist
        response = client.get(
            f"/api/barbers/{test_barber.id}/schedules/",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_multiple_unavailable_times_overlapping(self, client, admin_headers, test_barber):
        """Test creating multiple overlapping unavailable times"""
        # Create first unavailable time
        unavailable1_data = {
            "start_time": "2025-06-15T10:00:00+03:00",
            "end_time": "2025-06-15T12:00:00+03:00",
            "reason": "Morning break"
        }
        
        response1 = client.post(
            f"/api/barbers/{test_barber.id}/unavailable-times/",
            json=unavailable1_data,
            headers=admin_headers
        )
        
        assert response1.status_code == 201
        
        # Create overlapping unavailable time
        unavailable2_data = {
            "start_time": "2025-06-15T11:00:00+03:00",
            "end_time": "2025-06-15T13:00:00+03:00",
            "reason": "Lunch break"
        }
        
        response2 = client.post(
            f"/api/barbers/{test_barber.id}/unavailable-times/",
            json=unavailable2_data,
            headers=admin_headers
        )
        
        assert response2.status_code == 201
        
        # Verify both unavailable times exist
        response = client.get(
            f"/api/barbers/{test_barber.id}/unavailable-times/",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
