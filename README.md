# StudyOS

**An academic planning system that helps students organize coursework, plan study time, and recover when they fall behind.**

StudyOS is a full-stack web application for managing academic responsibilities. Its central feature is an explainable study planner that allocates available study time to unfinished tasks, accounts for deadlines and priorities, and identifies work that cannot fit within the available capacity.

When planned study sessions are missed, students can replan their remaining work while retaining a record of previous sessions.

**Project status:** Functional local MVP. Not yet deployed.

## Key Features

- **Personalized Dashboard** — Track upcoming deadlines, overdue work, exams, completion statistics, and study activity.
- **Subject Management** — Organize academic work by subject and view related tasks, exams, and study sessions.
- **Task Management** — Create and manage assignments with priorities, time estimates, due dates, status tracking, filtering, sorting, and pagination.
- **Exam Tracking** — Record exams, topics, and importance to help prioritize preparation.
- **Study Session Management** — Track planned, completed, and missed sessions, including actual study time.
- **Explainable Study Planner** — Generate a ranked study plan using task urgency, priority, workload, exam proximity, and available time.
- **Missed-Work Recovery** — Replan unfinished work after missed sessions and identify tasks that cannot fit within the available schedule.
- **Workload and Capacity Analysis** — Compare required study time with available capacity and report unscheduled work.
- **Authentication and Data Isolation** — Support individual accounts, password hashing, server-side sessions, and user-specific data access.
- **Responsive Interface** — Provide loading, empty, error, success, and confirmation states across the application.

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React 18, JavaScript, React Router |
| Build Tool and Development Server | Vite |
| Backend API | Python, FastAPI |
| Validation and Settings | Pydantic, pydantic-settings |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Database Migrations | Alembic |
| Database Driver | Psycopg |
| Authentication | bcrypt password hashing, server-side sessions, HttpOnly cookies |
| Backend Testing | pytest, FastAPI TestClient, HTTPX |
| Frontend Testing | Vitest |

## Architecture

StudyOS uses a client-server architecture with a relational database.

```text
┌─────────────────────────────┐
│      React Frontend         │
│      Vite :5173             │
└──────────────┬──────────────┘
               │ HTTP / JSON
               ▼
┌─────────────────────────────┐
│       Vite API Proxy        │
│       /api/*                │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│       FastAPI Backend       │
│                             │
│  Authentication and Routes  │
│  Application Services       │
│  Validation and Access      │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│       SQLAlchemy ORM        │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│       PostgreSQL            │
└─────────────────────────────┘
```

The frontend communicates with the backend through HTTP endpoints. FastAPI handles request validation, authentication, and application logic. SQLAlchemy manages database access, and Alembic provides versioned database migrations.

During development, Vite proxies `/api` requests to the backend, allowing the browser to communicate through a single origin.

For further technical details, see:

- [Architecture](docs/architecture.md)
- [Database Design](docs/database-design.md)
- [API Guide](docs/api-guide.md)

## How the Planner Works

The planner uses a deterministic, explainable heuristic rather than a machine-learning model or a black-box optimization service.

### 1. Task Prioritization

Tasks are scored using four factors:

- **Urgency:** How close the deadline is, including overdue work.
- **Priority:** The task's low, medium, or high priority.
- **Exam proximity:** The importance and timing of an upcoming exam in the same subject.
- **Workload:** The estimated remaining effort.

The score includes a breakdown so users can understand why tasks are ranked in a particular order.

### 2. Capacity-Aware Scheduling

The planner considers available study minutes for each day and existing planned or completed study activity. It reserves time for higher-ranked tasks while respecting feasible deadlines.

### 3. Review Before Acceptance

Generated recommendations are presented for review before they are saved as study sessions. Users can choose which recommendations to accept.

### 4. Recovery After Missed Sessions

Missed sessions remain in the history. Their unfinished work can be considered again when the planner generates a new schedule.

### 5. Workload Shortfall

When available time is insufficient, the planner reports unscheduled work and the shortfall associated with overdue or approaching deadlines. Work outside the planning horizon can be deferred.

The algorithm is designed to be understandable and predictable, not to guarantee a mathematically optimal schedule.

See [Planner Algorithm](docs/planner-algorithm.md) for the scoring rules, scheduling procedure, worked example, and limitations.

## Database Design

The database contains entities for:

- Users and authentication sessions
- Subjects
- Tasks
- Exams
- Study sessions
- Weekly availability

Foreign keys, constraints, and indexes support relational integrity. User-owned records are associated with the relevant account, and database schema changes are managed through Alembic migrations.

See [Database Design](docs/database-design.md) for the schema details.

## Getting Started

The following instructions describe the local development setup. The application has not been deployed as a hosted service.

### Prerequisites

Install:

- Python 3.11–3.13
- Node.js 20 or newer and npm
- PostgreSQL 15 or newer
- Git

The commands below use Windows PowerShell. On macOS or Linux, activate the Python virtual environment with `source .venv/bin/activate` instead.

### 1. Clone the Repository

```powershell
git clone https://github.com/Ephraim-Immanuel/StudyOS.git
cd StudyOS
```

### 2. Create the PostgreSQL Database

Ensure PostgreSQL is running. Open a PostgreSQL shell as an administrator, for example:

```powershell
psql -U postgres
```

Create a dedicated application user and database. Replace the example password with your own:

```sql
CREATE USER studyos WITH PASSWORD 'choose-a-password';
CREATE DATABASE studyos OWNER studyos;
```

Exit the PostgreSQL shell:

```sql
\q
```

If `psql` is not recognized, use PostgreSQL's SQL Shell or configure the PostgreSQL `bin` directory in your PATH.

### 3. Configure the Backend

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Edit `backend/.env` and configure the database connection:

```dotenv
DATABASE_URL=postgresql+psycopg://studyos:YOUR_PASSWORD@localhost:5432/studyos
```

Replace `YOUR_PASSWORD` with the password you created. If the password contains URL-reserved characters, encode them appropriately in the connection string.

Keep `.env` private. Do not commit database passwords or other secrets.

### 4. Apply Database Migrations

From the `backend` directory, with the virtual environment activated:

```powershell
python -m alembic upgrade head
```

This creates the database schema defined by the project's migration history.

### 5. Start the Backend

```powershell
python -m uvicorn app.main:app --reload
```

Keep this terminal open while using the application.

The backend provides:

- Health check: http://localhost:8000/api/health
- Interactive API documentation: http://localhost:8000/docs
- Alternative API documentation: http://localhost:8000/redoc

The health endpoint should return:

```json
{
  "status": "ok"
}
```

### 6. Start the Frontend

Open a second terminal at the repository root:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173 in your browser.

No frontend `.env` file is required for the default development setup. The Vite configuration proxies `/api` requests to `http://localhost:8000`.

To stop either development server, press `Ctrl+C` in its terminal.

## Testing

### Backend Tests

From the `backend` directory, activate the virtual environment if necessary and run:

```powershell
python -m pytest
```

By default, the tests use an in-memory SQLite database, so a separate PostgreSQL test database is not required for the default test run.

To run the tests against PostgreSQL, create a separate, empty test database and set `TEST_DATABASE_URL` before running pytest. The test fixtures drop and recreate tables, so **never point this variable at a database containing data you need to keep**.

### Frontend Tests

From the `frontend` directory:

```powershell
npm ci
npm test
```

### Production Build Check

From the `frontend` directory:

```powershell
npm run build
```

This checks whether Vite can generate the production frontend bundle. It does not deploy the application.

## Project Structure

```text
StudyOS/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── security.py
│   ├── migrations/
│   │   └── versions/
│   ├── tests/
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── context/
│   │   ├── lib/
│   │   └── pages/
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
├── docs/
│   ├── architecture.md
│   ├── database-design.md
│   ├── api-guide.md
│   ├── planner-algorithm.md
│   ├── learning-guide.md
│   └── interview-and-resume.md
├── .gitignore
└── README.md
```

## Security Considerations

The application includes password hashing, server-side sessions, HttpOnly session cookies, and user-specific access controls. These are useful foundations, but they do not by themselves establish production readiness.

Before deploying to a public environment, additional work is needed around HTTPS, secure cookie configuration, CSRF protections, rate limiting, account recovery, monitoring, and deployment configuration.

Never commit `.env` files, passwords, session tokens, or other secrets. The example environment files are templates, not places to store real credentials.

## Known Limitations

- The application is intended as a local MVP and has not been deployed.
- The planner is a heuristic, not an optimal scheduling solver.
- Scheduling uses calendar-day granularity rather than exact time slots.
- Tasks do not support dependencies, breaks, or minimum and maximum study-block sizes.
- Exam proximity influences task ranking but does not create hard deadlines for every task in a subject.
- Progress is based on task status and recorded study-session activity.
- Frontend tests cover helper logic; comprehensive browser-automation tests are not included.
- Email verification, password reset, rate limiting, and account lockout are not implemented.

## Potential Future Improvements

- Calendar and ICS export
- Recurring tasks and task dependencies
- More flexible scheduling constraints
- Browser-based end-to-end testing
- Continuous integration for automated tests and build checks
- Password recovery and additional account protections
- Deployment with HTTPS, monitoring, and operational safeguards
- Optional AI-assisted features built on top of the existing planning functionality

## License

No license has been specified for this repository. All rights are reserved by default unless a license is added.