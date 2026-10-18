from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_now, get_owned
from app.models import Exam, Subject, Task, User
from app.schemas import ExamCreate, ExamOut, ExamUpdate
from app.services.serializers import exam_out
from app.services.timeutil import local_today
from app.services.workload import remaining_to_study, task_progress

router = APIRouter(prefix="/api/exams", tags=["exams"])


def _prep_minutes(db: Session, user: User, today) -> dict[int, list[int]]:
    progress = task_progress(db, user.id, today)
    prep: dict[int, list[int]] = {}
    for t in db.scalars(select(Task).where(Task.user_id == user.id, Task.status != "completed")):
        prep.setdefault(t.subject_id, []).append(remaining_to_study(t, progress))
    return prep


@router.get("", response_model=list[ExamOut])
def list_exams(
    subject_id: int | None = None,
    upcoming_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    now: datetime = Depends(get_now),
):
    today = local_today(user, now)
    conds = [Exam.user_id == user.id]
    if subject_id:
        conds.append(Exam.subject_id == subject_id)
    if upcoming_only:
        conds.append(Exam.exam_date >= today)
    exams = db.scalars(select(Exam).where(*conds).order_by(Exam.exam_date, Exam.id))
    prep = _prep_minutes(db, user, today)
    return [exam_out(e, today, prep.get(e.subject_id, [])) for e in exams]


def _one(db: Session, user: User, exam: Exam, now: datetime) -> ExamOut:
    today = local_today(user, now)
    return exam_out(exam, today, _prep_minutes(db, user, today).get(exam.subject_id, []))


@router.post("", response_model=ExamOut, status_code=status.HTTP_201_CREATED)
def create_exam(data: ExamCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user),
                now: datetime = Depends(get_now)):
    get_owned(db, Subject, data.subject_id, user, "Subject")
    exam = Exam(user_id=user.id, **data.model_dump())
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return _one(db, user, exam, now)


@router.get("/{exam_id}", response_model=ExamOut)
def get_exam(exam_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user),
             now: datetime = Depends(get_now)):
    return _one(db, user, get_owned(db, Exam, exam_id, user, "Exam"), now)


@router.patch("/{exam_id}", response_model=ExamOut)
def update_exam(exam_id: int, data: ExamUpdate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user), now: datetime = Depends(get_now)):
    exam = get_owned(db, Exam, exam_id, user, "Exam")
    changes = data.model_dump(exclude_unset=True)
    for required in ("title", "subject_id", "exam_date", "importance"):
        if required in changes and changes[required] is None:
            raise HTTPException(422, f"{required} cannot be null")
    if "subject_id" in changes:
        get_owned(db, Subject, changes["subject_id"], user, "Subject")
    for key, value in changes.items():
        setattr(exam, key, value)
    db.commit()
    db.refresh(exam)
    return _one(db, user, exam, now)


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(exam_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.delete(get_owned(db, Exam, exam_id, user, "Exam"))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
