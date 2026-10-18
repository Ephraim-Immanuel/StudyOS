"""Builds the dashboard numbers. Everything is computed from database rows."""
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Availability, Exam, StudySession, Task, User
from app.services.serializers import exam_out, task_out
from app.services.timeutil import day_bounds_utc, local_today, to_local_date
from app.services.workload import remaining_to_study, task_progress


def build_dashboard(db: Session, user: User, now: datetime) -> dict:
    today = local_today(user, now)
    _, today_end = day_bounds_utc(today, user)
    _, week_end = day_bounds_utc(today + timedelta(days=7), user)  # exclusive: today+7 days

    open_tasks = list(db.scalars(
        select(Task).where(Task.user_id == user.id, Task.status != "completed")
        .order_by(Task.due_at.asc().nulls_last(), Task.id)
    ))
    overdue = [t for t in open_tasks if t.due_at and t.due_at < now]
    due_today = [t for t in open_tasks if t.due_at and now <= t.due_at < today_end]
    upcoming = [t for t in open_tasks if t.due_at and today_end <= t.due_at < week_end]

    counts = dict(db.execute(
        select(Task.status, func.count()).where(Task.user_id == user.id).group_by(Task.status)
    ).all())
    total = sum(counts.values())
    stats = {
        "total": total,
        "pending": counts.get("pending", 0),
        "in_progress": counts.get("in_progress", 0),
        "completed": counts.get("completed", 0),
        "overdue": len(overdue),
        "completion_rate": round(counts.get("completed", 0) / total, 3) if total else 0.0,
    }

    # exams in the next 30 days, with unfinished-task effort per subject
    progress = task_progress(db, user.id, today)
    prep: dict[int, list[int]] = {}
    for t in open_tasks:
        prep.setdefault(t.subject_id, []).append(remaining_to_study(t, progress))
    exams = list(db.scalars(
        select(Exam).where(Exam.user_id == user.id, Exam.exam_date >= today,
                           Exam.exam_date <= today + timedelta(days=30))
        .order_by(Exam.exam_date, Exam.id).limit(5)
    ))

    # study time over the last 7 days (today included)
    start = today - timedelta(days=6)
    sessions = list(db.scalars(
        select(StudySession).where(StudySession.user_id == user.id,
                                   StudySession.planned_date >= start,
                                   StudySession.planned_date <= today)
    ))
    study_time = {
        "date_from": start, "date_to": today,
        "planned_minutes": sum(s.planned_minutes for s in sessions),
        "completed_minutes": sum(s.actual_minutes or 0 for s in sessions if s.status == "completed"),
    }

    # next 7 days workload
    avail = {a.weekday: a.minutes for a in db.scalars(select(Availability).where(Availability.user_id == user.id))}
    future_sessions = list(db.scalars(
        select(StudySession).where(StudySession.user_id == user.id, StudySession.status == "planned",
                                   StudySession.planned_date >= today,
                                   StudySession.planned_date < today + timedelta(days=7))
    ))
    workload = []
    for i in range(7):
        d = today + timedelta(days=i)
        workload.append({
            "date": d,
            "task_minutes_due": sum(remaining_to_study(t, progress) for t in open_tasks
                                    if t.due_at and to_local_date(t.due_at, user) == d),
            "planned_study_minutes": sum(s.planned_minutes for s in future_sessions if s.planned_date == d),
            "available_minutes": avail.get(d.weekday(), 0),
        })

    return {
        "today": today,
        "due_today": [task_out(t, now) for t in due_today],
        "overdue": [task_out(t, now) for t in overdue[:20]],
        "upcoming": [task_out(t, now) for t in upcoming[:10]],
        "exams": [exam_out(e, today, prep.get(e.subject_id, [])) for e in exams],
        "stats": stats,
        "study_time": study_time,
        "workload": workload,
    }
