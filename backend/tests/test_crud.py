"""Subjects, tasks, exams, study sessions: CRUD, validation, filters, data isolation.
Frozen clock: Wed 2026-03-04 10:00 UTC; test users use the UTC timezone."""
import pytest


def make_task(client, subject, **kw):
    body = {"title": "Read chapter", "subject_id": subject["id"], **kw}
    r = client.post("/api/tasks", json=body)
    assert r.status_code == 201, r.text
    return r.json()


# ---------------- subjects
def test_subject_crud_and_duplicates(client):
    r = client.post("/api/subjects", json={"name": " Maths ", "description": "Calculus", "color": "#112233"})
    assert r.status_code == 201 and r.json()["name"] == "Maths"
    sid = r.json()["id"]
    assert client.post("/api/subjects", json={"name": "Maths"}).status_code == 409
    assert client.patch(f"/api/subjects/{sid}", json={"description": "Linear algebra"}).json()["description"] == "Linear algebra"
    assert [s["name"] for s in client.get("/api/subjects").json()] == ["Maths"]
    assert client.delete(f"/api/subjects/{sid}").status_code == 204
    assert client.get(f"/api/subjects/{sid}").status_code == 404


def test_subject_validation(client):
    assert client.post("/api/subjects", json={"name": ""}).status_code == 422
    assert client.post("/api/subjects", json={"name": "X", "color": "red"}).status_code == 422


def test_cannot_delete_subject_with_dependents(client, subject):
    t = make_task(client, subject)
    r = client.delete(f"/api/subjects/{subject['id']}")
    assert r.status_code == 409 and "1 task" in r.json()["detail"]
    client.delete(f"/api/tasks/{t['id']}")
    assert client.delete(f"/api/subjects/{subject['id']}").status_code == 204


def test_subject_counts(client, subject):
    make_task(client, subject)
    done = make_task(client, subject, title="done")
    client.post(f"/api/tasks/{done['id']}/complete")
    s = client.get(f"/api/subjects/{subject['id']}").json()
    assert s["total_tasks"] == 2 and s["open_tasks"] == 1


# ---------------- tasks
def test_task_crud_and_complete(client, subject):
    t = make_task(client, subject, description=" notes ", priority="high", estimated_minutes=90,
                  due_at="2026-03-10T12:00:00Z")
    assert t["status"] == "pending" and t["description"] == "notes" and t["subject"]["name"] == "Operating Systems"
    upd = client.patch(f"/api/tasks/{t['id']}", json={"status": "in_progress", "title": "New title"}).json()
    assert upd["status"] == "in_progress" and upd["title"] == "New title" and upd["completed_at"] is None
    done = client.post(f"/api/tasks/{t['id']}/complete").json()
    assert done["status"] == "completed" and done["completed_at"] is not None
    reopened = client.patch(f"/api/tasks/{t['id']}", json={"status": "pending"}).json()
    assert reopened["completed_at"] is None
    assert client.patch(f"/api/tasks/{t['id']}", json={"due_at": None}).json()["due_at"] is None
    assert client.delete(f"/api/tasks/{t['id']}").status_code == 204
    assert client.get(f"/api/tasks/{t['id']}").status_code == 404


@pytest.mark.parametrize("bad", [
    {"title": ""}, {"title": "   "}, {"priority": "urgent"}, {"estimated_minutes": 0},
    {"estimated_minutes": 5000}, {"status": "done"}, {"due_at": "not-a-date"},
])
def test_task_validation_errors(client, subject, bad):
    body = {"title": "ok", "subject_id": subject["id"], **bad}
    assert client.post("/api/tasks", json=body).status_code == 422


def test_task_needs_existing_subject(client):
    assert client.post("/api/tasks", json={"title": "x", "subject_id": 999}).status_code == 404


def test_overdue_is_different_from_incomplete(client, subject):
    past = make_task(client, subject, title="past", due_at="2026-03-01T10:00:00Z")
    future = make_task(client, subject, title="future", due_at="2026-03-20T10:00:00Z")
    nodate = make_task(client, subject, title="nodate")
    assert (past["is_overdue"], future["is_overdue"], nodate["is_overdue"]) == (True, False, False)
    # all three are incomplete, only one is overdue
    assert client.get("/api/tasks?status=pending").json()["total"] == 3
    assert [t["title"] for t in client.get("/api/tasks?due=overdue").json()["items"]] == ["past"]
    done = client.post(f"/api/tasks/{past['id']}/complete").json()
    assert done["is_overdue"] is False  # completed work is never overdue


def test_task_filters_sorting_pagination(client, subject):
    other_subject = client.post("/api/subjects", json={"name": "Maths"}).json()
    make_task(client, subject, title="A low", priority="low", due_at="2026-03-10T10:00:00Z")
    make_task(client, subject, title="B high", priority="high", due_at="2026-03-08T10:00:00Z")
    make_task(client, other_subject, title="C med", priority="medium")
    make_task(client, subject, title="D today", due_at="2026-03-04T18:00:00Z")

    titles = lambda q: [t["title"] for t in client.get(f"/api/tasks?{q}").json()["items"]]
    assert titles("sort=due_at") == ["D today", "B high", "A low", "C med"]  # no-date last
    assert titles("sort=due_at&order=desc")[:3] == ["A low", "B high", "D today"]
    assert titles("sort=priority&order=desc")[0] == "B high"
    assert titles("priority=low") == ["A low"]
    assert titles(f"subject_id={other_subject['id']}") == ["C med"]
    assert titles("due=today") == ["D today"]
    assert titles("due=upcoming") == ["D today", "B high", "A low"]  # now .. end of Mar 10
    assert titles("due=none") == ["C med"]
    assert titles("q=high") == ["B high"]
    page = client.get("/api/tasks?limit=2&offset=2&sort=due_at").json()
    assert page["total"] == 4 and len(page["items"]) == 2
    assert client.get("/api/tasks?limit=0").status_code == 422
    assert client.get("/api/tasks?sort=bogus").status_code == 422


def test_naive_datetime_is_interpreted_in_user_timezone(client, subject):
    client.patch("/api/auth/me", json={"timezone": "Asia/Kolkata"})
    t = make_task(client, subject, due_at="2026-03-10T12:00:00")  # no offset => 12:00 IST
    assert t["due_at"].startswith("2026-03-10T06:30:00")


# ---------------- exams
def test_exam_crud_and_prep_workload(client, subject):
    make_task(client, subject, estimated_minutes=90)
    make_task(client, subject, estimated_minutes=30)
    r = client.post("/api/exams", json={"subject_id": subject["id"], "title": "Midterm",
                                        "exam_date": "2026-03-10", "importance": 5, "topics": "Deadlocks"})
    assert r.status_code == 201
    e = r.json()
    assert e["days_until"] == 6 and e["prep_minutes"] == 120 and e["open_tasks"] == 2
    assert client.patch(f"/api/exams/{e['id']}", json={"importance": 2}).json()["importance"] == 2
    assert client.post("/api/exams", json={"subject_id": subject["id"], "title": "x", "exam_date": "2026-03-10",
                                           "importance": 9}).status_code == 422
    assert len(client.get("/api/exams?upcoming_only=true").json()) == 1
    assert client.delete(f"/api/exams/{e['id']}").status_code == 204


# ---------------- study sessions
def test_session_workflow(client, subject):
    t = make_task(client, subject)
    r = client.post("/api/sessions", json={"subject_id": subject["id"], "task_id": t["id"],
                                           "planned_date": "2026-03-04", "planned_minutes": 45})
    assert r.status_code == 201
    s = r.json()
    assert s["status"] == "planned" and s["actual_minutes"] is None and s["task"]["id"] == t["id"]
    done = client.post(f"/api/sessions/{s['id']}/complete", json={"actual_minutes": 30}).json()
    assert done["status"] == "completed" and done["actual_minutes"] == 30
    summary = client.get("/api/sessions/summary").json()
    assert summary["planned_minutes"] == 45 and summary["completed_minutes"] == 30
    assert client.patch(f"/api/sessions/{s['id']}", json={"status": "planned"}).json()["actual_minutes"] is None


def test_session_default_actual_equals_planned_and_validation(client, subject):
    s = client.post("/api/sessions", json={"subject_id": subject["id"], "planned_date": "2026-03-04",
                                           "planned_minutes": 25}).json()
    assert client.post(f"/api/sessions/{s['id']}/complete").json()["actual_minutes"] == 25
    assert client.post("/api/sessions", json={"subject_id": subject["id"], "planned_date": "2026-03-04",
                                              "planned_minutes": 0}).status_code == 422
    assert client.post(f"/api/sessions/{s['id']}/complete", json={"actual_minutes": -5}).status_code == 422


def test_session_task_must_match_subject(client, subject):
    maths = client.post("/api/subjects", json={"name": "Maths"}).json()
    t = make_task(client, subject)
    r = client.post("/api/sessions", json={"subject_id": maths["id"], "task_id": t["id"],
                                           "planned_date": "2026-03-04", "planned_minutes": 30})
    assert r.status_code == 422


def test_deleting_task_keeps_session_history(client, subject):
    t = make_task(client, subject)
    s = client.post("/api/sessions", json={"subject_id": subject["id"], "task_id": t["id"],
                                           "planned_date": "2026-03-04", "planned_minutes": 30}).json()
    client.delete(f"/api/tasks/{t['id']}")
    after = client.get(f"/api/sessions/{s['id']}").json()
    assert after["task_id"] is None and after["planned_minutes"] == 30


# ---------------- data isolation (the IDOR tests)
def test_users_cannot_see_or_touch_each_others_data(client, other, subject):
    task = make_task(client, subject)
    exam = client.post("/api/exams", json={"subject_id": subject["id"], "title": "E", "exam_date": "2026-03-10"}).json()
    sess = client.post("/api/sessions", json={"subject_id": subject["id"], "planned_date": "2026-03-04",
                                              "planned_minutes": 30}).json()
    # lists are empty for the other user
    for path in ("subjects", "exams", "sessions"):
        assert other.get(f"/api/{path}").json() == []
    assert other.get("/api/tasks").json()["total"] == 0
    # direct access by id is "not found", never "forbidden" (does not reveal existence)
    for path, obj in (("subjects", subject), ("tasks", task), ("exams", exam), ("sessions", sess)):
        assert other.get(f"/api/{path}/{obj['id']}").status_code == 404
        assert other.patch(f"/api/{path}/{obj['id']}", json={}).status_code == 404
        assert other.delete(f"/api/{path}/{obj['id']}").status_code == 404
    assert other.post(f"/api/tasks/{task['id']}/complete").status_code == 404
    assert other.post(f"/api/sessions/{sess['id']}/complete").status_code == 404
    # cannot attach own objects to someone else's subject / task
    assert other.post("/api/tasks", json={"title": "x", "subject_id": subject["id"]}).status_code == 404
    assert other.post("/api/exams", json={"subject_id": subject["id"], "title": "x", "exam_date": "2026-03-10"}).status_code == 404
    assert other.post("/api/sessions", json={"subject_id": subject["id"], "planned_date": "2026-03-04",
                                             "planned_minutes": 10}).status_code == 404
    mine = other.post("/api/subjects", json={"name": "Mine"}).json()
    assert other.patch(f"/api/tasks/{task['id']}", json={"subject_id": mine["id"]}).status_code == 404
    # nothing changed for the owner
    assert client.get(f"/api/tasks/{task['id']}").json()["title"] == "Read chapter"
    assert client.get(f"/api/subjects/{subject['id']}").status_code == 200
