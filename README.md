# Neuro Blooms Backend

The backend system for the **Neuro Blooms Healthcare Management System**, built as a simple, maintainable Django monolith.

## Technology Stack

* Django 5+
* Django REST Framework
* PostgreSQL

## Installation Steps

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd neuro-blooms-backend
   ```

2. **Set up a virtual environment:**
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment:**
   * On Windows (Command Prompt):
     ```cmd
     .venv\Scripts\activate.bat
     ```
   * On Windows (PowerShell):
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   * On macOS/Linux:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables:**
   Copy `.env.example` to `.env` and fill in the values:
   ```bash
   cp .env.example .env
   ```

## Database Migration Commands

Create database tables and apply migrations:
```bash
python manage.py migrate
```

## Running the Server

Start the Django development server:
```bash
python manage.py runserver
```
The server will start at `http://127.0.0.1:8000/`.
