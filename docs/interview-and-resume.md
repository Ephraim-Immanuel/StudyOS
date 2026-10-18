# Interview preparation and resume (truthful edition)

Answers below describe **what this code actually does**. Rehearse them in your own words, and only claim what you have run and understood.

## Likely questions

**Why FastAPI?** It's Python (my strongest language), validates requests automatically from type hints via Pydantic, and generates interactive docs at `/docs`. I used dependencies (`Depends`) for the DB session, current user and the clock.

**How does a REST API work?** Resources are URLs (`/api/tasks/7`); HTTP methods are the actions (GET read, POST create, PATCH partial update, DELETE remove); status codes report the outcome (201 created, 404 not found, 409 conflict, 422 invalid). Data is JSON. The server keeps no per-request state apart from the session cookie.

**How does React communicate with FastAPI?** `src/api/client.js` wraps `fetch` (JSON, `credentials: 'include'`). Pages call functions from `src/api/index.js`. In development Vite proxies `/api` to port 8000 so the browser sees one origin. Errors are normalised into an `ApiError` with per-field messages for forms.

**Why PostgreSQL?** The data is relational (users → subjects → tasks/exams/sessions). I wanted foreign keys, CHECK constraints, unique constraints and indexes enforced by the database, not only by my code.

**How did you design the schema?** One table per entity, every user-owned row carries `user_id`. `UNIQUE(user_id, name)` on subjects; `ON DELETE RESTRICT` from tasks/exams/sessions to subjects; `SET NULL` from sessions to tasks so history survives. Planner output is computed, not stored; accepting it creates normal study sessions. (See `docs/database-design.md`.)

**What is a foreign key?** A column whose value must exist in another table's key, e.g. `tasks.subject_id → subjects.id`, so a task can't point at a missing subject.

**How does authentication work?** Passwords are hashed with bcrypt. On login the server creates a random token, stores only its SHA-256 hash in `auth_sessions`, and sends the token in an HttpOnly, SameSite=Lax cookie. Each protected route resolves the user from that cookie via `get_current_user`; logout deletes the row so the token dies immediately.

**How do you stop users accessing others' data?** Lists are filtered by `user_id`; single-object routes use `get_owned`, which returns 404 for rows that aren't yours; referenced ids (subject_id, task_id) are checked for ownership too. A dedicated test hits every resource with a second user.

**How does your planner work?** Score each unfinished task (urgency 45, priority 30, exam proximity 15, workload 10). Phase 1 reserves minutes for tasks in score order on the latest days before their deadlines, so low-scoring tasks lose when time is short. Phase 2 lays the admitted minutes out earliest-deadline-first on the earliest free days. It's deterministic and explained per task. It isn't optimal.

**What happens when tasks exceed available time?** The plan still returns what fits, marks tasks `partial`/`unscheduled` with a reason, reports a shortfall in minutes (extra time needed before the deadlines) and shows a warning. Nothing is deleted or completed, and the user must accept before anything is saved.

**How did you test the backend?** pytest with FastAPI's test client, an in-memory SQLite DB by default and PostgreSQL via `TEST_DATABASE_URL`. Dependency overrides swap the DB and freeze the clock. Tests cover auth, isolation, CRUD, validation, filters, planner unit tests and the full missed-work workflow. (Run it yourself and quote *your* numbers.)

**What would you change with 10,000 users?** Add indexes based on measured slow queries (`EXPLAIN ANALYZE`), a connection pool/pgbouncer, rate limiting, caching the dashboard, move sessions to Redis if needed, background job for heavy planning, structured logging and monitoring, CI, HTTPS, and per-user pagination on every list. I haven't load-tested this, so I'd measure first.

**Current limitations?** No email verification/password reset/rate limiting; day-granularity planner heuristics; no deployment; frontend has only helper unit tests.

**What would you build next?** Min/max block size and breaks in the planner, calendar export, CI, Playwright end-to-end tests, deployment; AI features only after that, built on the working data model.

**Bonus:** *Why cookie sessions over JWT?* HttpOnly cookies can't be stolen by XSS, and server-side sessions allow real logout. Trade-off: CSRF, handled with SameSite=Lax + JSON-only + CORS allow-list. *Why return 404 instead of 403?* Doesn't confirm that someone else's id exists. *Why store times in UTC?* One unambiguous instant; convert to the user's timezone only for "which day" and display.

## Truthful resume entry (template)
Fill in **only** what you have implemented, run and can explain. Delete any bullet that isn't true for you.

> **StudyOS: academic planner and missed-work recovery tool** · Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, React · *GitHub: link*
> - Built a full-stack web app (FastAPI REST API, React/Vite UI, PostgreSQL) for managing subjects, tasks, exams and study sessions, with cookie-session authentication and bcrypt password hashing.
> - Designed a relational schema with foreign keys, check constraints and Alembic migrations; enforced per-user data isolation on every endpoint.
> - Implemented a deterministic weekly planning heuristic (urgency, priority, exam proximity, effort) with explainable output, overload/deadline-conflict reporting and a review-then-accept workflow for rescheduling missed work.
> - Wrote **N** automated tests (pytest) covering authentication, access control, validation and planner logic. *(Replace N with the real number from your own run; the original build reported 58 backend tests and 7 frontend tests.)*

Do **not** add users, traffic, performance gains, "deployed" or "production" claims unless they're true. If you later deploy it, add the link then.

## Self-check before an interview
- Can I draw the request flow for "create a task" from memory?
- Can I explain every table and why `RESTRICT` / `SET NULL` was chosen?
- Can I run the app and the tests from a clean clone?
- Can I change the planner weights and predict the effect?
