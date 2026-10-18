# Architecture: how a request travels through StudyOS

We follow ONE real action: **creating a task** ("Lab report", Operating Systems, 120 min, due Friday).

## 1. The browser and React
`frontend/src/components/TaskForm.jsx` holds the form values in React state (`useState`). Each input is wired with `onChange`. When you press **Save task**, `submit()` runs:
```js
await tasks.create(body)          // frontend/src/api/index.js
```
React then re-renders because state changed (e.g. `busy` becomes `true`, disabling the button).

## 2. React sends an HTTP request
`tasks.create` calls `post('/tasks', d)` in `frontend/src/api/client.js`, which calls `fetch('/api/tasks', { method: 'POST', credentials: 'include', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(...) })`.
* **POST** means "create something new". (GET reads, PATCH edits part of something, PUT replaces, DELETE removes.)
* `credentials: 'include'` makes the browser attach the session cookie.
* In development the URL is `http://localhost:5173/api/tasks`; `vite.config.js` forwards it to `http://localhost:8000/api/tasks`. The browser only ever talks to one origin, so no CORS problem.

## 3. FastAPI receives it and validates it
`app/main.py` registered every router, so FastAPI matches `POST /api/tasks` to `create_task` in `app/routers/tasks.py`:
```python
@router.post("", response_model=TaskOut, status_code=201)
def create_task(data: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user), now = Depends(get_now)):
```
Before the function body runs FastAPI:
1. Resolves **dependencies**: `get_db` (`app/database.py`) opens a DB session; `get_current_user` (`app/deps.py`) reads the cookie, hashes it, looks it up in `auth_sessions`, and returns the `User` or raises **401**.
2. Parses the JSON body into **`TaskCreate`** (`app/schemas.py`). Pydantic checks types and rules (title 1–200 chars and not blank, `estimated_minutes` 1–1440, priority one of low/medium/high). Any violation returns **422** with a list of messages and your function never runs. `api/client.js → parseError` turns that list into `fieldErrors` that the form shows under each input.

## 4. Business logic
Inside `create_task`:
* `get_owned(db, Subject, data.subject_id, user, "Subject")` (`app/deps.py`) makes sure the subject belongs to **this** user (404 otherwise).
* `ensure_aware()` (`app/services/timeutil.py`) turns the due date into UTC. A string without an offset is read in the user's profile timezone.
* `_apply_status()` sets `completed_at` if needed.

## 5. SQLAlchemy talks to PostgreSQL
```python
task = Task(user_id=user.id, ...)   # a Python object, nothing in the DB yet
db.add(task)                         # register it
db.commit()                          # BEGIN; INSERT INTO tasks ...; COMMIT
db.refresh(task)                     # reload id, created_at
```
`app/models.py::Task` maps the class to the `tasks` table. Values are sent as **bound parameters** (never string-glued into SQL), which prevents SQL injection. If the database rejects the row (e.g. a CHECK constraint), SQLAlchemy raises an exception. Unexpected ones hit the handler in `app/main.py` which logs details server-side and returns a generic **500** `{"detail": "Internal server error"}`.

## 6. The response returns
`response_model=TaskOut` filters what leaves the server. `task_out()` (`app/services/serializers.py`) adds `is_overdue`. FastAPI sends **201 Created** with JSON. `fetch` resolves, `TaskForm` shows a toast (`ToastContext.jsx`), calls `onSaved()`, and `Tasks.jsx` calls `reload()` from `useAsync` to refetch the list. If the request failed, the `catch` block shows `err.fieldErrors` / `err.message`.

---

## Authentication and authorization
**Choice: server-side sessions in an HttpOnly cookie** (not JWT in localStorage).
| | Cookie session (chosen) | Token (JWT) in JS |
|---|---|---|
| Stored in | HttpOnly cookie; JavaScript can't read it | usually localStorage; any XSS bug can steal it |
| Logout | server deletes the row; token is dead immediately | token stays valid until expiry unless extra machinery exists |
| Extra risk | CSRF (mitigated below) | XSS token theft |

Flow (`app/routers/auth.py`, `app/security.py`):
1. **Register/login**: password checked with bcrypt (`verify_password`, with a dummy hash when the email is unknown so response time doesn't reveal which emails exist). `new_session_token()` makes 32 random bytes; only its **SHA-256 hash** is stored in `auth_sessions`. The raw token goes to the browser as a cookie: `HttpOnly`, `SameSite=Lax`, `Secure` when `COOKIE_SECURE=true`, 7-day expiry.
2. **Every protected route** depends on `get_current_user`. No cookie, unknown/expired token → 401. The React `AuthContext` calls `GET /api/auth/me` on load; a 401 means "show the login page".
3. **Authorization (ownership)**: every table with user data has `user_id`. Every single-row route calls `get_owned()` which returns **404** (not 403) for someone else's row, so IDs cannot be probed. List routes always filter `WHERE user_id = current_user.id`. `tests/test_crud.py::test_users_cannot_see_or_touch_each_others_data` checks this for subjects, tasks, exams and sessions.
4. **CORS**: `app/main.py` allows only origins in `CORS_ORIGINS` with credentials (never `*`). In dev the proxy makes it moot.
5. **CSRF**: `SameSite=Lax` stops browsers sending the cookie on cross-site POST/PATCH/DELETE; all state-changing endpoints require a JSON body. For production use HTTPS, `COOKIE_SECURE=true`, and ideally serve the frontend and API under the same site (e.g. `app.example.com` and `api.example.com`).

**Production implications**: set `COOKIE_SECURE=true`, set `CORS_ORIGINS` to the real frontend URL, use a real secret-managed `DATABASE_URL`, add rate limiting, and put it behind HTTPS.

## Time and timezones
* All instants (`due_at`, `created_at`...) are stored **in UTC** (`app/db_types.py::UTCDateTime` refuses naive datetimes).
* "Which day is it?" is always answered in the **user's profile timezone** (`users.timezone`, defaulting to the browser's timezone at registration): `app/services/timeutil.py`.
* Exam dates and session dates are plain calendar dates (no time).
* Known simplification: the planner treats a deadline as "the whole due day".

## Migrations
Alembic compares nothing by itself at runtime. `migrations/versions/0001_initial_schema.py` holds the `upgrade()` that creates the tables and `downgrade()` that drops them. `alembic upgrade head` runs unapplied versions in order and records the current version in the `alembic_version` table. To change the schema: edit `app/models.py`, run `alembic revision --autogenerate -m "add X"`, **read the generated file**, then `alembic upgrade head`. `alembic check` reports drift between models and the database.

## Debugging a failing request
1. **Reproduce in the browser DevTools → Network tab.** Click the red request. Look at *Status*, *Request payload*, and *Response*.
2. Status tells you where to look: `0`/"Cannot reach the server" → backend down or wrong port. **401** → not logged in / cookie missing (is the app on `localhost:5173`?). **403/404** → wrong id or someone else's row. **409** → business rule (duplicate name, subject has tasks). **422** → validation; the Response lists the field. **500** → a server bug.
3. For 500s read the **uvicorn terminal**; the traceback is printed there (not sent to the browser).
4. Try the same call in **http://localhost:8000/docs** ("Try it out") to separate frontend bugs from backend bugs. (Log in via `/api/auth/login` first; the cookie is shared.)
5. Write a failing **pytest** that reproduces it, fix, keep the test.
6. Inspect data: `psql -U studyos -d studyos -c "select * from tasks order by id desc limit 5;"`.
