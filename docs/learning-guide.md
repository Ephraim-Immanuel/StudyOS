# Learning guide: Build → Run → Understand → Modify → Test

You already have the working project. Use it as a **guided reading + modification course**. Do the milestones in order; each takes a few evenings. For every milestone: run it, read the listed files, do the exercise, run the tests.

> Rule: never paste code you don't understand. After each exercise, explain the change aloud in 3 sentences. If you can't, re-read the files.

---
## Milestone 0: Run everything (day 1)
**Goal:** register, create a subject and task, see the row in PostgreSQL, use the planner. Follow the README runbook and "Smoke test".
**Verify:** `psql -U studyos -d studyos -c "select id,title,status from tasks;"` shows your task.
**Common errors:** see README Troubleshooting.
**Exercise:** change the brand text in `frontend/src/components/Layout.jsx`; watch the browser update without refresh (Vite hot reload).
**You should be able to answer:** What are the three processes running (PostgreSQL, uvicorn, Vite) and what does each do?

## Milestone 1: HTTP, REST and FastAPI basics
**Concepts:** an API endpoint is *method + URL* (`GET /api/subjects`). REST: nouns in URLs, verbs as HTTP methods, status codes for outcomes.
**Read:** `backend/app/main.py`, `backend/app/routers/subjects.py`, then try every subject endpoint in http://localhost:8000/docs.
**Expected:** you can create, edit and delete a subject from Swagger UI, and see a 409 when deleting a subject that has tasks.
**Exercise:** add `GET /api/subjects/count` returning `{"count": N}`. (Hint: declare it *before* `/{subject_id}`; see how `/sessions/summary` does it and why.) Write a test in `tests/test_crud.py`.
**Interview outcome:** explain GET vs POST vs PATCH vs PUT vs DELETE, and why delete returns 204.

## Milestone 2: Validation (Pydantic)
**Read:** `app/schemas.py::TaskCreate`; `tests/test_crud.py::test_task_validation_errors`.
**Expected:** posting `{"title":"", ...}` returns 422 naming the field; the React form shows it under the input (`api/client.js::parseError`, `components/Field.jsx`).
**Exercise:** forbid `estimated_minutes` above 600 (change `le=1440`), add a test case to the parametrised list, and see the form error in the browser.
**Interview outcome:** where is input validated, and why is client-side validation alone not enough?

## Milestone 3: Database and SQLAlchemy
**Concepts:** table, row, primary key, foreign key, index, constraint, transaction.
**Read:** `app/models.py`, `docs/database-design.md`, `migrations/versions/0001_initial_schema.py`.
**Expected:** you can map each model class to a table in `\d tasks` inside psql.
**Exercise:** add an optional `location` string to `Task` (e.g. "Library"): edit the model, `alembic revision --autogenerate -m "add task location"`, read the generated file, `alembic upgrade head`, add the field to `TaskCreate`/`TaskOut`, `TaskForm.jsx`, and a test. 
**Common errors:** forgetting `alembic upgrade head` → "column does not exist" 500.
**Interview outcome:** what is a foreign key; what does `ON DELETE RESTRICT` vs `SET NULL` do (see `tasks` and `study_sessions`); what is a migration and why not edit tables by hand?

## Milestone 4: Authentication and authorization
**Read:** `app/security.py`, `app/routers/auth.py`, `app/deps.py` (`get_current_user`, `get_owned`), `frontend/src/context/AuthContext.jsx`, `tests/test_auth.py`.
**Expected:** DevTools → Application → Cookies shows `studyos_session` flagged HttpOnly; `document.cookie` in the console does *not* show it.
**Exercise:** in `test_crud.py::test_users_cannot_see_or_touch_each_others_data`, add a check for another endpoint. Then *break* `get_owned` (remove the `user_id` comparison), run the tests, and watch the isolation test fail. Undo it.
**Interview outcome:** explain cookie sessions vs JWT, why only a hash of the token is stored, and how IDOR is prevented.

## Milestone 5: Tasks, filters and the React data flow
**Read:** `routers/tasks.py::list_tasks` (how filters build a `WHERE` clause), `frontend/src/pages/Tasks.jsx`, `lib/useAsync.js`, `components/TaskForm.jsx`.
**Expected:** changing a filter triggers a new `GET /api/tasks?...` visible in the Network tab.
**Exercise:** add a "Due this month" option to the Deadline filter: backend (`due` literal + condition) and frontend (`<option>`), plus a test.
**Interview outcome:** walk through `docs/architecture.md` end to end for "create a task"; explain overdue vs incomplete.

## Milestone 6: Dashboard
**Read:** `app/services/dashboard.py`, `pages/Dashboard.jsx`, `tests/test_dashboard_planner.py::test_dashboard_numbers_come_from_real_rows`.
**Exercise:** add `completed_this_week` to the stats (backend schema + service + a card + test).
**Interview outcome:** why `now` is injected (`deps.get_now`) so tests can freeze time; how timezones are handled.

## Milestone 7: Exams and study sessions
**Read:** `routers/exams.py`, `routers/sessions.py`, `services/workload.py`.
**Exercise:** add `notes` to study sessions (full-stack, with migration), or show the exam's `topics` on the Dashboard.
**Interview outcome:** why `task_id` uses `SET NULL`; how "remaining effort" is computed.

## Milestone 8: The planner
**Read in this order:** `docs/planner-algorithm.md`, `app/services/planner.py` (top to bottom), `tests/test_planner.py`, `routers/planner.py::generate`, `pages/Planner.jsx`.
**Expected:** you can predict, on paper, the plan for 3 tasks and compare with the app.
**Exercise A (easy):** change `PRIORITY_POINTS` high from 30 to 40; run `pytest`, see which tests change and why (some assertions encode the weights). 
**Exercise B (medium):** add a per-day cap `MAX_BLOCK = 90` so a task is split into sessions of ≤ 90 minutes. Write the failing test first.
**Exercise C (hard):** treat an exam date as an implicit deadline for undated tasks in that subject.
**Interview outcome:** describe the two phases and why score-order placement alone is wrong; what happens when workload exceeds capacity; the limitations.

## Milestone 9: Missed-work recovery
**Read:** `routers/planner.py::missed_candidates / mark_missed / accept`, `Planner.jsx::Missed`, `test_missed_work_recovery_flow`.
**Exercise:** show a "recovery summary" (minutes missed this week) on the Planner page.
**Interview outcome:** why missed sessions are marked, not deleted; why accept is a single transaction.

## Milestone 10: Testing
**Read:** `tests/conftest.py` (fixtures, dependency overrides, frozen clock), one test file end to end.
**Run:** `pytest -v`, `pytest -k planner`, `pytest -x` (stop at first failure). Also run with `TEST_DATABASE_URL` for PostgreSQL.
**Exercise:** write a test for a bug you invent (e.g. a negative `offset` on `/api/tasks`) *before* fixing it.
**Interview outcome:** unit vs API vs integration tests; why the planner is a pure function; what a fixture is.

---
## Git commit sequence
Use this as a *template for how to commit as you work through the milestones*. Commit only what you have actually done, with your own understanding. Don't backdate or fake history.
```
chore: initial project skeleton (.gitignore, README, folder layout)
feat(backend): FastAPI app, config and database connection
feat(db): SQLAlchemy models and first Alembic migration
feat(auth): register/login/logout with hashed passwords and cookie sessions
test(auth): authentication and access-control tests
feat(subjects): subject CRUD with ownership checks
feat(tasks): task CRUD, filters, sorting, pagination
test(isolation): cross-user data isolation tests
feat(frontend): Vite + React shell, API client, auth pages
feat(frontend): subjects and tasks pages
feat(exams-sessions): exams and study sessions (API + UI)
feat(dashboard): dashboard endpoint and page
feat(planner): planning algorithm with unit tests
feat(planner): availability, generate/accept API and Planner page
feat(recovery): missed-session workflow and re-planning
docs: architecture, database, planner and API docs
docs: screenshots and README polish
```
Good habits: small commits, present-tense messages, run `pytest` before each commit, never commit `.env`.
