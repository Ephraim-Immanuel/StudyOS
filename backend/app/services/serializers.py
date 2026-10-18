"""Turn ORM objects into response schemas, filling the computed fields."""
from datetime import date, datetime

from app.models import Exam, Task
from app.schemas import ExamOut, TaskOut


def task_out(task: Task, now: datetime) -> TaskOut:
    out = TaskOut.model_validate(task)
    out.is_overdue = task.status != "completed" and task.due_at is not None and task.due_at < now
    return out


def exam_out(exam: Exam, today: date, open_task_minutes: list[int]) -> ExamOut:
    out = ExamOut.model_validate(exam)
    out.days_until = (exam.exam_date - today).days
    out.open_tasks = len(open_task_minutes)
    out.prep_minutes = sum(open_task_minutes)
    return out
