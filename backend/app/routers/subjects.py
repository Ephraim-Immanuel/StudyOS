from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_owned
from app.models import Exam, StudySession, Subject, Task, User
from app.schemas import SubjectCreate, SubjectOut, SubjectUpdate

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


def _with_counts(db: Session, user: User, subjects: list[Subject]) -> list[SubjectOut]:
    """Counts come from 3 grouped queries (not one query per subject: avoids N+1)."""
    tasks = {r[0]: (r[1], r[2]) for r in db.execute(
        select(Task.subject_id, func.count(),
               func.sum(case((Task.status != "completed", 1), else_=0)))
        .where(Task.user_id == user.id).group_by(Task.subject_id))}
    exams = dict(db.execute(select(Exam.subject_id, func.count())
                            .where(Exam.user_id == user.id).group_by(Exam.subject_id)).all())
    sessions = dict(db.execute(select(StudySession.subject_id, func.count())
                               .where(StudySession.user_id == user.id)
                               .group_by(StudySession.subject_id)).all())
    out = []
    for s in subjects:
        item = SubjectOut.model_validate(s)
        item.total_tasks, item.open_tasks = tasks.get(s.id, (0, 0))
        item.open_tasks = int(item.open_tasks or 0)
        item.exam_count = exams.get(s.id, 0)
        item.session_count = sessions.get(s.id, 0)
        out.append(item)
    return out


@router.get("", response_model=list[SubjectOut])
def list_subjects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    subjects = list(db.scalars(select(Subject).where(Subject.user_id == user.id).order_by(Subject.name)))
    return _with_counts(db, user, subjects)


@router.post("", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
def create_subject(data: SubjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    subject = Subject(user_id=user.id, **data.model_dump())
    db.add(subject)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have a subject with that name")
    return _with_counts(db, user, [subject])[0]


@router.get("/{subject_id}", response_model=SubjectOut)
def get_subject(subject_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    subject = get_owned(db, Subject, subject_id, user, "Subject")
    return _with_counts(db, user, [subject])[0]


@router.patch("/{subject_id}", response_model=SubjectOut)
def update_subject(subject_id: int, data: SubjectUpdate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    subject = get_owned(db, Subject, subject_id, user, "Subject")
    for key, value in data.model_dump(exclude_unset=True).items():
        if key == "name" and value is None:
            continue
        setattr(subject, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have a subject with that name")
    return _with_counts(db, user, [subject])[0]


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(subject_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Refuses when tasks, exams or sessions still reference the subject."""
    subject = get_owned(db, Subject, subject_id, user, "Subject")
    c = _with_counts(db, user, [subject])[0]
    if c.total_tasks or c.exam_count or c.session_count:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"This subject still has {c.total_tasks} task(s), {c.exam_count} exam(s) and "
            f"{c.session_count} study session(s). Delete or move them first.",
        )
    db.delete(subject)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
