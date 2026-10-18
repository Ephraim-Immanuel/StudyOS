"""Availability + weekly planner (suggest -> review -> accept) + missed-work recovery."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_now
from app.models import Availability, Exam, StudySession, Task, User
from app.schemas import (AcceptIn, AvailabilityDay, AvailabilityIn, MarkMissedIn, PlanOut,
                         PlanRequest, SessionOut)
from app.services import planner as algo
from app.services.timeutil import local_today, to_local_date
from app.services.workload import remaining_to_schedule, task_progress

router = APIRouter(prefix="/api", tags=["planner"])


def _availability(db: Session, user: User) -> dict[int, int]:
    return {a.weekday: a.minutes for a in db.scalars(select(Availability).where(Availability.user_id == user.id))}


@router.get("/availability", response_model=list[AvailabilityDay])
def get_availability(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    saved = _availability(db, user)
    return [AvailabilityDay(weekday=d, minutes=saved.get(d, 0)) for d in range(7)]


@router.put("/availability", response_model=list[AvailabilityDay])
def put_availability(data: AvailabilityIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = {a.weekday: a for a in db.scalars(select(Availability).where(Availability.user_id == user.id))}
    for day in data.days:
        if day.weekday in rows:
            rows[day.weekday].minutes = day.minutes
        else:
            db.add(Availability(user_id=user.id, weekday=day.weekday, minutes=day.minutes))
    db.commit()
    saved = _availability(db, user)
    return [AvailabilityDay(weekday=d, minutes=saved.get(d, 0)) for d in range(7)]


@router.get("/planner/missed", response_model=list[SessionOut])
def missed_candidates(db: Session = Depends(get_db), user: User = Depends(get_current_user),
                      now: datetime = Depends(get_now)):
    """Planned sessions whose day has passed but were never completed."""
    today = local_today(user, now)
    return list(db.scalars(select(StudySession).where(
        StudySession.user_id == user.id, StudySession.status == "planned",
        StudySession.planned_date < today).order_by(StudySession.planned_date, StudySession.id)))


@router.post("/planner/mark-missed", response_model=list[SessionOut])
def mark_missed(data: MarkMissedIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Marks sessions as missed. Nothing is deleted: the history stays visible."""
    ids = set(data.session_ids)
    rows = list(db.scalars(select(StudySession).where(
        StudySession.user_id == user.id, StudySession.id.in_(ids))))
    if len(rows) != len(ids):
        raise HTTPException(404, "One or more study sessions were not found")
    for s in rows:
        if s.status == "completed":
            raise HTTPException(409, "A completed session cannot be marked as missed")
        s.status = "missed"
        s.actual_minutes = None
    db.commit()
    return rows


@router.post("/planner/generate", response_model=PlanOut)
def generate(data: PlanRequest | None = None, db: Session = Depends(get_db),
             user: User = Depends(get_current_user), now: datetime = Depends(get_now)):
    """Computes a SUGGESTED plan. Nothing is saved; see /planner/accept."""
    data = data or PlanRequest()
    today = local_today(user, now)
    dates = algo.window_dates(today, data.days)
    avail = _availability(db, user)

    # Already-booked time reduces free capacity: planned sessions + completed minutes.
    booked: dict = {d: 0 for d in dates}
    for s in db.scalars(select(StudySession).where(
            StudySession.user_id == user.id, StudySession.planned_date >= dates[0],
            StudySession.planned_date <= dates[-1], StudySession.status.in_(("planned", "completed")))):
        used = (s.actual_minutes or 0) if s.status == "completed" else s.planned_minutes
        booked[s.planned_date] += used
    free = {d: max(0, avail.get(d.weekday(), 0) - booked[d]) for d in dates}

    progress = task_progress(db, user.id, today)
    tasks = [
        algo.PlanTask(
            id=t.id, title=t.title, subject_id=t.subject_id,
            due_date=to_local_date(t.due_at, user) if t.due_at else None,
            priority=t.priority, remaining_minutes=remaining_to_schedule(t, progress))
        for t in db.scalars(select(Task).where(Task.user_id == user.id, Task.status != "completed"))
    ]
    exams = [algo.PlanExam(e.subject_id, e.exam_date, e.importance) for e in db.scalars(
        select(Exam).where(Exam.user_id == user.id, Exam.exam_date >= today,
                           Exam.exam_date <= today + timedelta(days=algo.EXAM_WINDOW_DAYS)))]

    result = algo.generate_plan(tasks, exams, free, today)
    out = PlanOut.model_validate(_to_dict(result))
    out.stale_planned_sessions = len(missed_candidates(db, user, now))
    if out.stale_planned_sessions:
        out.warnings.append(
            f"{out.stale_planned_sessions} older planned session(s) were never completed. "
            "Mark them as missed so their work is re-planned cleanly.")
    return out


def _to_dict(result: algo.PlanResult) -> dict:
    from dataclasses import asdict
    return asdict(result)


@router.post("/planner/accept", response_model=list[SessionOut], status_code=status.HTTP_201_CREATED)
def accept(data: AcceptIn, db: Session = Depends(get_db), user: User = Depends(get_current_user),
           now: datetime = Depends(get_now)):
    """Saves reviewed suggestions as planned study sessions, in ONE transaction.
    Existing tasks and sessions are never modified or deleted."""
    today = local_today(user, now)
    task_ids = {i.task_id for i in data.items}
    tasks = {t.id: t for t in db.scalars(select(Task).where(Task.user_id == user.id, Task.id.in_(task_ids)))}
    if len(tasks) != len(task_ids):
        raise HTTPException(404, "One or more tasks were not found")
    created = []
    for item in data.items:
        task = tasks[item.task_id]
        if task.status == "completed":
            raise HTTPException(409, f"Task '{task.title}' is already completed")
        if item.date < today:
            raise HTTPException(422, "Suggested sessions cannot be in the past")
        s = StudySession(user_id=user.id, subject_id=task.subject_id, task_id=task.id,
                         planned_date=item.date, planned_minutes=item.minutes,
                         status="planned", source="planner")
        db.add(s)
        created.append(s)
    db.commit()
    return created
