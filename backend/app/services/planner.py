"""The StudyOS planning algorithm.

This module is PURE: it never touches the database or the clock, so it is easy to
test. The routers collect the inputs; this module decides.  Full explanation (with
worked examples and limitations) lives in docs/planner-algorithm.md.

Two phases
----------
1. ADMISSION (priority-driven). Rank tasks by a transparent score. Walk the ranking
   and reserve study minutes for each task on the LATEST days before its deadline
   that still have free capacity. When time is scarce, high-scoring tasks reserve
   first, so low-scoring tasks are the ones that get squeezed out.
2. PLACEMENT (deadline-driven). Take the admitted minutes and lay them out
   earliest-deadline-first, filling the EARLIEST free days. Phase 1 proves that a
   valid arrangement exists; earliest-deadline-first finds one and starts work early.

It is a documented heuristic, not a mathematically optimal scheduler.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

PRIORITY_POINTS = {"low": 10.0, "medium": 20.0, "high": 30.0}  # max 30
URGENCY_MAX = 45.0
EXAM_MAX = 15.0
WORKLOAD_MAX = 10.0
URGENCY_WINDOW_DAYS = 14
EXAM_WINDOW_DAYS = 14
WORKLOAD_CAP_MINUTES = 240
NO_DEADLINE_URGENCY = 2.0


@dataclass
class PlanTask:
    id: int
    title: str
    subject_id: int
    due_date: date | None  # in the user's local calendar
    priority: str
    remaining_minutes: int  # still needs to be scheduled


@dataclass
class PlanExam:
    subject_id: int
    exam_date: date
    importance: int  # 1..5


@dataclass
class Breakdown:
    urgency: float
    priority: float
    exam: float
    workload: float

    @property
    def total(self) -> float:
        return round(self.urgency + self.priority + self.exam + self.workload, 1)


@dataclass
class TaskResult:
    task_id: int
    title: str
    subject_id: int
    due_date: date | None
    priority: str
    remaining_minutes: int
    score: float
    breakdown: Breakdown
    scheduled_minutes: int = 0
    unscheduled_minutes: int = 0
    status: str = "unscheduled"
    overdue: bool = False
    counts_as_shortfall: bool = False
    reason: str = ""


@dataclass
class Suggestion:
    task_id: int
    title: str
    subject_id: int
    date: date
    minutes: int


@dataclass
class DayResult:
    date: date
    free_minutes: int
    allocated_minutes: int = 0


@dataclass
class PlanResult:
    start_date: date
    end_date: date
    suggestions: list[Suggestion] = field(default_factory=list)
    tasks: list[TaskResult] = field(default_factory=list)
    days: list[DayResult] = field(default_factory=list)
    total_capacity_minutes: int = 0
    total_demand_minutes: int = 0
    scheduled_minutes: int = 0
    shortfall_minutes: int = 0
    deferred_minutes: int = 0
    overloaded: bool = False
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- scoring
def urgency_points(due: date | None, today: date) -> float:
    """0..45. Overdue or due today = 45; due in 14+ days = 0; no deadline = 2."""
    if due is None:
        return NO_DEADLINE_URGENCY
    days_left = (due - today).days
    if days_left <= 0:
        return URGENCY_MAX
    return round(URGENCY_MAX * (1 - min(days_left, URGENCY_WINDOW_DAYS) / URGENCY_WINDOW_DAYS), 2)


def exam_points(subject_id: int, exams: list[PlanExam], today: date) -> float:
    """0..15. The nearest, most important exam in the same subject within 14 days."""
    best = 0.0
    for exam in exams:
        if exam.subject_id != subject_id:
            continue
        days = (exam.exam_date - today).days
        if days < 0 or days >= EXAM_WINDOW_DAYS:
            continue
        pts = EXAM_MAX * (exam.importance / 5) * (1 - days / EXAM_WINDOW_DAYS)
        best = max(best, pts)
    return round(best, 2)


def workload_points(remaining_minutes: int) -> float:
    """0..10. Bigger tasks get a small boost so they are started earlier."""
    return round(WORKLOAD_MAX * min(remaining_minutes, WORKLOAD_CAP_MINUTES) / WORKLOAD_CAP_MINUTES, 2)


def score_task(task: PlanTask, exams: list[PlanExam], today: date) -> Breakdown:
    return Breakdown(
        urgency=urgency_points(task.due_date, today),
        priority=PRIORITY_POINTS[task.priority],
        exam=exam_points(task.subject_id, exams, today),
        workload=workload_points(task.remaining_minutes),
    )


# ---------------------------------------------------------------- planning
def generate_plan(
    tasks: list[PlanTask],
    exams: list[PlanExam],
    free_minutes: dict[date, int],
    today: date,
) -> PlanResult:
    """`free_minutes` maps every day of the planning window to the minutes still free
    (availability minus sessions that already exist). Its keys define the window."""
    days = sorted(free_minutes)
    result = PlanResult(start_date=days[0], end_date=days[-1])
    horizon_end = days[-1]
    result.days = [DayResult(d, free_minutes[d]) for d in days]
    result.total_capacity_minutes = sum(free_minutes.values())

    # ---- score and rank (highest first; ties: earlier deadline, then id)
    ranked: list[tuple[PlanTask, TaskResult]] = []
    for t in tasks:
        if t.remaining_minutes <= 0:
            continue
        bd = score_task(t, exams, today)
        res = TaskResult(
            task_id=t.id, title=t.title, subject_id=t.subject_id, due_date=t.due_date,
            priority=t.priority, remaining_minutes=t.remaining_minutes, score=bd.total,
            breakdown=bd, unscheduled_minutes=t.remaining_minutes,
            overdue=t.due_date is not None and t.due_date < today,
        )
        ranked.append((t, res))
    ranked.sort(key=lambda p: (-p[1].score, p[0].due_date or date.max, p[0].id))
    result.total_demand_minutes = sum(t.remaining_minutes for t, _ in ranked)

    def last_day(t: PlanTask, overdue: bool) -> date:
        # The last day work for this task may be placed on.
        if t.due_date is None or overdue or t.due_date > horizon_end:
            return horizon_end
        return t.due_date

    # ---- phase 1: admission (latest-fit, in score order)
    spare = dict(free_minutes)
    admitted: dict[int, int] = {}
    window_end: dict[int, date] = {}
    for t, res in ranked:
        end = last_day(t, res.overdue)
        window_end[t.id] = end
        need = t.remaining_minutes
        got = 0
        for d in reversed([d for d in days if d <= end]):
            take = min(need - got, spare[d])
            if take > 0:
                spare[d] -= take
                got += take
            if got == need:
                break
        admitted[t.id] = got

    # ---- phase 2: placement (earliest-deadline-first, earliest-fit)
    free = dict(free_minutes)
    by_id = {t.id: (t, res) for t, res in ranked}
    order = sorted(ranked, key=lambda p: (window_end[p[0].id], -p[1].score, p[0].id))
    placed: dict[tuple[int, date], int] = {}
    for t, res in order:
        need = admitted[t.id]
        for d in [d for d in days if d <= window_end[t.id]]:
            if need == 0:
                break
            take = min(need, free[d])
            if take > 0:
                free[d] -= take
                need -= take
                placed[(t.id, d)] = placed.get((t.id, d), 0) + take
        res.scheduled_minutes = admitted[t.id] - need

    # ---- explain every task
    for t, res in ranked:
        res.unscheduled_minutes = t.remaining_minutes - res.scheduled_minutes
        if res.unscheduled_minutes == 0:
            res.status = "scheduled"
            res.reason = "Fully scheduled."
            if res.overdue:
                res.reason = "Deadline already passed; scheduled as early as capacity allows."
        else:
            res.status = "partial" if res.scheduled_minutes else "unscheduled"
            short = res.unscheduled_minutes
            if res.overdue:
                res.counts_as_shortfall = True
                res.reason = (f"Deadline already passed and {short} min do not fit in the "
                              f"planning window. Free up time or move the deadline.")
            elif t.due_date is not None and t.due_date <= horizon_end:
                res.counts_as_shortfall = True
                res.reason = (f"Deadline conflict: about {short} min more study time is needed "
                              f"before {t.due_date.isoformat()}.")
            else:
                res.reason = (f"Not enough free time in this window for {short} min; the deadline "
                              f"is later than the window, so it is deferred, not missed.")

    result.tasks = [res for _, res in ranked]
    result.suggestions = sorted(
        (Suggestion(tid, by_id[tid][0].title, by_id[tid][0].subject_id, d, m)
         for (tid, d), m in placed.items()),
        key=lambda s: (s.date, -by_id[s.task_id][1].score, s.task_id),
    )
    for day in result.days:
        day.allocated_minutes = sum(s.minutes for s in result.suggestions if s.date == day.date)
    result.scheduled_minutes = sum(s.minutes for s in result.suggestions)
    result.shortfall_minutes = sum(r.unscheduled_minutes for r in result.tasks if r.counts_as_shortfall)
    result.deferred_minutes = sum(r.unscheduled_minutes for r in result.tasks if not r.counts_as_shortfall)
    result.overloaded = result.shortfall_minutes > 0

    # ---- overall warnings
    if result.total_capacity_minutes == 0:
        result.warnings.append("You have no free study time in this window. Set your weekly availability first.")
    if result.overloaded:
        n = sum(1 for r in result.tasks if r.counts_as_shortfall)
        result.warnings.append(
            f"Overloaded: {n} task(s) cannot fully fit before their deadlines. "
            f"You need at least {result.shortfall_minutes} more minutes of study time "
            f"(on days before those deadlines), or lower-priority work must be dropped or moved."
        )
    return result


def window_dates(start: date, days: int) -> list[date]:
    return [start + timedelta(days=i) for i in range(days)]
