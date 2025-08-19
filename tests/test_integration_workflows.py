import pytest
import os
import sys
from datetime import datetime, timedelta, date, time, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import existing test infrastructure
from .test_database import (
    TestBase, engine, TestingSessionLocal, TestUser, TestBarber, TestService, 
    TestAddon, TestBarberService, TestBarberSchedule, TestBarberUnavailableTime,
    TestAppointment, TestAppointmentAddon, TestBarberAddon, override_get_db_with_test_user, 
    create_test_tables, drop_test_tables, get_test_current_user, TestDatabaseSession,
    create_test_admin_required, create_test_barber_required
)

# Import app components
from app.database import get_db
from app.auth.security import create_access_token, hash_password
from app.auth.dependencies import get_current_user, admin_required, barber_required
from app.main import app

# Override dependencies
app.dependency_overrides[get_db] = override_get_db_with_test_user


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    create_test_tables()
    session = TestingSessionLocal()
    
    # Setup authentication overrides
    test_db = TestDatabaseSession(session)
    app.dependency_overrides[get_current_user] = get_test_current_user(test_db)
    app.dependency_overrides[admin_required] = create_test_admin_required(test_db)
    app.dependency_overrides[barber_required] = create_test_barber_required(test_db)
    
    yield session
    session.close()
    drop_test_tables()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_user(db_session):
    """Create an admin user"""
    admin = TestUser(
        name="Admin User",
        email="admin@example.com",
        hashed_password=hash_password("AdminPassword123!"),
        phone_number="+1234567890",
        is_verified=True,
        role="admin"
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def regular_user(db_session):
    """Create a regular user"""
    user = TestUser(
        name="Regular User",
        email="user@example.com",
        hashed_password=hash_password("UserPassword123!"),
        phone_number="+1234567892",
        is_verified=True,
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def barber_user(db_session):
    """Create a barber user"""
    barber = TestUser(
        name="Barber User",
        email="barber@example.com",
        hashed_password=hash_password("BarberPassword123!"),
        phone_number="+1234567891",
        is_verified=True,
        role="barber"
    )
    db_session.add(barber)
    db_session.commit()
    db_session.refresh(barber)
    return barber


@pytest.fixture
def test_service(db_session):
    """Create a test service"""
    service = TestService(name="Haircut", price=2500)
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)
    return service


@pytest.fixture
def test_addon(db_session):
    """Create a test addon"""
    addon = TestAddon(name="Hair Wash", duration=15, price=500)
    db_session.add(addon)
    db_session.commit()
    db_session.refresh(addon)
    return addon


@pytest.fixture
def test_barber(db_session, barber_user):
    """Create a test barber"""
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
def test_barber_schedule(db_session, test_barber):
    """Create a barber schedule"""
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
def test_barber_service(db_session, test_barber, test_service):
    """Create a barber-service relationship"""
    barber_service = TestBarberService(
        barber_id=test_barber.id,
        service_id=test_service.id,
        duration=30
    )
    db_session.add(barber_service)
    db_session.commit()
    return barber_service


class TestUserRegistrationWorkflow:
    """Test user registration workflow"""
    
    @patch('app.services.email_service.AsyncEmailSender')
    def test_user_registration_to_appointment_booking(self, mock_email_sender, client, db_session, 
                                                     test_barber, test_service, test_addon, 
                                                     test_barber_service, test_barber_schedule):
        """Test: registration → email verification → login → book appointment"""
        
        # Mock email service
        mock_email_sender.return_value.__aenter__ = AsyncMock()
        mock_email_sender.return_value.__aexit__ = AsyncMock()
        
        # Step 1: User Registration
        registration_data = {
            "name": "New User",
            "email": "newuser@example.com",
            "password": "NewUserPassword123!",
            "phone_number": "+1234567899"
        }
        
        response = client.post("/api/auth/register", json=registration_data)
        assert response.status_code == 201
        
        # Verify user was created
        user = db_session.query(TestUser).filter(TestUser.email == "newuser@example.com").first()
        assert user is not None
        assert user.is_verified == False
        assert user.verification_code is not None
        
        # Step 2: Email Verification
        verification_code = user.verification_code
        response = client.post(f"/api/auth/verify-email?email=newuser@example.com&code={verification_code}")
        assert response.status_code == 200
        
        # Step 3: User Login
        login_data = {
            "email": "newuser@example.com",
            "password": "NewUserPassword123!"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        token_data = response.json()
        auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        
        # Step 4: Get available timeslots
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
        assert len(timeslots) > 0
        
        # Step 5: Book appointment
        appointment_data = {
            "name": "New User",
            "phoneNumber": "+1234567899",
            "barberId": test_barber.id,
            "serviceId": test_service.id,
            "addonIds": [test_addon.id],
            "scheduled_time": timeslots[0]
        }
        
        response = client.post("/api/appointments/", json=appointment_data, headers=auth_headers)
        assert response.status_code == 201
        
        appointment = response.json()
        assert appointment["name"] == "New User"
        assert appointment["barber_id"] == test_barber.id
        assert len(appointment["addons"]) == 1


class TestAdminBarberCreationWorkflow:
    """Test admin barber creation workflow"""
    
    def test_admin_creates_barber_and_assigns_services(self, client, admin_user, test_service, test_addon):
        """Test: admin creates barber → assigns services → user books"""
        
        # Create auth headers for admin
        admin_token = create_access_token(user_id=admin_user.id)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Step 1: Create a user that will become a barber
        barber_user = TestUser(
            name="John the Barber",
            email="john@example.com",
            hashed_password=hash_password("JohnPassword123!"),
            phone_number="+1234567893",
            is_verified=True,
            role="user"
        )
        db_session = TestingSessionLocal()
        db_session.add(barber_user)
        db_session.commit()
        db_session.refresh(barber_user)
        db_session.close()
        
        # Step 2: Admin creates barber (converts user to barber)
        barber_data = {
            "name": "John the Barber",
            "avatar_url": "https://example.com/john.jpg",
            "email": "john@example.com"
        }
        
        response = client.post("/api/barbers/", json=barber_data, headers=admin_headers)
        assert response.status_code == 200
        
        barber = response.json()
        barber_id = barber["id"]
        
        # Step 3: Admin assigns services
        service_assignment = {
            "services": [{"service_id": test_service.id, "duration": 30}]
        }
        
        response = client.post(f"/api/barbers/{barber_id}/service", json=service_assignment, headers=admin_headers)
        assert response.status_code == 200
        
        # Step 4: Admin assigns addons
        addon_assignment = {"addon_ids": [test_addon.id]}
        response = client.post(f"/api/barbers/{barber_id}/addon", json=addon_assignment, headers=admin_headers)
        assert response.status_code == 200
        
        # Step 5: Admin creates schedule
        schedule_data = {
            "day_of_week": 0,
            "start_time": "09:00:00",
            "end_time": "17:00:00"
        }
        
        response = client.post(f"/api/barbers/{barber_id}/schedules/", json=schedule_data, headers=admin_headers)
        assert response.status_code == 201


class TestBarberScheduleConflictWorkflow:
    """Test barber schedule conflicts"""
    
    def test_barber_schedule_conflicts_with_appointments(self, client, regular_user, test_barber, 
                                                        test_service, test_barber_service, test_barber_schedule):
        """Test that scheduling conflicts are properly handled"""
        
        # Create auth headers for regular user
        user_token = create_access_token(user_id=regular_user.id)
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Step 1: Create an existing appointment
        target_date = date(2024, 1, 1)  # Monday
        existing_time = datetime.combine(target_date, time(10, 0), tzinfo=timezone.utc)
        
        existing_appointment = TestAppointment(
            name="Existing Customer",
            phone_number="+1234567894",
            barber_id=test_barber.id,
            service_id=test_service.id,
            total_duration=30,
            total_price=2500,
            user_id=regular_user.id,
            scheduled_time=existing_time,
            created_at=datetime.now(timezone.utc)
        )
        db_session = TestingSessionLocal()
        db_session.add(existing_appointment)
        db_session.commit()
        db_session.close()
        
        # Step 2: Try to book overlapping appointment
        conflicting_time = datetime.combine(target_date, time(10, 15), tzinfo=timezone.utc)
        
        appointment_data = {
            "name": "Conflicting Customer",
            "phoneNumber": "+1234567895",
            "barberId": test_barber.id,
            "serviceId": test_service.id,
            "addonIds": [],
            "scheduled_time": conflicting_time.isoformat()
        }
        
        response = client.post("/api/appointments/", json=appointment_data, headers=user_headers)
        assert response.status_code == 400  # Should fail due to conflict
        
        # Step 3: Try to book non-overlapping appointment
        non_conflicting_time = datetime.combine(target_date, time(11, 0), tzinfo=timezone.utc)
        
        appointment_data = {
            "name": "Non-Conflicting Customer",
            "phoneNumber": "+1234567896",
            "barberId": test_barber.id,
            "serviceId": test_service.id,
            "addonIds": [],
            "scheduled_time": non_conflicting_time.isoformat()
        }
        
        response = client.post("/api/appointments/", json=appointment_data, headers=user_headers)
        assert response.status_code == 201


class TestAppointmentBookingWithMultipleAddons:
    """Test appointment booking with multiple addons"""
    
    def test_appointment_booking_with_multiple_addons(self, client, regular_user, test_barber, 
                                                     test_service, test_addon, test_barber_service, test_barber_schedule):
        """Test appointment booking with addons and verify calculations"""
        
        # Create auth headers
        user_token = create_access_token(user_id=regular_user.id)
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Get available timeslots
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
            headers=user_headers
        )
        
        assert response.status_code == 200
        timeslots = response.json()
        assert len(timeslots) > 0
        
        # Book appointment with addon
        appointment_data = {
            "name": "Multiple Addons Customer",
            "phoneNumber": "+1234567898",
            "barberId": test_barber.id,
            "serviceId": test_service.id,
            "addonIds": [test_addon.id],
            "scheduled_time": timeslots[0]
        }
        
        response = client.post("/api/appointments/", json=appointment_data, headers=user_headers)
        assert response.status_code == 201
        
        appointment = response.json()
        
        # Verify appointment details
        assert appointment["name"] == "Multiple Addons Customer"
        assert appointment["barber_id"] == test_barber.id
        assert len(appointment["addons"]) == 1
        assert appointment["addons"][0]["id"] == test_addon.id
        
        # Verify pricing calculation
        expected_total_price = 2500 + 500  # Service + Addon
        assert appointment["total_price"] == expected_total_price
        
        # Verify duration calculation
        expected_total_duration = 30 + 15  # Service + Addon
        assert appointment["total_duration"] == expected_total_duration


class TestCrossEndpointBusinessRules:
    """Test cross-endpoint business rules"""
    
    def test_user_cannot_access_admin_endpoints(self, client, regular_user, test_barber):
        """Test that regular users cannot access admin endpoints"""
        
        # Create auth headers for regular user
        user_token = create_access_token(user_id=regular_user.id)
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Try to create a barber (admin only)
        barber_data = {
            "name": "Unauthorized Barber",
            "avatar_url": "https://example.com/unauthorized.jpg",
            "email": "unauthorized@example.com"
        }
        
        response = client.post("/api/barbers/", json=barber_data, headers=user_headers)
        assert response.status_code == 403  # Forbidden
    
    def test_admin_can_manage_barbers(self, client, admin_user, test_barber, test_service):
        """Test that admin can manage barbers"""
        
        # Create auth headers for admin
        admin_token = create_access_token(user_id=admin_user.id)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Admin can view all barbers
        response = client.get("/api/barbers/", headers=admin_headers)
        assert response.status_code == 200
        barbers = response.json()
        assert len(barbers) >= 1
        
        # Admin can update barber
        update_data = {
            "name": "Updated Barber Name",
            "avatar_url": "https://example.com/updated.jpg"
        }
        
        response = client.put(f"/api/barbers/{test_barber.id}", json=update_data, headers=admin_headers)
        assert response.status_code == 200
        
        updated_barber = response.json()
        assert updated_barber["name"] == "Updated Barber Name"
    
    def test_appointment_cancellation(self, client, regular_user, test_barber, test_service, 
                                     test_barber_service, test_barber_schedule):
        """Test appointment cancellation workflow"""
        
        # Create auth headers
        user_token = create_access_token(user_id=regular_user.id)
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Get available timeslots
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
            headers=user_headers
        )
        
        assert response.status_code == 200
        timeslots = response.json()
        
        # Book appointment
        appointment_data = {
            "name": "Cancel Customer",
            "phoneNumber": "+1234567900",
            "barberId": test_barber.id,
            "serviceId": test_service.id,
            "addonIds": [],
            "scheduled_time": timeslots[0]
        }
        
        response = client.post("/api/appointments/", json=appointment_data, headers=user_headers)
        assert response.status_code == 201
        
        appointment = response.json()
        appointment_id = appointment["id"]
        
        # Cancel appointment
        response = client.delete(f"/api/appointments/{appointment_id}", headers=user_headers)
        assert response.status_code == 204
        
        # Verify appointment is cancelled
        response = client.get("/api/appointments/me", headers=user_headers)
        assert response.status_code == 200
        
        user_appointments = response.json()
        assert len(user_appointments["upcoming"]) == 0
