"""Unit tests for the pure planning algorithm (no database, no HTTP)."""
from datetime import date, timedelta

from app.services.planner import (PlanExam, PlanTask, exam_points, generate_plan, urgency_points,
                                  window_dates, workload_points)

TODAY = date(2026, 3, 4)


def free(*minutes_per_day):
    return {TODAY + timedelta(days=i): m for i, m in enumerate(minutes_per_day)}


def task(id, due_in=None, prio="medium", mins=60, subject=1):
    due = TODAY + timedelta(days=due_in) if due_in is not None else None
    return PlanTask(id=id, title=f"T{id}", subject_id=subject, due_date=due, priority=prio, remaining_minutes=mins)


def by_task(plan):
    return {r.task_id: r for r in plan.tasks}


def test_simple_plan_fits_everything():
    plan = generate_plan([task(1, due_in=2, mins=60)], [], free(60, 60, 60), TODAY)
    assert not plan.overloaded and plan.shortfall_minutes == 0
    assert by_task(plan)[1].status == "scheduled"
    assert sum(s.minutes for s in plan.suggestions) == 60
    # earliest-fit: work starts today, not at the deadline
    assert plan.suggestions[0].date == TODAY


def test_capacity_is_never_exceeded():
    tasks = [task(i, due_in=3, mins=50) for i in range(1, 6)]
    plan = generate_plan(tasks, [], free(60, 60, 60, 60), TODAY)
    for day in plan.days:
        assert day.allocated_minutes <= day.free_minutes


def test_nothing_is_scheduled_after_its_deadline():
    plan = generate_plan([task(1, due_in=1, mins=100)], [], free(60, 60, 60, 60), TODAY)
    assert all(s.date <= TODAY + timedelta(days=1) for s in plan.suggestions)


def test_overload_squeezes_out_lowest_score_first():
    high = task(1, due_in=1, prio="high", mins=60)
    low = task(2, due_in=1, prio="low", mins=60)
    plan = generate_plan([low, high], [], free(60, 30), TODAY)  # only 90 min before the deadline
    r = by_task(plan)
    assert r[1].status == "scheduled"
    assert r[2].status == "partial" and r[2].scheduled_minutes == 30
    assert plan.overloaded and plan.shortfall_minutes == 30
    assert "30" in r[2].reason and "Deadline conflict" in r[2].reason


def test_earlier_deadline_task_not_starved_by_higher_scored_task():
    """A (high, due day 2, 120 min) vs B (low, due day 1, 60 min); 60 min/day.
    Naive earliest-fit by score would give A days 0-1 and miss B. This must not happen."""
    a = task(1, due_in=2, prio="high", mins=120)
    b = task(2, due_in=1, prio="low", mins=60)
    plan = generate_plan([a, b], [], free(60, 60, 60), TODAY)
    assert not plan.overloaded
    r = by_task(plan)
    assert r[1].status == "scheduled" and r[2].status == "scheduled"
    b_days = [s.date for s in plan.suggestions if s.task_id == 2]
    assert all(d <= TODAY + timedelta(days=1) for d in b_days)


def test_overdue_task_is_flagged_and_still_scheduled_asap():
    plan = generate_plan([task(1, due_in=-3, mins=45)], [], free(60, 60), TODAY)
    r = by_task(plan)[1]
    assert r.overdue and r.status == "scheduled"
    assert plan.suggestions[0].date == TODAY
    assert "already passed" in r.reason


def test_overdue_task_that_cannot_fit_counts_as_shortfall():
    plan = generate_plan([task(1, due_in=-1, mins=500)], [], free(60, 60), TODAY)
    assert plan.overloaded and plan.shortfall_minutes == 380


def test_deadline_beyond_window_is_deferred_not_a_shortfall():
    plan = generate_plan([task(1, due_in=20, mins=300)], [], free(60, 60), TODAY)
    r = by_task(plan)[1]
    assert r.status == "partial" and r.scheduled_minutes == 120
    assert not plan.overloaded and plan.shortfall_minutes == 0 and plan.deferred_minutes == 180


def test_no_capacity_at_all():
    plan = generate_plan([task(1, due_in=2)], [], free(0, 0, 0), TODAY)
    assert plan.suggestions == []
    assert by_task(plan)[1].status == "unscheduled"
    assert any("availability" in w for w in plan.warnings)


def test_fully_planned_tasks_are_skipped():
    plan = generate_plan([task(1, due_in=2, mins=0)], [], free(60), TODAY)
    assert plan.tasks == [] and plan.suggestions == []


def test_exam_raises_score_of_same_subject_only():
    exams = [PlanExam(subject_id=1, exam_date=TODAY + timedelta(days=2), importance=5)]
    plan = generate_plan([task(1, due_in=10, subject=1), task(2, due_in=10, subject=2)], exams, free(60), TODAY)
    r = by_task(plan)
    assert r[1].breakdown.exam > 0 and r[2].breakdown.exam == 0
    assert r[1].score > r[2].score


def test_scoring_components():
    assert urgency_points(None, TODAY) == 2.0
    assert urgency_points(TODAY - timedelta(days=5), TODAY) == 45.0
    assert urgency_points(TODAY + timedelta(days=14), TODAY) == 0.0
    assert urgency_points(TODAY + timedelta(days=1), TODAY) > urgency_points(TODAY + timedelta(days=5), TODAY)
    assert exam_points(1, [PlanExam(1, TODAY + timedelta(days=30), 5)], TODAY) == 0.0  # too far away
    assert workload_points(10_000) == 10.0


def test_plan_is_deterministic():
    tasks = [task(i, due_in=i % 4, prio=["low", "medium", "high"][i % 3], mins=30 + 10 * i) for i in range(1, 9)]
    a = generate_plan(tasks, [], free(90, 90, 90, 90, 90), TODAY)
    b = generate_plan(list(reversed(tasks)), [], free(90, 90, 90, 90, 90), TODAY)
    assert [(s.task_id, s.date, s.minutes) for s in a.suggestions] == [(s.task_id, s.date, s.minutes) for s in b.suggestions]


def test_window_dates():
    assert window_dates(TODAY, 3) == [TODAY, TODAY + timedelta(days=1), TODAY + timedelta(days=2)]
