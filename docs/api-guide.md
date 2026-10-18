# API guide

Interactive docs (generated from the code): **http://localhost:8000/docs**. All paths below start with `/api`. Bodies are JSON. Auth = the `studyos_session` cookie set by login/register. Errors look like `{"detail": "..."}` (422 returns a list of field errors).

| Method | Path | Purpose | Success |
|---|---|---|---|
| POST | `/auth/register` | Create account + log in | 201 |
| POST | `/auth/login` | Log in | 200 |
| POST | `/auth/logout` | Delete session | 204 |
| GET / PATCH | `/auth/me` | Current user / change name, timezone | 200 |
| GET, POST | `/subjects` | List (with counts) / create | 200 / 201 |
| GET, PATCH, DELETE | `/subjects/{id}` | Read / edit / delete (409 if it has tasks, exams or sessions) | 200 / 200 / 204 |
| GET | `/tasks` | Filters: `status, priority, subject_id, due=overdue\|today\|upcoming\|none, q`; sort: `sort=due_at\|priority\|created_at`, `order`; paging `limit` (≤200), `offset` → `{items,total,limit,offset}` | 200 |
| POST | `/tasks` | Create | 201 |
| GET, PATCH, DELETE | `/tasks/{id}` | Read / edit / delete | 200/200/204 |
| POST | `/tasks/{id}/complete` | Mark completed | 200 |
| GET, POST | `/exams` | List (`subject_id`, `upcoming_only`) with `days_until`, `prep_minutes` / create | 200 / 201 |
| GET, PATCH, DELETE | `/exams/{id}` | | |
| GET, POST | `/sessions` | List (`status, subject_id, task_id, date_from, date_to`) / create | |
| GET | `/sessions/summary` | planned / completed / missed minutes for a date range (default last 7 days) | 200 |
| GET, PATCH, DELETE | `/sessions/{id}` | | |
| POST | `/sessions/{id}/complete` | `{actual_minutes}` (defaults to planned) | 200 |
| GET, PUT | `/availability` | 7 weekday entries (0=Mon) | 200 |
| POST | `/planner/generate` | `{days: 1–28}` → suggested plan, **saves nothing** | 200 |
| POST | `/planner/accept` | `{items:[{task_id,date,minutes}]}` → creates planned sessions atomically | 201 |
| GET | `/planner/missed` | Planned sessions in the past | 200 |
| POST | `/planner/mark-missed` | `{session_ids:[...]}` | 200 |
| GET | `/dashboard` | All dashboard numbers | 200 |
| GET | `/health` | Liveness check | 200 |

Status codes used: **401** not logged in, **404** not found *or not yours*, **409** conflict (duplicate email/subject name, subject in use, completed task), **422** validation error, **500** unexpected (generic message).

Task example:
```http
POST /api/tasks
{"title":"Lab report","subject_id":1,"due_at":"2026-03-06T17:00","priority":"high","estimated_minutes":120}
→ 201 {"id":7,"title":"Lab report","status":"pending","is_overdue":false,"subject":{"id":1,"name":"Operating Systems","color":"#3366ff"}, ...}
```
`due_at` accepts an ISO datetime. **Without an offset it is read in the user's profile timezone**; with `Z`/`+05:30` it is exact. Responses are always UTC.
