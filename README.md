# Neuro Blooms Backend

The secure, high-performance backend system for the **Neuro Blooms Healthcare Management System**, designed as a maintainable, robust Django monolith.

This backend serves the admin console, doctor portal, and receptionist interfaces, providing secure session handling, dynamic two-factor authentication, fine-grained Role-Based Access Control (RBAC), and a comprehensive security auditing ledger.

---

## Key Features

- **Standardized REST API**: Standardized JSON envelope structures with robust error mapping, pagination, and unified query filtering across all resource collections.
- **Dynamic Two-Factor Authentication (2FA)**: Password login backed by custom One-Time Password (OTP) verification flows sent for security actions.
- **Active Session Tracking & Revocation**: Monitors active user logins with IP addresses, browser agents, and device signatures. Provides immediate, remote session revocation hooks.
- **Role-Based Access Control (RBAC)**: Secure permission classes separating access scopes for `ADMIN`, `DOCTOR`, and `RECEPTIONIST` roles, enforcing group-level data isolation.
- **Security Audit Ledger (Security Center)**: Complete activity logs tracking login attempts, lockouts, administrative unlocks, and system changes, fully searchable and paginated.
- **Media Asset Management**: Secure user avatar uploads, media file paths, and local media serving configurations.

---

## Technology Stack

- **Framework**: Django 5+
- **API Engine**: Django REST Framework (DRF)
- **Database**: PostgreSQL (Production) / SQLite (Local fallback)
- **Authentication**: JWT (JSON Web Tokens) with custom stateless refresh/rotation handlers
- **Testing**: Django Unit Tests with pre-seeded fixtures

---

## Directory Structure

```text
apps/
└── accounts/
    ├── api/
    │   ├── views/          # Endpoint controllers (Auth, Sessions, Activity logs)
    │   ├── serializers/    # Data serialization and validation schemas
    │   ├── urls.py         # Route definitions and versioning mapping
    │   └── pagination.py   # Page-number and cursor pagination overrides
    ├── models/             # Database schemas (User, Session, ActivityLog, OTP)
    ├── permissions/        # RBAC security classes (IsAdmin, IsDoctor)
    └── tests.py            # Comprehensive test suite
config/                     # Django project configuration, settings, and URL configurations
docs/                       # Detailed API specifications and developer guides
manage.py                   # Django CLI management entrypoint
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- PostgreSQL (optional, fallback to SQLite is automated)

### Installation Steps

1. **Clone the Repository:**
   ```bash
   git clone <repository_url>
   cd neuro-blooms-backend
   ```

2. **Set up a Virtual Environment:**
   ```bash
   python -m venv .venv
   ```

3. **Activate the Virtual Environment:**
   - **Windows (Command Prompt):**
     ```cmd
     .venv\Scripts\activate.bat
     ```
   - **Windows (PowerShell):**
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **macOS/Linux:**
     ```bash
     source .venv/bin/activate
     ```

4. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure Environment Variables:**
   Copy the example environment template and configure your secrets:
   ```bash
   cp .env.example .env
   ```

---

## Database & Server Operations

### Database Migrations
Generate and apply database schema updates:
```bash
python manage.py makemigrations
python manage.py migrate
```

### Running the Development Server
Start the local server:
```bash
python manage.py runserver
```
The API will be accessible at `http://127.0.0.1:8000/`. The interactive API documentation or base endpoints are versioned under `/api/v1/`.

---

## Testing

The backend includes a comprehensive test suite covering authentication, token rotations, OTP logic, session revocation, and security ledger filtering.

Run the test suite using:
```bash
python manage.py test
```
All tests are configured to run within an isolated test database.
