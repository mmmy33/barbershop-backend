import pytest
import os
import sys
from datetime import datetime, timedelta, date, time, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import test database setup first
from .test_database import (
    TestBase, engine, TestingSessionLocal, TestUser, TestBarber, TestService, 
    TestAddon, TestBarberService, TestBarberSchedule, TestBarberUnavailableTime,
    TestAppointment, override_get_db_with_test_user, create_test_tables, 
    drop_test_tables, get_test_current_user, TestDatabaseSession
)

# Import app components after test setup
from app.database import get_db
from app.auth.security import create_access_token, hash_password
from app.auth.dependencies import get_current_user

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
    
    yield session
    session.close()
    # Drop tables after each test
    drop_test_tables()


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def test_user(db_session):
    """Create a test user in the database"""
    user = TestUser(
        name="Test User",
        email="test@example.com",
        hashed_password=hash_password("TestPassword123!"),
        phone_number="+1234567890",
        is_verified=True,
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_barber(db_session, test_user):
    """Create a test barber in the database"""
    barber = TestBarber(
        name="Test Barber",
        avatar_url="https://example.com/avatar.jpg",
        user_id=test_user.id
    )
    db_session.add(barber)
    db_session.commit()
    db_session.refresh(barber)
    return barber


@pytest.fixture
def test_service(db_session):
    """Create a test service in the database"""
    service = TestService(
        name="Haircut",
        price=2500  # $25.00
    )
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)
    return service


@pytest.fixture
def test_addon(db_session):
    """Create a test addon in the database"""
    addon = TestAddon(
        name="Hair Wash",
        duration=15,  # 15 minutes
        price=500  # $5.00
    )
    db_session.add(addon)
    db_session.commit()
    db_session.refresh(addon)
    return addon


@pytest.fixture
def test_barber_service(db_session, test_barber, test_service):
    """Create a barber-service relationship"""
    barber_service = TestBarberService(
        barber_id=test_barber.id,
        service_id=test_service.id,
        duration=30  # 30 minutes
    )
    db_session.add(barber_service)
    db_session.commit()
    return barber_service


@pytest.fixture
def test_barber_schedule(db_session, test_barber):
    """Create a barber schedule for Monday (weekday 0)"""
    schedule = TestBarberSchedule(
        barber_id=test_barber.id,
        day_of_week=0,  # Monday
        start_time="09:00:00",
        end_time="17:00:00"
    )
    db_session.add(schedule)
    db_session.commit()
    return schedule


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers for the test user"""
    token = create_access_token(user_id=test_user.id)
    return {"Authorization": f"Bearer {token}"}


class TestRootEndpoint:
    """Test the root endpoint (GET /)"""
    
    def test_root_endpoint_success(self, client):
        """Test that the root endpoint returns the expected response"""
        response = client.get("/")
        
        assert response.status_code == 200
        assert response.json() == {"message": "Barbershop backend is working"}


class TestTimeslotsAvailability:
    """Test the timeslots availability endpoint (GET /api/timeslots/available)"""
    
    def test_get_available_timeslots_success(self, client, auth_headers, test_barber, test_service, test_barber_service, test_barber_schedule):
        """Test successful retrieval of available timeslots"""
        # Use a Monday date
        target_date = date(2024, 1, 1)  # Monday
        
        response = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [],
                "slot_interval_minutes": 30
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        timeslots = response.json()
        assert isinstance(timeslots, list)
        assert len(timeslots) > 0
        
        # Verify timeslots are in the correct format and timezone
        for slot in timeslots:
            slot_dt = datetime.fromisoformat(slot.replace('Z', '+00:00'))
            assert slot_dt.tzinfo is not None
            assert slot_dt.date() == target_date
            assert slot_dt.hour >= 9 and slot_dt.hour < 17
    
    def test_get_available_timeslots_with_addons(self, client, auth_headers, test_barber, test_service, test_addon, test_barber_service, test_barber_schedule):
        """Test available timeslots calculation with addons"""
        target_date = date(2024, 1, 1)  # Monday
        
        response = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [test_addon.id],
                "slot_interval_minutes": 30
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        timeslots = response.json()
        assert isinstance(timeslots, list)
        
        # With addon (15 min) + service (30 min) = 45 min total duration
        # Should have fewer available slots than without addons
        response_without_addons = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [],
                "slot_interval_minutes": 30
            },
            headers=auth_headers
        )
        
        timeslots_without_addons = response_without_addons.json()
        # Should have more slots without addons (shorter duration)
        assert len(timeslots_without_addons) >= len(timeslots)
    
    def test_get_available_timeslots_barber_not_found(self, client, auth_headers, test_service):
        """Test error when barber doesn't exist"""
        target_date = date(2024, 1, 1)
        
        response = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": 99999,  # Non-existent barber
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [],
                "slot_interval_minutes": 30
            },
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "Barber not found" in response.json()["detail"]
    
    def test_get_available_timeslots_service_not_found(self, client, auth_headers, test_barber):
        """Test error when service doesn't exist"""
        target_date = date(2024, 1, 1)
        
        response = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": 99999,  # Non-existent service
                "addons": [],
                "slot_interval_minutes": 30
            },
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "Service not found" in response.json()["detail"]
    
    def test_get_available_timeslots_no_schedule(self, client, auth_headers, test_barber, test_service, test_barber_service):
        """Test when barber has no schedule for the requested day"""
        # Use a Tuesday (weekday 1) when barber only has Monday schedule
        target_date = date(2024, 1, 2)  # Tuesday
        
        response = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [],
                "slot_interval_minutes": 30
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        timeslots = response.json()
        assert timeslots == []  # No available slots
    
    def test_get_available_timeslots_with_existing_appointments(self, client, auth_headers, test_barber, test_service, test_barber_service, test_barber_schedule, test_user):
        """Test available timeslots when there are existing appointments"""
        target_date = date(2024, 1, 1)  # Monday
        
        # Create an existing appointment at 10:00 AM
        existing_appointment = TestAppointment(
            name="Existing Customer",
            phone_number="+1234567890",
            barber_id=test_barber.id,
            service_id=test_service.id,
            total_duration=30,
            total_price=2500,
            user_id=test_user.id,
            scheduled_time=datetime.combine(target_date, time(10, 0), tzinfo=timezone.utc)
        )
        
        # Add to database
        from .test_database import TestingSessionLocal
        db = TestingSessionLocal()
        db.add(existing_appointment)
        db.commit()
        db.close()
        
        response = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [],
                "slot_interval_minutes": 30
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        timeslots = response.json()
        
        # Verify that 10:00 AM is not in the available timeslots
        ten_am_slot = datetime.combine(target_date, time(10, 0), tzinfo=timezone.utc).isoformat()
        assert ten_am_slot not in timeslots
    
    def test_get_available_timeslots_with_unavailable_time(self, client, auth_headers, test_barber, test_service, test_barber_service, test_barber_schedule):
        """Test available timeslots when barber has unavailable time periods"""
        target_date = date(2024, 1, 1)  # Monday
        
        # Create an unavailable time period from 12:00 PM to 1:00 PM
        unavailable_time = TestBarberUnavailableTime(
            barber_id=test_barber.id,
            start_time=datetime.combine(target_date, time(12, 0), tzinfo=timezone.utc),
            end_time=datetime.combine(target_date, time(13, 0), tzinfo=timezone.utc),
            reason="Lunch break"
        )
        
        # Add to database
        from .test_database import TestingSessionLocal
        db = TestingSessionLocal()
        db.add(unavailable_time)
        db.commit()
        db.close()
        
        response = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [],
                "slot_interval_minutes": 30
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        timeslots = response.json()
        
        # Verify that 12:00 PM is not in the available timeslots
        noon_slot = datetime.combine(target_date, time(12, 0), tzinfo=timezone.utc).isoformat()
        assert noon_slot not in timeslots
    
    def test_get_available_timeslots_different_slot_intervals(self, client, auth_headers, test_barber, test_service, test_barber_service, test_barber_schedule):
        """Test available timeslots with different slot intervals"""
        target_date = date(2024, 1, 1)  # Monday
        
        # Test with 15-minute intervals
        response_15min = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [],
                "slot_interval_minutes": 15
            },
            headers=auth_headers
        )
        
        # Test with 60-minute intervals
        response_60min = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [],
                "slot_interval_minutes": 60
            },
            headers=auth_headers
        )
        
        assert response_15min.status_code == 200
        assert response_60min.status_code == 200
        
        timeslots_15min = response_15min.json()
        timeslots_60min = response_60min.json()
        
        # 15-minute intervals should provide more slots than 60-minute intervals
        assert len(timeslots_15min) >= len(timeslots_60min)
    
    def test_get_available_timeslots_invalid_slot_interval(self, client, auth_headers, test_barber, test_service):
        """Test error with invalid slot interval"""
        target_date = date(2024, 1, 1)
        
        response = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [],
                "slot_interval_minutes": 0  # Invalid interval
            },
            headers=auth_headers
        )
        
        # FastAPI returns 422 for validation errors, not 400
        assert response.status_code == 422
    
    def test_get_available_timeslots_unauthorized(self, client, test_barber, test_service):
        """Test that unauthorized requests are rejected"""
        target_date = date(2024, 1, 1)
        
        response = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [],
                "slot_interval_minutes": 30
            }
            # No auth headers
        )
        
        assert response.status_code == 403
    
    def test_get_available_timeslots_complex_scenario(self, client, auth_headers, test_barber, test_service, test_addon, test_barber_service, test_barber_schedule, test_user):
        """Test complex scenario with multiple appointments and unavailable times"""
        target_date = date(2024, 1, 1)  # Monday
        
        # Create multiple existing appointments
        appointments = [
            TestAppointment(
                name="Customer 1",
                phone_number="+1111111111",
                barber_id=test_barber.id,
                service_id=test_service.id,
                total_duration=30,
                total_price=2500,
                user_id=test_user.id,
                scheduled_time=datetime.combine(target_date, time(10, 0), tzinfo=timezone.utc)
            ),
            TestAppointment(
                name="Customer 2",
                phone_number="+2222222222",
                barber_id=test_barber.id,
                service_id=test_service.id,
                total_duration=45,  # Service + addon
                total_price=3000,
                user_id=test_user.id,
                scheduled_time=datetime.combine(target_date, time(14, 0), tzinfo=timezone.utc)
            )
        ]
        
        # Create unavailable time periods
        unavailable_times = [
            TestBarberUnavailableTime(
                barber_id=test_barber.id,
                start_time=datetime.combine(target_date, time(12, 0), tzinfo=timezone.utc),
                end_time=datetime.combine(target_date, time(13, 0), tzinfo=timezone.utc),
                reason="Lunch break"
            ),
            TestBarberUnavailableTime(
                barber_id=test_barber.id,
                start_time=datetime.combine(target_date, time(15, 30), tzinfo=timezone.utc),
                end_time=datetime.combine(target_date, time(16, 0), tzinfo=timezone.utc),
                reason="Break"
            )
        ]
        
        # Add to database
        from .test_database import TestingSessionLocal
        db = TestingSessionLocal()
        for appointment in appointments:
            db.add(appointment)
        for unavailable_time in unavailable_times:
            db.add(unavailable_time)
        db.commit()
        db.close()
        
        # Test with service only
        response_service_only = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [],
                "slot_interval_minutes": 30
            },
            headers=auth_headers
        )
        
        # Test with service + addon
        response_with_addon = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [test_addon.id],
                "slot_interval_minutes": 30
            },
            headers=auth_headers
        )
        
        assert response_service_only.status_code == 200
        assert response_with_addon.status_code == 200
        
        service_only_slots = response_service_only.json()
        with_addon_slots = response_with_addon.json()
        
        # Verify that blocked times are not in available slots
        blocked_times = [
            datetime.combine(target_date, time(10, 0), tzinfo=timezone.utc).isoformat(),
            datetime.combine(target_date, time(12, 0), tzinfo=timezone.utc).isoformat(),
            datetime.combine(target_date, time(14, 0), tzinfo=timezone.utc).isoformat(),
            datetime.combine(target_date, time(15, 30), tzinfo=timezone.utc).isoformat(),
        ]
        
        for blocked_time in blocked_times:
            assert blocked_time not in service_only_slots
            assert blocked_time not in with_addon_slots
        
        # Service + addon should have fewer available slots due to longer duration
        assert len(with_addon_slots) <= len(service_only_slots)
    
    def test_get_available_timeslots_edge_cases(self, client, auth_headers, test_barber, test_service, test_barber_service, test_barber_schedule):
        """Test edge cases for timeslot availability"""
        target_date = date(2024, 1, 1)  # Monday
        
        # Test with very short working hours
        short_schedule = TestBarberSchedule(
            barber_id=test_barber.id,
            day_of_week=0,
            start_time="14:00:00",  # 2 PM
            end_time="15:00:00"     # 3 PM
        )
        
        # Update the schedule
        from .test_database import TestingSessionLocal
        db = TestingSessionLocal()
        db.query(TestBarberSchedule).filter(
            TestBarberSchedule.barber_id == test_barber.id,
            TestBarberSchedule.day_of_week == 0
        ).delete()
        db.add(short_schedule)
        db.commit()
        db.close()
        
        response = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [],
                "slot_interval_minutes": 30
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        timeslots = response.json()
        
        # With only 1 hour working time and 30-minute service, should have limited slots
        assert len(timeslots) <= 2  # Maximum 2 slots in 1 hour with 30-min service
        
        # Verify all slots are within working hours
        for slot in timeslots:
            slot_dt = datetime.fromisoformat(slot.replace('Z', '+00:00'))
            assert slot_dt.hour >= 14 and slot_dt.hour < 15
    
    def test_get_available_timeslots_multiple_addons(self, client, auth_headers, test_barber, test_service, test_barber_service, test_barber_schedule):
        """Test available timeslots with multiple addons"""
        target_date = date(2024, 1, 1)  # Monday
        
        # Create additional addons
        addon1 = TestAddon(name="Hair Wash", duration=15, price=500)
        addon2 = TestAddon(name="Hair Styling", duration=20, price=800)
        addon3 = TestAddon(name="Beard Trim", duration=10, price=300)
        
        from .test_database import TestingSessionLocal
        db = TestingSessionLocal()
        db.add_all([addon1, addon2, addon3])
        db.commit()
        db.refresh(addon1)
        db.refresh(addon2)
        db.refresh(addon3)
        
        # Store the IDs before closing the session
        addon1_id = addon1.id
        addon2_id = addon2.id
        addon3_id = addon3.id
        db.close()
        
        # Test with different combinations of addons
        response_no_addons = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [],
                "slot_interval_minutes": 30
            },
            headers=auth_headers
        )
        
        response_one_addon = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [addon1_id],
                "slot_interval_minutes": 30
            },
            headers=auth_headers
        )
        
        response_three_addons = client.get(
            "/api/timeslots/available",
            params={
                "barber_id": test_barber.id,
                "target_date": target_date.isoformat(),
                "service_id": test_service.id,
                "addons": [addon1_id, addon2_id, addon3_id],
                "slot_interval_minutes": 30
            },
            headers=auth_headers
        )
        
        assert response_no_addons.status_code == 200
        assert response_one_addon.status_code == 200
        assert response_three_addons.status_code == 200
        
        no_addons_slots = response_no_addons.json()
        one_addon_slots = response_one_addon.json()
        three_addons_slots = response_three_addons.json()
        
        # More addons should result in fewer available slots due to longer duration
        assert len(no_addons_slots) >= len(one_addon_slots) >= len(three_addons_slots)
        
        # Verify that with 3 addons (30 + 15 + 20 + 10 = 75 min), slots are properly calculated
        # This should significantly reduce available slots compared to service only (30 min)
        assert len(three_addons_slots) < len(no_addons_slots)
