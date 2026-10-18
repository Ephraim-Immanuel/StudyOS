# The planner algorithm

Code: `backend/app/services/planner.py` (pure functions, no database). Inputs are gathered by `backend/app/routers/planner.py::generate`. Tests: `backend/tests/test_planner.py` and `test_dashboard_planner.py`.

**It is a documented heuristic, not an optimal scheduler.**

## Inputs
* **Free minutes per day** for the planning window (7/14/21 days from *today* in the user's timezone) = weekly availability for that weekday **minus** minutes already booked that day (planned sessions + actual minutes of completed sessions).
* **Tasks** that are not completed, each with `remaining_minutes = estimated − completed study − already-planned future study`. *Missed* sessions and planned sessions dated in the past count as neither, so that work is still "to do". Tasks with 0 remaining are skipped.
* **Exams** within the next 14 days.

## Step 1: score each task (0–100)
| Part | Max | Rule |
|---|---|---|
| Urgency | 45 | Overdue or due today = 45; due in *d* days = `45 × (1 − min(d,14)/14)`; no due date = 2 |
| Priority | 30 | low 10, medium 20, high 30 |
| Exam | 15 | Nearest exam in the **same subject** within 14 days: `15 × (importance/5) × (1 − days/14)` |
| Workload | 10 | `10 × min(remaining,240)/240`: bigger tasks get started earlier |

Ranking: score descending; ties → earlier deadline → lower id (so results are deterministic).

## Step 2: admission (who gets time when time is scarce)
Walk the ranking. For each task reserve its minutes on the **latest** days *before its deadline* that still have free time. The window for a task ends on its due date, or at the end of the planning window if it has no deadline, is overdue, or is due later than the window. High-scoring tasks reserve first, so when there isn't enough time the **lowest-scoring** tasks lose out.

## Step 3: placement (when to do it)
Take the admitted minutes and lay them out **earliest-deadline-first**, filling the **earliest** free days. Step 2 proves a valid arrangement exists; this step picks one that starts work as early as possible. (Why two steps? Placing in score order alone can let a high-score task with a later deadline use the early slots that a tight-deadline task needs. `test_earlier_deadline_task_not_starved_by_higher_scored_task` covers it.)

## Output
Per task: score + breakdown, scheduled and unscheduled minutes, status (`scheduled`/`partial`/`unscheduled`), and a plain-English reason. Overall: capacity, demand, scheduled, **shortfall** and **deferred** minutes, per-day allocation, warnings.
* **Shortfall** = unscheduled minutes of tasks that are overdue or due inside the window: "at least this many more minutes are needed before those deadlines". `overloaded = shortfall > 0`.
* **Deferred** = unscheduled minutes of tasks due *after* the window or with no deadline. Not a conflict, just not planned yet.

## Worked example (real output of the code)
Today = Wed 4 Mar. Free time: 60 min on each of Wed–Sat (240 total). Exam: Operating Systems (subject 1), importance 5, on Sat.

| Task | Subject | Due | Priority | Needs | Urgency | Priority | Exam | Workload | **Score** |
|---|---|---|---|---|---|---|---|---|---|
| Lab report | OS | Fri | high | 120 | 38.57 | 30 | 11.79 | 5 | **85.4** |
| Read chapter 5 | OS | Thu | low | 60 | 41.79 | 10 | 11.79 | 2.5 | **66.1** |
| Project draft | other | Sat | medium | 90 | 35.36 | 20 | 0 | 3.75 | **59.1** |

Demand 270 min > capacity 240 min. Admission reserves Lab report (Fri+Thu), Read chapter (Wed), and Project draft gets only the remaining Sat slot. Placement result:

| Day | Session |
|---|---|
| Wed | Read chapter 5: 60 |
| Thu | Lab report: 60 |
| Fri | Lab report: 60 |
| Sat | Project draft: 60 |

Project draft is *partial*: 60 of 90 scheduled; **shortfall 30 min**; `overloaded = true`. Nothing is deleted or completed.

## Review before saving
`POST /api/planner/generate` saves nothing. The user ticks the suggestions to keep and `POST /api/planner/accept` creates `study_sessions` (all-or-nothing transaction, `source='planner'`). Accepting twice is harmless: the second generate sees the planned sessions and suggests nothing new.

## Missed-work recovery
1. `GET /api/planner/missed` lists planned sessions dated before today that were never completed.
2. `POST /api/planner/mark-missed` sets `status='missed'` (history is kept, completed sessions are refused).
3. Generate again: missed minutes count as remaining work, and the algorithm explains what fits and what does not (`test_missed_work_recovery_flow`).

## Limitations and edge cases
* Day granularity only (no clock times); a deadline means "by the end of that calendar day".
* Overdue tasks are placed after tasks that can still meet their deadline (they never displace feasible work), then as early as capacity allows.
* No minimum/maximum block size: a task can be split into small pieces over many days.
* No dependencies, breaks, energy levels, or subject-switching cost.
* Exams only add a score boost; they do not create a hard deadline for a subject's undated tasks.
* The shortfall figure assumes extra time can be added on any day before the deadline.
* Window ends at the horizon: later work is "deferred", not planned.
* Time zone: "today" and due days use the user's profile timezone; changing it changes the plan.
