"""Shared queries: how much of each task is already studied / already planned."""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import StudySession, Task


def task_progress(db: Session, user_id: int, today: date) -> dict[int, tuple[int, int]]:
    """task_id -> (completed_minutes, planned_minutes_from_today_on).

    * completed  = actual minutes of COMPLETED sessions linked to the task
    * planned    = planned minutes of PLANNED sessions dated today or later
    MISSED sessions and PLANNED sessions in the past count as neither, so the
    planner treats that work as still to do.
    """
    done = dict(db.execute(
        select(StudySession.task_id, func.coalesce(func.sum(StudySession.actual_minutes), 0))
        .where(StudySession.user_id == user_id, StudySession.status == "completed",
               StudySession.task_id.is_not(None))
        .group_by(StudySession.task_id)
    ).all())
    planned = dict(db.execute(
        select(StudySession.task_id, func.coalesce(func.sum(StudySession.planned_minutes), 0))
        .where(StudySession.user_id == user_id, StudySession.status == "planned",
               StudySession.task_id.is_not(None), StudySession.planned_date >= today)
        .group_by(StudySession.task_id)
    ).all())
    ids = set(done) | set(planned)
    return {i: (int(done.get(i, 0)), int(planned.get(i, 0))) for i in ids}


def remaining_to_study(task: Task, progress: dict[int, tuple[int, int]]) -> int:
    """Minutes of this task that still need study time (not yet done)."""
    done, _ = progress.get(task.id, (0, 0))
    return max(0, task.estimated_minutes - done)


def remaining_to_schedule(task: Task, progress: dict[int, tuple[int, int]]) -> int:
    """Minutes of this task that still need a planned slot."""
    done, planned = progress.get(task.id, (0, 0))
    return max(0, task.estimated_minutes - done - planned)
