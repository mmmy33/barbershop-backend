# Barbershop Backend API

This is the FastAPI backend for the Barbershop project. It handles user authentication, appointment booking, and management of services and barbers.

## 🔧 Tech Stack
- FastAPI
- PostgreSQL
- Alembic (migrations)
- Docker / Docker Compose
- JWT authentication

## 🧑‍💻 Setup Instructions for Frontend Developer

### 1. Clone Backend Repository

```bash
git clone https://github.com/YOUR_BACKEND_REPO_URL
cd barbershop-backend
git checkout develop
⚠️ Note: All development is currently in the `develop` branch.
```

### 2. Install Python Dependencies

Make sure you have Python 3.11+ and [Poetry](https://python-poetry.org/docs/) or `pip` set up. Then:

```bash
python -m venv .venv
source .venv/Scripts/activate # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the root:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/barbershop
SECRET_KEY=your_secret_key_here
MAIL_USERNAME_ENV=your_email@gmail.com
MAIL_APP_PASSWORD=your_secure_password_here
```

### 4. Run Database in Docker

Make sure Docker is running. Then run:

```bash
docker-compose up -d
```

This will start a PostgreSQL instance on port `5433`.

### 5. Run Migrations

```bash
alembic upgrade head
```

### 6.  **Create an Admin User**

    To manage barbers, services, and schedules, you'll need an admin user. Run this script to create one via the terminal:

    ```bash
    python create_admin.py
    ```
    Follow the prompts to enter the admin's email, name, phone number (optional), and password. This user will have the `admin` role required for management endpoints.

### 7.  **Seed Initial Data**

    You can populate your database with some initial barbers, services, and addons for testing purposes.

    ```bash
    python seed.py
    ```


### 8. Run the Backend Server

```bash
uvicorn src.app.main:app --reload
```

### 9. API Docs

Open your browser and go to:

```
http://127.0.0.1:8000/docs
```

## 🔌 Connecting Frontend to Backend

Update your API base URL in frontend (Vite config or `.env`):

```
VITE_API_URL=http://127.0.0.1:8000/api
```

⚠️ **Important**: Backend supports CORS with all origins during development (`*`). So you don’t need to worry about CORS errors now.

## 🛠 Endpoints Available

## Appointments

- `POST /api/appointments/` – create appointment
- `GET /api/appointments/barber/{barber_id}` – list by barber
- `DELETE /api/appointments/{appointment_id}` – delete appointment

## Barbers
- `GET /api/barbers/` – list barbers
- `POST   /api/barbers/` – create barber
- `GET /api/barbers/{barber_id}` – get barber by id
- `PUT /api/barbers/{barber_id}` – update barber
- `DELETE /api/barbers/{barber_id}` – delete barber

💼 Services

- `GET /api/services/` – list services
- `POST /api/services/` – create service
- `GET /api/services/{service_id}` – get service by id
- `PUT /api/services/{service_id}` – update service
- `DELETE /api/services/{service_id}` – delete service

## ✅ Swagger Docs

Interactive docs available at:  
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## 🧪 Testing

This project includes comprehensive test coverage for all endpoints and functionality.

### Test Structure

The tests are organized in the `tests/` directory and cover:

- **Authentication** (`test_auth.py`) - User registration, login, email verification, password reset
- **Appointments** (`test_appointments.py`) - Appointment creation, management, and validation
- **Barbers** (`test_barbers.py`) - Barber CRUD operations and management
- **Services** (`test_services.py`) - Service management and validation
- **Addons** (`test_addons.py`) - Addon management and pricing
- **Barber Schedules** (`test_barber_schedules.py`) - Schedule management and availability
- **Timeslots** (`test_timeslots.py`) - Available time slot generation and validation
- **Integration Workflows** (`test_integration_workflows.py`) - End-to-end user workflows
- **Database** (`test_database.py`) - Database connection and session management

### Running Tests

#### Prerequisites
Make sure you have the test dependencies installed:
```bash
pip install -r requirements.txt
```

#### Quick Test Commands

**Run all tests:**
```bash
pytest tests/ -v
```

**Run with coverage report:**
```bash
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

**Run specific test categories:**
```bash
# Authentication tests only
pytest tests/test_auth.py -v

# Appointments tests only
pytest tests/test_appointments.py -v

# Barbers tests only
pytest tests/test_barbers.py -v

# Services tests only
pytest tests/test_services.py -v
```

**Run tests by markers:**
```bash
# Run only unit tests
pytest tests/ -m "unit" -v

# Run only integration tests
pytest tests/ -m "integration" -v

# Skip slow tests
pytest tests/ -m "not slow" -v
```

#### Using the Test Runner Script

For convenience, you can use the provided test runner script:

```bash
# Run all tests
python run_tests.py

# Run authentication tests only
python run_tests.py --type auth

# Run with coverage report
python run_tests.py --coverage

# Run with HTML coverage report
python run_tests.py --html

# Run specific test categories
python run_tests.py --type register
python run_tests.py --type login
python run_tests.py --type admin
```

### Test Configuration

The project uses `pytest` with the following configuration (`pytest.ini`):
- Test discovery in `tests/` directory
- Coverage reporting for `src/` directory
- HTML coverage reports
- Custom markers for test categorization
- Verbose output by default

### Test Database

Tests use SQLite in-memory database for:
- Fast execution
- Complete isolation between tests
- No external database dependencies
- Automatic cleanup after each test

### Coverage Report

After running tests with coverage, view the HTML report:
```bash
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html in your browser
```

### Test Categories

#### Unit Tests
- Individual function and endpoint testing
- Mocked dependencies
- Fast execution
- Focused on specific functionality

#### Integration Tests
- End-to-end workflow testing
- Real database interactions
- Complete user scenarios
- Cross-module functionality

#### Security Tests
- JWT token validation
- Authentication and authorization
- Input validation and sanitization
- SQL injection prevention

### Continuous Integration

The test suite is designed for CI/CD pipelines:
- No external dependencies
- Deterministic results
- Comprehensive coverage
- Clear pass/fail reporting

For detailed test documentation, see [tests/README.md](tests/README.md).
