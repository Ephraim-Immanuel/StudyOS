from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_now, get_owned
from app.models import StudySession, Subject, Task, User
from app.schemas import (SessionComplete, SessionCreate, SessionOut, SessionStatus,
                         SessionSummary, SessionUpdate)
from app.services.timeutil import local_today

router = APIRouter(prefix="/api/sessions", tags=["study sessions"])


def _check_links(db: Session, user: User, subject_id: int, task_id: int | None) -> None:
    get_owned(db, Subject, subject_id, user, "Subject")
    if task_id is not None:
        task = get_owned(db, Task, task_id, user, "Task")
        if task.subject_id != subject_id:
            raise HTTPException(422, "The chosen task does not belong to the chosen subject")


@router.get("", response_model=list[SessionOut])
def list_sessions(
    status_: SessionStatus | None = Query(default=None, alias="status"),
    subject_id: int | None = None,
    task_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conds = [StudySession.user_id == user.id]
    if status_:
        conds.append(StudySession.status == status_)
    if subject_id:
        conds.append(StudySession.subject_id == subject_id)
    if task_id:
        conds.append(StudySession.task_id == task_id)
    if date_from:
        conds.append(StudySession.planned_date >= date_from)
    if date_to:
        conds.append(StudySession.planned_date <= date_to)
    return list(db.scalars(select(StudySession).where(*conds)
                           .order_by(StudySession.planned_date.desc(), StudySession.id.desc()).limit(limit)))


# NOTE: declared BEFORE "/{session_id}" so "summary" is not parsed as an id.
@router.get("/summary", response_model=SessionSummary)
def summary(date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db),
            user: User = Depends(get_current_user), now: datetime = Depends(get_now)):
    today = local_today(user, now)
    date_to = date_to or today
    date_from = date_from or date_to - timedelta(days=6)
    if date_from > date_to:
        raise HTTPException(422, "date_from must not be after date_to")
    rows = list(db.scalars(select(StudySession).where(
        StudySession.user_id == user.id, StudySession.planned_date >= date_from,
        StudySession.planned_date <= date_to)))
    return SessionSummary(
        date_from=date_from, date_to=date_to,
        planned_minutes=sum(s.planned_minutes for s in rows),
        completed_minutes=sum(s.actual_minutes or 0 for s in rows if s.status == "completed"),
        missed_minutes=sum(s.planned_minutes for s in rows if s.status == "missed"),
        session_count=len(rows),
    )


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(data: SessionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _check_links(db, user, data.subject_id, data.task_id)
    session = StudySession(user_id=user.id, source="manual", **data.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_owned(db, StudySession, session_id, user, "Study session")


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(session_id: int, data: SessionUpdate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    session = get_owned(db, StudySession, session_id, user, "Study session")
    changes = data.model_dump(exclude_unset=True)
    for required in ("subject_id", "planned_date", "planned_minutes", "status"):
        if required in changes and changes[required] is None:
            raise HTTPException(422, f"{required} cannot be null")
    _check_links(db, user, changes.get("subject_id", session.subject_id),
                 changes["task_id"] if "task_id" in changes else session.task_id)
    for key, value in changes.items():
        setattr(session, key, value)
    if session.status != "completed":
        session.actual_minutes = None
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/complete", response_model=SessionOut)
def complete_session(session_id: int, data: SessionComplete | None = None, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    session = get_owned(db, StudySession, session_id, user, "Study session")
    actual = data.actual_minutes if data and data.actual_minutes is not None else session.planned_minutes
    session.status = "completed"
    session.actual_minutes = actual
    db.commit()
    db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.delete(get_owned(db, StudySession, session_id, user, "Study session"))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
