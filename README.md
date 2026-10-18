# 📚 StudyOS

**An academic planner that helps students recover when they fall behind.**

StudyOS tracks subjects, assignments, exams and study sessions, and has one defining feature: a transparent **weekly planner** that fits your unfinished work into the study time you actually have, and **re-plans after missed sessions**, telling you honestly when the workload does not fit.

> Status: complete MVP, built as a full-stack learning/portfolio project. Runs locally. It has **not** been deployed anywhere and has no real users.

<!-- After you run the app, add a screenshot and uncomment this line:
![Dashboard screenshot](docs/screenshots/dashboard.png)
-->
*(Screenshots: see the [Screenshots](#screenshots) section. Add your own after running the app.)*

---

## Table of contents
1. [Problem statement](#problem-statement) · 2. [Features](#features) · 3. [Tech stack](#tech-stack-and-why) · 4. [Architecture](#architecture) · 5. [Database](#database-schema) · 6. [Setup: step by step](#setup-step-by-step) · 7. [Using the app](#smoke-test-use-the-app) · 8. [Tests](#running-the-tests) · 9. [Troubleshooting](#troubleshooting) · 10. [Limitations](#known-limitations) · 11. [Future work](#future-improvements) · 12. [GitHub](#publishing-to-github)

## Problem statement
Generic to-do apps list tasks. They do not answer the question students actually have after a bad week: *"I'm behind. What should I do **now**, and is it even possible to catch up?"* StudyOS answers it with a deterministic, explainable algorithm instead of a black box.

## Features
| Area | What it does |
|---|---|
| Accounts | Register, log in/out, server-side sessions in an HttpOnly cookie, bcrypt password hashing, every row owned by one user |
| Subjects | Create/edit/delete (blocked while tasks, exams or sessions exist), colour, per-subject task/session/exam view |
| Tasks | Priority, estimate (minutes), due date/time, status; filter by status/priority/subject/deadline, search, sort, pagination; **overdue ≠ incomplete** is explicit |
| Exams | Date, topics, importance (1–5); shows the unfinished-task workload for that subject |
| Study sessions | Planned → completed (with actual minutes) or missed; planned-vs-completed summary |
| Dashboard | Due today, overdue, upcoming, exams, completion stats, 7-day planned vs completed, 7-day workload vs capacity (all computed from the database) |
| **Planner** | Weekly availability → ranked, explained plan → you review → accept (nothing saved until then) |
| **Recovery** | Mark old unfinished sessions as *missed* (kept in history), re-plan, see honestly which tasks don't fit and how many minutes short you are |
| UX | Loading, empty, error and success states, confirmations, accessible labelled forms, responsive layout |

## Tech stack and why
| Layer | Choice | Why |
|---|---|---|
| API | **FastAPI** (Python) | Your strongest language; automatic validation (Pydantic) and interactive docs at `/docs` |
| Database | **PostgreSQL** | Real relational integrity: foreign keys, check constraints, indexes |
| ORM | **SQLAlchemy 2.x** (typed `Mapped[...]` style) | Standard Python ORM; parameterised queries (no SQL injection) |
| Migrations | **Alembic** | Reproducible schema creation and evolution |
| Frontend | **React 18 + Vite** (JavaScript), React Router | Fast dev server, no TypeScript to learn yet |
| Styling | Plain CSS with variables | Nothing to learn beyond CSS |
| Auth | Server-side sessions + HttpOnly cookie | Real logout, no token in JavaScript (see [docs/architecture.md](docs/architecture.md)) |
| Tests | **pytest** (+ httpx test client), **Vitest** | Backend and planner are tested; frontend helpers are unit-tested |

No Docker, no paid service, no API key is needed.

## Architecture
```mermaid
flowchart LR
  B[Browser<br/>React app :5173] -- "/api/* (JSON over HTTP,<br/>session cookie)" --> V[Vite dev proxy]
  V --> F[FastAPI :8000]
  F --> R[Routers<br/>app/routers]
  R --> S[Services<br/>planner · dashboard · workload]
  R --> M[SQLAlchemy models<br/>app/models.py]
  S --> M
  M --> P[(PostgreSQL)]
  A[Alembic migrations] --> P
```
Read [docs/architecture.md](docs/architecture.md) for the full request walkthrough using real files.

## Database schema
```mermaid
erDiagram
  users ||--o{ auth_sessions : "has login sessions"
  users ||--o{ subjects : owns
  users ||--o{ tasks : owns
  users ||--o{ exams : owns
  users ||--o{ study_sessions : owns
  users ||--o{ availability : "7 rows max"
  subjects ||--o{ tasks : contains
  subjects ||--o{ exams : has
  subjects ||--o{ study_sessions : has
  tasks |o--o{ study_sessions : "optional link"
  users { int id PK
    string email UK
    string name
    string password_hash
    string timezone }
  subjects { int id PK
    int user_id FK
    string name "unique per user"
    string color }
  tasks { int id PK
    int user_id FK
    int subject_id FK
    string title
    datetime due_at "UTC, nullable"
    string priority "low|medium|high"
    int estimated_minutes
    string status "pending|in_progress|completed" }
  exams { int id PK
    int subject_id FK
    date exam_date
    int importance "1..5" }
  study_sessions { int id PK
    int subject_id FK
    int task_id FK "nullable"
    date planned_date
    int planned_minutes
    int actual_minutes
    string status "planned|completed|missed"
    string source "manual|planner" }
  availability { int id PK
    int user_id FK
    int weekday "0=Mon..6=Sun"
    int minutes }
```
Why each table exists: [docs/database-design.md](docs/database-design.md).

---

## Setup: step by step

> **New words, explained once.**
> **Terminal / PowerShell** – the text window where you type commands.
> **Virtual environment (venv)** – a private folder of Python packages for *this* project so it doesn't clash with other projects.
> **Environment variable / `.env` file** – settings (like the database password) kept outside the code so they are never committed to GitHub.
> **Database migration** – a versioned script that creates or changes database tables, so everyone gets the identical schema.
> **API endpoint** – a URL such as `/api/tasks` that the frontend calls to read or change data.
> **CORS** – a browser security rule about which websites may call which servers. In development we avoid it with a proxy.

### 1. Install prerequisites
| Tool | Version | Get it |
|---|---|---|
| Python | 3.11, 3.12 or 3.13 | https://www.python.org/downloads/ (Windows: tick **"Add python.exe to PATH"**) |
| Node.js | 20 LTS or newer (includes `npm`) | https://nodejs.org |
| PostgreSQL | 15 or newer | https://www.postgresql.org/download/ (Windows: remember the password you set for the `postgres` user; keep the default port 5432) |
| Git | any recent | https://git-scm.com |
| VS Code (recommended) | | https://code.visualstudio.com |

Check in PowerShell (macOS/Linux: Terminal):
```powershell
python --version      # macOS/Linux: python3 --version
node --version
npm --version
git --version
psql --version        # if "not recognised" on Windows, see Troubleshooting
```

### 2. Get the project and open it
```powershell
cd $HOME\Documents          # or wherever you keep projects
git clone <YOUR-REPO-URL> studyos   # or unzip studyos.zip
cd studyos
code .                      # opens VS Code; use Terminal > New Terminal inside VS Code
```

### 3. Create the database
PostgreSQL must be running (on Windows it normally starts automatically as a service).
```powershell
psql -U postgres
```
Enter your `postgres` password, then paste this at the `postgres=#` prompt (change the password!):
```sql
CREATE USER studyos WITH PASSWORD 'choose-a-password';
CREATE DATABASE studyos OWNER studyos;
\q
```
*(macOS/Linux: `sudo -u postgres psql` instead of `psql -U postgres`.)*

### 4. Set up the backend
```powershell
cd backend

# 4a. Create and activate a virtual environment
python -m venv .venv                    # macOS/Linux: python3 -m venv .venv
.\.venv\Scripts\Activate.ps1            # macOS/Linux: source .venv/bin/activate
# If PowerShell blocks the script: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned, then retry.
# Your prompt should now start with (.venv)

# 4b. Install Python packages
pip install -r requirements-dev.txt

# 4c. Create your .env file from the template, then edit it
Copy-Item .env.example .env             # macOS/Linux: cp .env.example .env
```
Open `backend/.env` and make `DATABASE_URL` match what you created:
```
DATABASE_URL=postgresql+psycopg://studyos:choose-a-password@localhost:5432/studyos
```
(If your password contains `@ : / #` characters, URL-encode them or choose a simpler password.)

```powershell
# 4d. Create the tables (run the migration)
alembic upgrade head

# 4e. Start the API server (leave this window open)
uvicorn app.main:app --reload
```
Check it: open http://localhost:8000/api/health → `{"status":"ok"}`, and http://localhost:8000/docs for the interactive API documentation.

### 5. Set up the frontend (in a **second** terminal)
```powershell
cd studyos\frontend
npm install
npm run dev
```
Open **http://localhost:5173**. (No `.env` is needed for the frontend in development; the Vite dev server forwards `/api` to port 8000.)

### Stop and restart
Stop either server with `Ctrl + C`. Next time: activate the venv again (`.\.venv\Scripts\Activate.ps1`) and run `uvicorn app.main:app --reload` in `backend`, and `npm run dev` in `frontend`. Your data stays in PostgreSQL.

## Smoke test: use the app
1. **Register** (name, email, password ≥ 8 chars). You land on an empty dashboard.
2. **Subjects → New subject**: "Operating Systems".
3. **Tasks → New task**: "Lab report", due in 2 days, High priority, 120 minutes. Add 2–3 more with different due dates, including one in the past (it will show **Overdue**).
4. **Exams → New exam** for that subject, 4 days away, importance 5.
5. **Planner**: enter e.g. 90 min per day, **Save availability**, then **Generate plan**. Read the ranking table ("Why this plan?"), then **Accept**. Open **Study** to see the created sessions.
6. **Recovery workflow**: on **Study**, add a session dated *yesterday* and leave it unfinished. Back in **Planner**, the *Missed work* box appears → **Mark selected as missed** → **Generate plan** again: the work is re-planned.
7. **Overload**: lower availability to 15 min/day and re-generate. The red banner reports how many minutes short you are, and which tasks don't fit. Nothing is deleted.
8. **Dashboard**: numbers reflect all of the above. Log out, log in again; data persists.
9. Confirm persistence in the database: `psql -U studyos -d studyos -c "select title, status from tasks;"`

## Running the tests
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest                       # uses an in-memory SQLite database; needs no setup
```
Run against real PostgreSQL too (use a separate, empty database, because tests drop and recreate tables):
```powershell
# one-time: psql -U postgres -c "CREATE DATABASE studyos_test OWNER studyos;"
$env:TEST_DATABASE_URL = "postgresql+psycopg://studyos:choose-a-password@localhost:5432/studyos_test"
pytest
```
Frontend helper tests and a production build check:
```powershell
cd frontend
npm test
npm run build
```
What is covered: authentication and cookies, access control on every endpoint, CRUD, validation failures, **user data isolation (IDOR)**, filters/sorting/pagination, the planner algorithm (fitting, overload, deadline conflicts, overdue, exam boost, determinism, EDF-vs-score case), accept/missed/replan flow, and the dashboard numbers. A time-freezing `get_now` dependency makes date logic deterministic.

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| `psql` not recognised (Windows) | Add `C:\Program Files\PostgreSQL\<version>\bin` to PATH, or open "SQL Shell (psql)" from the Start menu |
| `password authentication failed for user "studyos"` | The password in `backend/.env` differs from the one you created. Fix `.env` (or `ALTER USER studyos PASSWORD '...';`) |
| `connection refused` on port 5432 | PostgreSQL isn't running. Windows: *Services* → `postgresql-x64-NN` → Start |
| `database "studyos" does not exist` | Redo step 3 |
| `alembic: command not found` / `No module named ...` | The venv isn't active. Run the activate command; your prompt should show `(.venv)` |
| PowerShell: "running scripts is disabled" | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Browser shows "Cannot reach the server" | Backend isn't running on port 8000, or you opened the app on a different port than 5173 |
| Logged out immediately / login "does nothing" | Open the app via `http://localhost:5173` (not `127.0.0.1`), and keep `CORS_ORIGINS` matching that exact URL |
| `Port 8000/5173 already in use` | Another instance is running. Close it, or use `--port 8001` (then change the proxy target in `frontend/vite.config.js`) |
| `ZoneInfoNotFoundError` on Windows | `pip install tzdata` (it's in requirements.txt already) |
| Edited models but DB didn't change | Models don't change tables by themselves. Create a migration: `alembic revision --autogenerate -m "describe change"` then `alembic upgrade head` |

How to debug a failing request: [docs/architecture.md#debugging-a-failing-request](docs/architecture.md).

## API documentation
Start the backend and open **http://localhost:8000/docs** (Swagger UI) or `/redoc`. Human-written overview: [docs/api-guide.md](docs/api-guide.md).

## Known limitations
This is a learning/portfolio project, **not production-hardened**.
- No email verification, password reset, rate limiting, or account lockout; registration reveals whether an email exists.
- CSRF protection relies on `SameSite=Lax` cookies + JSON-only endpoints + a strict CORS allow-list; there are no CSRF tokens. Production needs HTTPS (`COOKIE_SECURE=true`) and a same-site deployment.
- Not deployed. The dev setup uses a proxy; a production deployment (reverse proxy, HTTPS, process manager) is not provided.
- Planner is a **heuristic**, not an optimiser: day-level granularity (no clock times), deadlines compare calendar days, tasks have no dependencies, no breaks or maximum session length, and a task is split across days without a minimum block size. See [docs/planner-algorithm.md](docs/planner-algorithm.md).
- Tasks have a single estimate; progress is only inferred from completed study sessions.
- Only list endpoints for tasks are paginated; other lists are small and capped.
- Frontend has helper unit tests only; UI behaviour was verified by hand/API, not by browser-automation tests.

## Future improvements
Calendar/ICS export, recurring tasks, task dependencies, minimum/maximum block sizes and breaks in the planner, password reset by email, Docker Compose, CI (GitHub Actions running pytest + build), end-to-end tests (Playwright), deployment, and *later*, optional AI features built on top of the working core.

## Publishing to GitHub
1. Make sure no secrets are tracked: `git status` must **not** list `.env`. Only `.env.example` files are committed.
2. Create an empty repository on https://github.com/new (name: `studyos`, no README/.gitignore/licence, because this project already has them).
3. In the project folder:
```powershell
git init
git branch -M main
git add .
git status                       # review the list
git commit -m "chore: initial project skeleton"
git remote add origin https://github.com/<your-username>/studyos.git
git push -u origin main
```
A suggested commit-by-commit sequence for building this up honestly is in [docs/learning-guide.md](docs/learning-guide.md#git-commit-sequence). Interview questions and a truthful resume template: [docs/interview-and-resume.md](docs/interview-and-resume.md).

### Screenshots
After running the app, capture these and save to `docs/screenshots/`: `dashboard.png`, `tasks.png`, `planner-plan.png`, `planner-overloaded.png`, `missed-work.png`, and a mobile-width view. Update the image link at the top of this README.

## Project layout
```
studyos/
  backend/   app/ (main, config, database, models, schemas, security, deps, routers/, services/)
             migrations/  tests/  requirements*.txt  alembic.ini  .env.example
  frontend/  src/ (api/, components/, context/, lib/, pages/)  package.json  vite.config.js
  docs/      architecture · database-design · api-guide · planner-algorithm · learning-guide · interview-and-resume
```
