# Database design

PostgreSQL, created and evolved by Alembic (`backend/migrations`). Models: `backend/app/models.py`.

| Table | Purpose | Key decisions |
|---|---|---|
| `users` | One row per student | `email` unique (stored lower-case); `password_hash` (bcrypt, never the password); `timezone` decides what "today" means |
| `auth_sessions` | Logged-in browsers | `token_hash` unique (SHA-256 of the cookie value); `expires_at`; `ON DELETE CASCADE` from user so deleting a user removes sessions |
| `subjects` | Courses | `UNIQUE(user_id, name)` so two users may both have "Maths" but one user cannot have it twice |
| `tasks` | Assignments | `subject_id` is **`ON DELETE RESTRICT`**: the database itself refuses to delete a subject that still has tasks (the API also explains why). CHECKs: priority and status values, `estimated_minutes > 0`. Indexes `(user_id, status)` and `(user_id, due_at)` serve the filters and the dashboard |
| `exams` | Exam dates | `importance` CHECK 1–5; index `(user_id, exam_date)` |
| `study_sessions` | Planned/completed/missed study blocks | `task_id` nullable and **`ON DELETE SET NULL`**: deleting a task keeps your study history. `status` ∈ planned/completed/missed (*missed* keeps the record instead of deleting it: this is what makes recovery auditable). `source` ∈ manual/planner. `planned_date` is a date, `planned_minutes > 0`, `actual_minutes` null until done |
| `availability` | Study minutes per weekday | `UNIQUE(user_id, weekday)`, weekday 0–6 (Mon=0), minutes 0–1440. At most 7 rows per user |

## Why not a `plans` table?
A plan suggestion is **computed on demand** and shown for review; nothing about it is persistent until accepted. Accepting creates ordinary `study_sessions` with `source='planner'`. This means (a) the planner can never overwrite an existing plan, (b) there is a single source of truth, and (c) re-planning is just "run the algorithm again with the current rows".

## Foreign keys and ownership
A **foreign key** is a column that must match an id in another table (`tasks.subject_id → subjects.id`), so you can never have a task for a subject that doesn't exist. Every user-data table also carries `user_id`. The API additionally checks that a referenced subject/task belongs to the same user (see `get_owned` in `app/deps.py`), because a plain foreign key alone would allow pointing at someone else's subject.

## Why relational columns, not JSON
Filtering ("high priority tasks due this week in subject X") and aggregation (minutes per day) are what SQL is good at; indexes and constraints only work on real columns.

## Avoiding N+1 queries
`Task.subject`, `Exam.subject`, `StudySession.subject/task` use `lazy="joined"`, so listing 50 tasks is one query with a JOIN, not 51. Subject counts use three grouped queries total (`app/routers/subjects.py::_with_counts`).

## Constraint names
`app/database.py::NAMING_CONVENTION` gives every index/constraint a predictable name so migrations are stable.

## Migration workflow
```powershell
alembic upgrade head              # apply everything
alembic current                   # which version am I on?
alembic revision --autogenerate -m "add notes column to tasks"   # after editing models.py
alembic downgrade -1              # undo the last migration
alembic check                     # does the DB match the models?
```
