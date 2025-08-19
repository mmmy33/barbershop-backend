"""
Test database setup module to avoid SQLAlchemy table redefinition issues.
"""
import os
import sys
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set up test environment variables
os.environ.update({
    "SECRET_KEY": "test-secret-key-for-testing-only",
    "DATABASE_URL": "sqlite:///./test.db",
    "MAIL_USERNAME": "test@example.com",
    "MAIL_PASSWORD": "test-password",
    "MAIL_FROM": "test@example.com",
    "MAIL_PORT": "587",
    "MAIL_SERVER": "smtp.gmail.com",
    "MAIL_TLS": "True",
    "MAIL_SSL": "False"
})

# Create a separate Base for tests
TestBase = declarative_base()
TestBase.__test__ = False  # Prevent pytest from collecting this as a test

# Test database setup - use file-based database to avoid threading issues
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override the database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def create_test_tables():
    """Create all test tables"""
    TestBase.metadata.create_all(bind=engine)


def drop_test_tables():
    """Drop all test tables"""
    TestBase.metadata.drop_all(bind=engine)


# Import and define test models after setting up the base
class TestUser(TestBase):
    """Test User model to avoid conflicts with the main User model"""
    __tablename__ = "users"
    __test__ = False  # Prevent pytest from collecting this as a test

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone_number = Column(String, unique=True, nullable=True)
    hashed_password = Column(String(255))
    role = Column(String, default="user")
    is_verified = Column(Boolean, default=False)
    verification_code = Column(String(6), nullable=True)
    verification_code_expires = Column(DateTime, nullable=True)
    password_reset_jti = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)


class TestService(TestBase):
    """Test Service model to avoid conflicts with the main Service model"""
    __tablename__ = "services"
    __test__ = False

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)


class TestBarber(TestBase):
    """Test Barber model to avoid conflicts with the main Barber model"""
    __tablename__ = "barbers"
    __test__ = False

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    user_id = Column(Integer, nullable=False)


class TestBarberService(TestBase):
    """Test BarberService model to avoid conflicts with the main BarberService model"""
    __tablename__ = "barber_service"
    __test__ = False

    barber_id = Column(Integer, primary_key=True)
    service_id = Column(Integer, primary_key=True)
    duration = Column(Integer, nullable=False)


class TestAppointment(TestBase):
    """Test Appointment model to avoid conflicts with the main Appointment model"""
    __tablename__ = "appointments"
    __test__ = False

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    barber_id = Column(Integer, nullable=False)
    service_id = Column(Integer, nullable=False)
    total_duration = Column(Integer, nullable=False)
    total_price = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=True)
    scheduled_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), server_default=func.now())


class TestAddon(TestBase):
    """Test Addon model to avoid conflicts with the main Addon model"""
    __tablename__ = "addons"
    __test__ = False

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)


class TestAppointmentAddon(TestBase):
    """Test AppointmentAddon model to avoid conflicts with the main AppointmentAddon model"""
    __tablename__ = "appointment_addon"
    __test__ = False

    appointment_id = Column(Integer, primary_key=True)
    addon_id = Column(Integer, primary_key=True)


class TestBarberSchedule(TestBase):
    """Test BarberSchedule model to avoid conflicts with the main BarberSchedule model"""
    __tablename__ = "barber_schedules"
    __test__ = False

    id = Column(Integer, primary_key=True, index=True)
    barber_id = Column(Integer, nullable=False)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)


class TestBarberAddon(TestBase):
    """Test BarberAddon relationship model to avoid conflicts with the main BarberAddon model"""
    __tablename__ = "barber_addon"
    __test__ = False

    barber_id = Column(Integer, primary_key=True)
    addon_id = Column(Integer, primary_key=True)


class TestBarberUnavailableTime(TestBase):
    """Test BarberUnavailableTime model to avoid conflicts with the main BarberUnavailableTime model"""
    __tablename__ = "barber_unavailable_times"
    __test__ = False

    id = Column(Integer, primary_key=True, index=True)
    barber_id = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    reason = Column(String, nullable=True)


# Create a custom session that maps the main models to test models
class TestDatabaseSession:
    """Custom database session that maps main models to test models"""
    __test__ = False  # Prevent pytest from collecting this as a test
    
    def __init__(self, session):
        self.session = session
        # Map the main models to test models
        self.User = TestUser
        self.Service = TestService
        self.Barber = TestBarber
        self.BarberService = TestBarberService
        self.Appointment = TestAppointment
        self.Addon = TestAddon
        self.AppointmentAddon = TestAppointmentAddon
        self.BarberSchedule = TestBarberSchedule
        self.BarberAddon = TestBarberAddon
        self.BarberUnavailableTime = TestBarberUnavailableTime
    
    def query(self, model):
        """Override query to use test models instead of main models"""
        model_name = model.__name__ if hasattr(model, '__name__') else str(model)
        
        if model_name == 'User':
            return self.session.query(TestUser)
        elif model_name == 'Service':
            return self.session.query(TestService)
        elif model_name == 'Barber':
            return self.session.query(TestBarber)
        elif model_name == 'BarberService':
            return self.session.query(TestBarberService)
        elif model_name == 'Appointment':
            return self.session.query(TestAppointment)
        elif model_name == 'Addon':
            return self.session.query(TestAddon)
        elif model_name == 'AppointmentAddon':
            return self.session.query(TestAppointmentAddon)
        elif model_name == 'BarberSchedule':
            return self.session.query(TestBarberSchedule)
        elif model_name == 'BarberAddon':
            return self.session.query(TestBarberAddon)
        elif model_name == 'BarberUnavailableTime':
            return self.session.query(TestBarberUnavailableTime)
        
        # Handle string model names
        if isinstance(model, str):
            if model == 'User':
                return self.session.query(TestUser)
            elif model == 'Service':
                return self.session.query(TestService)
            elif model == 'Barber':
                return self.session.query(TestBarber)
            elif model == 'BarberService':
                return self.session.query(TestBarberService)
            elif model == 'Appointment':
                return self.session.query(TestAppointment)
            elif model == 'Addon':
                return self.session.query(TestAddon)
            elif model == 'AppointmentAddon':
                return self.session.query(TestAppointmentAddon)
            elif model == 'BarberSchedule':
                return self.session.query(TestBarberSchedule)
            elif model == 'BarberAddon':
                return self.session.query(TestBarberAddon)
            elif model == 'BarberUnavailableTime':
                return self.session.query(TestBarberUnavailableTime)
        
        return self.session.query(model)
    
    def add(self, obj):
        """Add object to session"""
        return self.session.add(obj)
    
    def commit(self):
        """Commit session"""
        return self.session.commit()
    
    def refresh(self, obj):
        """Refresh object"""
        return self.session.refresh(obj)
    
    def close(self):
        """Close session"""
        return self.session.close()
    
    def get(self, model, id):
        """Get object by id, mapping to test models"""
        model_name = model.__name__ if hasattr(model, '__name__') else str(model)
        
        if model_name == 'User':
            return self.session.query(TestUser).filter(TestUser.id == id).first()
        elif model_name == 'Service':
            return self.session.query(TestService).filter(TestService.id == id).first()
        elif model_name == 'Barber':
            return self.session.query(TestBarber).filter(TestBarber.id == id).first()
        elif model_name == 'BarberService':
            return self.session.query(TestBarberService).filter(TestBarberService.barber_id == id).first()
        elif model_name == 'Appointment':
            return self.session.query(TestAppointment).filter(TestAppointment.id == id).first()
        elif model_name == 'Addon':
            return self.session.query(TestAddon).filter(TestAddon.id == id).first()
        elif model_name == 'AppointmentAddon':
            return self.session.query(TestAppointmentAddon).filter(TestAppointmentAddon.appointment_id == id).first()
        elif model_name == 'BarberSchedule':
            return self.session.query(TestBarberSchedule).filter(TestBarberSchedule.id == id).first()
        elif model_name == 'BarberAddon':
            return self.session.query(TestBarberAddon).filter(TestBarberAddon.barber_id == id).first()
        elif model_name == 'BarberUnavailableTime':
            return self.session.query(TestBarberUnavailableTime).filter(TestBarberUnavailableTime.id == id).first()
        
        return self.session.query(model).filter(model.id == id).first()
    
    def __getattr__(self, name):
        """Delegate all other attributes to the underlying session"""
        return getattr(self.session, name)


def override_get_db_with_test_user():
    """Override the database dependency for testing with User model mapping"""
    try:
        db = TestingSessionLocal()
        test_db = TestDatabaseSession(db)
        yield test_db
    finally:
        db.close()


# Test-specific authentication dependencies
def get_test_current_user(db):
    """Test version of get_current_user that works with TestUser"""
    from fastapi import Depends, HTTPException, status
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
    from jose import jwt, JWTError
    
    def _get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
    ) -> TestUser:
        token = credentials.credentials
        
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(token, os.environ.get("SECRET_KEY"), algorithms=["HS256"])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = db.query(TestUser).filter(TestUser.id == int(user_id)).first()
        if user is None:
            raise credentials_exception

        return user
    
    return _get_current_user


def create_test_admin_required(db):
    """Test version of admin_required that works with TestUser"""
    from fastapi import Depends, HTTPException, status
    
    def _admin_required(current_user: TestUser = Depends(get_test_current_user(db))) -> TestUser:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return current_user
    
    return _admin_required


def create_test_barber_required(db):
    """Test version of barber_required that works with TestUser"""
    from fastapi import Depends, HTTPException, status
    
    def _barber_required(current_user: TestUser = Depends(get_test_current_user(db))) -> TestUser:
        if current_user.role != "barber":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return current_user
    
    return _barber_required
