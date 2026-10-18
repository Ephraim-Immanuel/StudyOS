"""Dashboard numbers, availability, and the planner workflow (generate -> accept -> missed -> replan).
Frozen clock: Wed 2026-03-04 10:00 UTC (weekday 2). Test users use the UTC timezone."""


def mk_task(client, subject, title, due=None, **kw):
    body = {"title": title, "subject_id": subject["id"], **kw}
    if due:
        body["due_at"] = due
    r = client.post("/api/tasks", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def set_availability(client, minutes_by_weekday):
    days = [{"weekday": d, "minutes": m} for d, m in minutes_by_weekday.items()]
    r = client.put("/api/availability", json={"days": days})
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------- dashboard
def test_dashboard_empty_state(client):
    d = client.get("/api/dashboard").json()
    assert d["today"] == "2026-03-04"
    assert d["due_today"] == d["overdue"] == d["upcoming"] == d["exams"] == []
    assert d["stats"]["total"] == 0 and d["stats"]["completion_rate"] == 0.0
    assert len(d["workload"]) == 7 and d["study_time"]["planned_minutes"] == 0


def test_dashboard_numbers_come_from_real_rows(client, subject):
    mk_task(client, subject, "overdue", "2026-03-03T10:00:00Z", estimated_minutes=30)
    mk_task(client, subject, "earlier today", "2026-03-04T09:00:00Z")  # 09:00 < now 10:00 => overdue
    mk_task(client, subject, "later today", "2026-03-04T20:00:00Z", estimated_minutes=45)
    mk_task(client, subject, "tomorrow", "2026-03-05T10:00:00Z", estimated_minutes=60)
    mk_task(client, subject, "far", "2026-04-01T10:00:00Z")
    done = mk_task(client, subject, "done")
    client.post(f"/api/tasks/{done['id']}/complete")
    client.post("/api/exams", json={"subject_id": subject["id"], "title": "Quiz", "exam_date": "2026-03-08"})
    set_availability(client, {2: 120, 3: 90})
    s = client.post("/api/sessions", json={"subject_id": subject["id"], "planned_date": "2026-03-04",
                                           "planned_minutes": 60}).json()
    client.post(f"/api/sessions/{s['id']}/complete", json={"actual_minutes": 40})

    d = client.get("/api/dashboard").json()
    assert [t["title"] for t in d["overdue"]] == ["overdue", "earlier today"]
    assert [t["title"] for t in d["due_today"]] == ["later today"]
    assert [t["title"] for t in d["upcoming"]] == ["tomorrow"]
    assert d["stats"] == {"total": 6, "pending": 5, "in_progress": 0, "completed": 1, "overdue": 2,
                          "completion_rate": 0.167}
    assert d["exams"][0]["days_until"] == 4
    assert d["study_time"]["planned_minutes"] == 60 and d["study_time"]["completed_minutes"] == 40
    today = d["workload"][0]
    assert today["date"] == "2026-03-04" and today["available_minutes"] == 120
    assert today["task_minutes_due"] == 60 + 45  # "earlier today" (60 default) + "later today" (45)
    assert today["planned_study_minutes"] == 0  # the one session today is completed, not planned
    tomorrow = d["workload"][1]
    assert tomorrow["task_minutes_due"] == 60 and tomorrow["available_minutes"] == 90


def test_dashboard_is_per_user(client, other, subject):
    mk_task(client, subject, "mine")
    assert other.get("/api/dashboard").json()["stats"]["total"] == 0


# ---------------------------------------------------------------- availability
def test_availability_defaults_and_upsert(client):
    assert [d["minutes"] for d in client.get("/api/availability").json()] == [0] * 7
    set_availability(client, {0: 60, 1: 90})
    res = set_availability(client, {0: 120})  # update, not duplicate
    assert res[0]["minutes"] == 120 and res[1]["minutes"] == 90
    assert client.put("/api/availability", json={"days": [{"weekday": 7, "minutes": 10}]}).status_code == 422
    assert client.put("/api/availability", json={"days": [{"weekday": 1, "minutes": 2000}]}).status_code == 422
    assert client.put("/api/availability", json={"days": [{"weekday": 1, "minutes": 5},
                                                          {"weekday": 1, "minutes": 6}]}).status_code == 422


# ---------------------------------------------------------------- planner
def test_generate_does_not_persist_anything(client, subject):
    mk_task(client, subject, "T", "2026-03-06T10:00:00Z", estimated_minutes=60)
    set_availability(client, {d: 60 for d in range(7)})
    plan = client.post("/api/planner/generate", json={"days": 7}).json()
    assert plan["scheduled_minutes"] == 60 and not plan["overloaded"]
    assert client.get("/api/sessions").json() == []  # review first, nothing saved


def test_accept_creates_sessions_and_replanning_does_not_duplicate(client, subject):
    t = mk_task(client, subject, "T", "2026-03-06T10:00:00Z", estimated_minutes=90)
    set_availability(client, {d: 60 for d in range(7)})
    plan = client.post("/api/planner/generate", json={"days": 7}).json()
    items = [{"task_id": s["task_id"], "date": s["date"], "minutes": s["minutes"]} for s in plan["suggestions"]]
    assert sum(i["minutes"] for i in items) == 90
    r = client.post("/api/planner/accept", json={"items": items})
    assert r.status_code == 201 and all(s["source"] == "planner" and s["task_id"] == t["id"] for s in r.json())
    # task itself is untouched
    assert client.get(f"/api/tasks/{t['id']}").json()["status"] == "pending"
    # generating again: the work is already planned, so nothing more is suggested
    again = client.post("/api/planner/generate", json={"days": 7}).json()
    assert again["suggestions"] == [] and again["tasks"] == []


def test_overloaded_plan_explains_itself(client, subject):
    mk_task(client, subject, "Big", "2026-03-05T10:00:00Z", priority="high", estimated_minutes=240)
    mk_task(client, subject, "Small", "2026-03-05T10:00:00Z", priority="low", estimated_minutes=60)
    set_availability(client, {2: 60, 3: 60})  # Wed + Thu = 120 min, but 300 min are due by Thu
    plan = client.post("/api/planner/generate", json={"days": 7}).json()
    assert plan["overloaded"] and plan["shortfall_minutes"] == 180
    assert plan["total_capacity_minutes"] == 120 and plan["total_demand_minutes"] == 300
    assert plan["scheduled_minutes"] == 120
    assert any("Overloaded" in w for w in plan["warnings"])
    by = {t["title"]: t for t in plan["tasks"]}
    assert by["Big"]["status"] == "partial" and "Deadline conflict" in by["Big"]["reason"]
    assert by["Small"]["status"] == "unscheduled"
    # nothing was deleted or completed
    assert client.get("/api/tasks").json()["total"] == 2


def test_missed_work_recovery_flow(client, subject):
    """The product's main workflow: plan -> miss a session -> mark missed -> re-plan."""
    t = mk_task(client, subject, "Lab report", "2026-03-09T10:00:00Z", estimated_minutes=120)
    set_availability(client, {d: 60 for d in range(7)})
    # an old planned session (yesterday) that never happened
    old = client.post("/api/sessions", json={"subject_id": subject["id"], "task_id": t["id"],
                                             "planned_date": "2026-03-03", "planned_minutes": 120}).json()
    plan = client.post("/api/planner/generate", json={"days": 7}).json()
    assert plan["stale_planned_sessions"] == 1
    assert any("never completed" in w for w in plan["warnings"])
    assert [m["id"] for m in client.get("/api/planner/missed").json()] == [old["id"]]

    r = client.post("/api/planner/mark-missed", json={"session_ids": [old["id"]]})
    assert r.status_code == 200 and r.json()[0]["status"] == "missed"
    # original session preserved (history), original task preserved
    assert client.get(f"/api/sessions/{old['id']}").json()["status"] == "missed"
    assert client.get("/api/tasks").json()["total"] == 1

    plan = client.post("/api/planner/generate", json={"days": 7}).json()
    assert plan["stale_planned_sessions"] == 0
    assert plan["scheduled_minutes"] == 120 and not plan["overloaded"]
    assert all(s["date"] <= "2026-03-09" for s in plan["suggestions"])


def test_completed_study_time_reduces_remaining_work(client, subject):
    t = mk_task(client, subject, "T", "2026-03-09T10:00:00Z", estimated_minutes=100)
    s = client.post("/api/sessions", json={"subject_id": subject["id"], "task_id": t["id"],
                                           "planned_date": "2026-03-04", "planned_minutes": 60}).json()
    client.post(f"/api/sessions/{s['id']}/complete", json={"actual_minutes": 60})
    set_availability(client, {d: 120 for d in range(7)})
    plan = client.post("/api/planner/generate", json={"days": 7}).json()
    assert plan["tasks"][0]["remaining_minutes"] == 40


def test_existing_sessions_use_up_daily_capacity(client, subject):
    t = mk_task(client, subject, "T", "2026-03-04T23:00:00Z", estimated_minutes=60)  # due today
    other_t = mk_task(client, subject, "Other", estimated_minutes=10)
    set_availability(client, {2: 60})
    client.post("/api/sessions", json={"subject_id": subject["id"], "task_id": other_t["id"],
                                       "planned_date": "2026-03-04", "planned_minutes": 50})
    plan = client.post("/api/planner/generate", json={"days": 3}).json()
    assert plan["days"][0]["free_minutes"] == 10
    r = {x["title"]: x for x in plan["tasks"]}
    assert r["T"]["scheduled_minutes"] == 10 and r["T"]["counts_as_shortfall"]


def test_accept_validation_and_isolation(client, other, subject):
    t = mk_task(client, subject, "T")
    ok = {"task_id": t["id"], "date": "2026-03-05", "minutes": 30}
    assert other.post("/api/planner/accept", json={"items": [ok]}).status_code == 404
    assert client.post("/api/planner/accept", json={"items": []}).status_code == 422
    assert client.post("/api/planner/accept", json={"items": [{**ok, "minutes": 0}]}).status_code == 422
    assert client.post("/api/planner/accept", json={"items": [{**ok, "date": "2026-03-01"}]}).status_code == 422
    client.post(f"/api/tasks/{t['id']}/complete")
    assert client.post("/api/planner/accept", json={"items": [ok]}).status_code == 409
    assert client.get("/api/sessions").json() == []  # failed accepts saved nothing


def test_accept_is_all_or_nothing(client, subject):
    t = mk_task(client, subject, "T")
    items = [{"task_id": t["id"], "date": "2026-03-05", "minutes": 30},
             {"task_id": t["id"], "date": "2026-03-01", "minutes": 30}]  # second is in the past
    assert client.post("/api/planner/accept", json={"items": items}).status_code == 422
    assert client.get("/api/sessions").json() == []


def test_cannot_mark_other_users_or_completed_sessions_missed(client, other, subject):
    s = client.post("/api/sessions", json={"subject_id": subject["id"], "planned_date": "2026-03-03",
                                           "planned_minutes": 30}).json()
    assert other.post("/api/planner/mark-missed", json={"session_ids": [s["id"]]}).status_code == 404
    client.post(f"/api/sessions/{s['id']}/complete")
    assert client.post("/api/planner/mark-missed", json={"session_ids": [s["id"]]}).status_code == 409


def test_unhandled_errors_do_not_leak_details(client, monkeypatch):
    from app.routers import subjects
    monkeypatch.setattr(subjects, "_with_counts", lambda *a, **k: 1 / 0)
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app, raise_server_exceptions=False)
    c.cookies.update(client.cookies)
    r = c.get("/api/subjects")
    assert r.status_code == 500 and r.json() == {"detail": "Internal server error"}
