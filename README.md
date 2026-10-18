# StudyOS — Academic Planning System

StudyOS is a full-stack academic planning application designed to help students organize coursework, manage deadlines, plan study sessions, and monitor their academic workload in one place.

The application combines a React frontend, a FastAPI backend, and a PostgreSQL database to provide a structured workflow for managing academic responsibilities.

## Features

- **Dashboard:** View an overview of academic tasks, upcoming deadlines, and study activity.
- **Subject Management:** Create and organize subjects and associate academic work with them.
- **Task Management:** Create, track, and manage coursework and assignments.
- **Exam Tracking:** Record exams and keep track of upcoming assessments.
- **Study Sessions:** Organize study activity and record completed sessions.
- **Study Planner:** Generate and manage study schedules based on academic workload and deadlines.
- **Authentication:** Register and sign in to access an individual account.
- **Persistent Storage:** Store application data in PostgreSQL.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, JavaScript, Vite |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Database Migrations | Alembic |
| Database Driver | Psycopg |
| API Documentation | OpenAPI / Swagger UI |
| Testing | Pytest, frontend tests |

## Architecture

StudyOS follows a client-server architecture.

```text
React Frontend
      |
      | HTTP / JSON
      v
FastAPI Backend
      |
      +---- Authentication and API routes
      |
      +---- Application services
      |
      v
SQLAlchemy
      |
      v
PostgreSQL Database
```

The frontend communicates with the backend through HTTP API endpoints. FastAPI handles requests, authentication, validation, and application logic. SQLAlchemy manages database interactions, while Alembic tracks database schema changes.

## Getting Started

### Prerequisites

Install the following before running the application:

- Python 3.13 or another version supported by the project's dependencies
- Node.js and npm
- PostgreSQL
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Ephraim-Immanuel/StudyOS.git
cd StudyOS
```

### 2. Configure the backend

Open a terminal in the project directory:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment.

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```bash
python -m pip install -r requirements.txt
```

Create your local environment file by copying the example.

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

Edit `backend/.env` and configure the database connection using your local PostgreSQL credentials. Use the variable names and settings provided in `.env.example`.

Do not commit your `.env` file or expose database credentials.

### 3. Create the database

Create a PostgreSQL database and database user for StudyOS. Configure the connection string in `backend/.env` to match your local setup.

### 4. Apply database migrations

From the `backend` directory, with the virtual environment activated, run:

```bash
python -m alembic upgrade head
```

### 5. Start the backend

From the `backend` directory, run:

```bash
python -m uvicorn app.main:app --reload
```

The API will be available at:

`http://127.0.0.1:8000`

Interactive API documentation is available at:

`http://127.0.0.1:8000/docs`

### 6. Configure and start the frontend

Open a second terminal:

```bash
cd frontend
npm ci
```

Create a local frontend environment file if required by the configuration:

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

Review `frontend/.env.example` and configure the API URL if your local setup requires it.

Start the development server:

```bash
npm run dev
```

Open the local URL printed by Vite in your terminal.

## Testing

### Backend

From the `backend` directory, with the virtual environment activated:

```bash
python -m pytest
```

### Frontend

From the `frontend` directory:

```bash
npm test
```

The available test scripts and required test dependencies are defined in the project's configuration files. Some tests may require additional database or environment configuration.

## Database Migrations

StudyOS uses Alembic to manage database schema changes.

Apply pending migrations:

```bash
python -m alembic upgrade head
```

Migration files are maintained in `backend/migrations/versions/`.

## Project Structure

```text
StudyOS/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── security.py
│   ├── migrations/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── context/
│   │   └── pages/
│   ├── package.json
│   └── .env.example
├── docs/
├── .gitignore
└── README.md
```

## Security and Configuration

- Keep database credentials and other secrets in local environment files.
- Use `.env.example` files to document required configuration without exposing sensitive values.
- Do not commit passwords, API keys, or production credentials.
- Configure authentication and deployment settings appropriately before using the application in a production environment.

## Current Scope and Future Improvements

Potential areas for further development include:

- More advanced scheduling and workload optimization.
- Improved accessibility and responsive design.
- Additional automated tests and integration coverage.
- Production deployment, monitoring, and operational hardening.
- Enhanced reporting on study habits and academic progress.

## License

No license has been specified yet. All rights remain with the respective copyright holder unless a license is added to this repository.
