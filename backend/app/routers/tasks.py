from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_now, get_owned
from app.models import Subject, Task, User
from app.schemas import Priority, TaskCreate, TaskOut, TaskPage, TaskStatus, TaskUpdate
from app.services.serializers import task_out
from app.services.timeutil import day_bounds_utc, ensure_aware, local_today

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _apply_status(task: Task, new_status: str, now: datetime) -> None:
    task.status = new_status
    task.completed_at = now if new_status == "completed" else None


@router.get("", response_model=TaskPage)
def list_tasks(
    status_: TaskStatus | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    subject_id: int | None = None,
    due: Literal["overdue", "today", "upcoming", "none"] | None = Query(
        default=None, description="overdue | today | upcoming (next 7 days) | none (no due date)"),
    q: str | None = Query(default=None, max_length=100),
    sort: Literal["due_at", "priority", "created_at"] = "due_at",
    order: Literal["asc", "desc"] = "asc",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    now: datetime = Depends(get_now),
):
    conds = [Task.user_id == user.id]
    if status_:
        conds.append(Task.status == status_)
    if priority:
        conds.append(Task.priority == priority)
    if subject_id:
        conds.append(Task.subject_id == subject_id)
    if q and q.strip():
        conds.append(Task.title.ilike(f"%{q.strip()}%"))
    if due:
        today = local_today(user, now)
        start, end = day_bounds_utc(today, user)
        _, week_end = day_bounds_utc(today + timedelta(days=7), user)
        if due == "overdue":
            conds += [Task.status != "completed", Task.due_at < now]
        elif due == "today":
            conds += [Task.due_at >= start, Task.due_at < end]
        elif due == "upcoming":
            conds += [Task.status != "completed", Task.due_at >= now, Task.due_at < week_end]
        else:
            conds.append(Task.due_at.is_(None))

    total = db.scalar(select(func.count()).select_from(Task).where(*conds)) or 0

    if sort == "priority":
        rank = case((Task.priority == "high", 3), (Task.priority == "medium", 2), else_=1)
        key = rank.asc() if order == "asc" else rank.desc()
        ordering = [key, Task.due_at.asc().nulls_last(), Task.id]
    elif sort == "created_at":
        ordering = [Task.created_at.asc() if order == "asc" else Task.created_at.desc(), Task.id]
    else:
        key = Task.due_at.asc() if order == "asc" else Task.due_at.desc()
        ordering = [key.nulls_last(), Task.id]

    rows = db.scalars(select(Task).where(*conds).order_by(*ordering).limit(limit).offset(offset))
    return TaskPage(items=[task_out(t, now) for t in rows], total=total, limit=limit, offset=offset)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user),
                now: datetime = Depends(get_now)):
    get_owned(db, Subject, data.subject_id, user, "Subject")
    task = Task(user_id=user.id, **data.model_dump(exclude={"due_at", "status"}),
                due_at=ensure_aware(data.due_at, user) if data.due_at else None)
    _apply_status(task, data.status, now)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task_out(task, now)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user),
             now: datetime = Depends(get_now)):
    return task_out(get_owned(db, Task, task_id, user, "Task"), now)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user), now: datetime = Depends(get_now)):
    task = get_owned(db, Task, task_id, user, "Task")
    changes = data.model_dump(exclude_unset=True)
    for required in ("title", "subject_id", "priority", "estimated_minutes", "status"):
        if required in changes and changes[required] is None:
            raise HTTPException(422, f"{required} cannot be null")
    if "subject_id" in changes:
        get_owned(db, Subject, changes["subject_id"], user, "Subject")
    if "due_at" in changes:
        task.due_at = ensure_aware(changes.pop("due_at"), user) if changes["due_at"] else None
    if "status" in changes:
        _apply_status(task, changes.pop("status"), now)
    for key, value in changes.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task_out(task, now)


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user),
                  now: datetime = Depends(get_now)):
    task = get_owned(db, Task, task_id, user, "Task")
    _apply_status(task, "completed", now)
    db.commit()
    db.refresh(task)
    return task_out(task, now)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = get_owned(db, Task, task_id, user, "Task")
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
