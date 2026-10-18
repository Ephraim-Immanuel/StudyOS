"""Pydantic schemas: what the API accepts (…Create/…Update) and returns (…Out)."""
from datetime import date, datetime, time
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Priority = Literal["low", "medium", "high"]
TaskStatus = Literal["pending", "in_progress", "completed"]
SessionStatus = Literal["planned", "completed", "missed"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _check_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        raise ValueError("Unknown timezone (use a name like 'Asia/Kolkata')")
    return value


# ---------- auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=72)
    timezone: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        return v

    @field_validator("password")
    @classmethod
    def bcrypt_limit(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes")
        return v

    @field_validator("timezone")
    @classmethod
    def tz(cls, v: str | None) -> str | None:
        return _check_timezone(v) if v else None


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    timezone: str | None = None

    @field_validator("timezone")
    @classmethod
    def tz(cls, v: str | None) -> str | None:
        return _check_timezone(v) if v else None


class UserOut(ORM):
    id: int
    email: str
    name: str
    timezone: str


# ---------- subjects ----------
class SubjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        return v

    @field_validator("description")
    @classmethod
    def strip_desc(cls, v: str | None) -> str | None:
        return _clean(v)


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        return v


class SubjectBrief(ORM):
    id: int
    name: str
    color: str | None


class SubjectOut(ORM):
    id: int
    name: str
    description: str | None
    color: str | None
    created_at: datetime
    updated_at: datetime
    total_tasks: int = 0
    open_tasks: int = 0
    exam_count: int = 0
    session_count: int = 0


# ---------- tasks ----------
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    subject_id: int
    due_at: datetime | None = None
    priority: Priority = "medium"
    estimated_minutes: int = Field(default=60, ge=1, le=1440)
    status: TaskStatus = "pending"

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be blank")
        return v

    @field_validator("description")
    @classmethod
    def strip_desc(cls, v: str | None) -> str | None:
        return _clean(v)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    subject_id: int | None = None
    due_at: datetime | None = None
    priority: Priority | None = None
    estimated_minutes: int | None = Field(default=None, ge=1, le=1440)
    status: TaskStatus | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be blank")
        return v


class TaskOut(ORM):
    id: int
    title: str
    description: str | None
    subject_id: int
    subject: SubjectBrief
    due_at: datetime | None
    priority: Priority
    estimated_minutes: int
    status: TaskStatus
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # "Overdue" = NOT completed AND due date already passed (filled in by the router).
    is_overdue: bool = False


class TaskPage(BaseModel):
    items: list[TaskOut]
    total: int
    limit: int
    offset: int


# ---------- exams ----------
class ExamCreate(BaseModel):
    subject_id: int
    title: str = Field(min_length=1, max_length=200)
    exam_date: date
    topics: str | None = Field(default=None, max_length=5000)
    importance: int = Field(default=3, ge=1, le=5)

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be blank")
        return v

    @field_validator("topics")
    @classmethod
    def strip_topics(cls, v: str | None) -> str | None:
        return _clean(v)


class ExamUpdate(BaseModel):
    subject_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    exam_date: date | None = None
    topics: str | None = Field(default=None, max_length=5000)
    importance: int | None = Field(default=None, ge=1, le=5)


class ExamOut(ORM):
    id: int
    subject_id: int
    subject: SubjectBrief
    title: str
    exam_date: date
    topics: str | None
    importance: int
    days_until: int = 0  # negative = in the past
    open_tasks: int = 0
    prep_minutes: int = 0  # unfinished task effort in this subject


# ---------- study sessions ----------
class SessionCreate(BaseModel):
    subject_id: int
    task_id: int | None = None
    planned_date: date
    start_time: time | None = None
    planned_minutes: int = Field(ge=1, le=1440)


class SessionUpdate(BaseModel):
    subject_id: int | None = None
    task_id: int | None = None
    planned_date: date | None = None
    start_time: time | None = None
    planned_minutes: int | None = Field(default=None, ge=1, le=1440)
    status: SessionStatus | None = None


class SessionComplete(BaseModel):
    actual_minutes: int | None = Field(default=None, ge=0, le=1440)


class TaskBrief(ORM):
    id: int
    title: str


class SessionOut(ORM):
    id: int
    subject_id: int
    subject: SubjectBrief
    task_id: int | None
    task: TaskBrief | None
    planned_date: date
    start_time: time | None
    planned_minutes: int
    actual_minutes: int | None
    status: SessionStatus
    source: Literal["manual", "planner"]


class SessionSummary(BaseModel):
    date_from: date
    date_to: date
    planned_minutes: int
    completed_minutes: int
    missed_minutes: int
    session_count: int


# ---------- availability & planner ----------
class AvailabilityDay(BaseModel):
    weekday: int = Field(ge=0, le=6)
    minutes: int = Field(ge=0, le=1440)


class AvailabilityIn(BaseModel):
    days: list[AvailabilityDay] = Field(min_length=1, max_length=7)

    @field_validator("days")
    @classmethod
    def unique(cls, v: list[AvailabilityDay]) -> list[AvailabilityDay]:
        if len({d.weekday for d in v}) != len(v):
            raise ValueError("Each weekday may appear only once")
        return v


class PlanRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=28)


class PlanSuggestion(BaseModel):
    task_id: int
    title: str
    subject_id: int
    date: date
    minutes: int


class ScoreBreakdown(BaseModel):
    urgency: float
    priority: float
    exam: float
    workload: float


class PlanTaskResult(BaseModel):
    task_id: int
    title: str
    subject_id: int
    due_date: date | None
    priority: Priority
    remaining_minutes: int
    score: float
    breakdown: ScoreBreakdown
    scheduled_minutes: int
    unscheduled_minutes: int
    status: Literal["scheduled", "partial", "unscheduled"]
    overdue: bool
    counts_as_shortfall: bool
    reason: str


class PlanDay(BaseModel):
    date: date
    free_minutes: int
    allocated_minutes: int


class PlanOut(BaseModel):
    start_date: date
    end_date: date
    suggestions: list[PlanSuggestion]
    tasks: list[PlanTaskResult]
    days: list[PlanDay]
    total_capacity_minutes: int
    total_demand_minutes: int
    scheduled_minutes: int
    shortfall_minutes: int
    deferred_minutes: int
    overloaded: bool
    warnings: list[str]
    stale_planned_sessions: int = 0


class AcceptItem(BaseModel):
    task_id: int
    date: date
    minutes: int = Field(ge=1, le=1440)


class AcceptIn(BaseModel):
    items: list[AcceptItem] = Field(min_length=1, max_length=300)


class MarkMissedIn(BaseModel):
    session_ids: list[int] = Field(min_length=1, max_length=300)


# ---------- dashboard ----------
class StudyTimeStats(BaseModel):
    date_from: date
    date_to: date
    planned_minutes: int
    completed_minutes: int


class WorkloadDay(BaseModel):
    date: date
    task_minutes_due: int
    planned_study_minutes: int
    available_minutes: int


class TaskStats(BaseModel):
    total: int
    pending: int
    in_progress: int
    completed: int
    overdue: int
    completion_rate: float


class DashboardOut(BaseModel):
    today: date
    due_today: list[TaskOut]
    overdue: list[TaskOut]
    upcoming: list[TaskOut]
    exams: list[ExamOut]
    stats: TaskStats
    study_time: StudyTimeStats
    workload: list[WorkloadDay]
