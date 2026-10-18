import { Link } from 'react-router-dom'
import { dashboard, tasks as tasksApi } from '../api'
import { EmptyState, ErrorBox, Loading, Minutes, PageHeader, PriorityBadge, SubjectDot } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { formatDateOnly, formatDateTime, percent, shortWeekday, weekdayIndex } from '../lib/format'
import { useAsync } from '../lib/useAsync'

function TaskRow({ t, tz, onComplete }) {
  return (
    <li>
      <span><strong>{t.title}</strong> <SubjectDot subject={t.subject} /></span>
      <span className="meta">
        <PriorityBadge value={t.priority} /> <span className="muted">{formatDateTime(t.due_at, tz)} · <Minutes value={t.estimated_minutes} /></span>
        <button className="btn btn-small btn-success" onClick={() => onComplete(t)} aria-label={`Complete ${t.title}`}>✓</button>
      </span>
    </li>
  )
}

function Section({ title, count, children, empty }) {
  return (
    <section className="card">
      <h2>{title}{count !== undefined && <span className="count">{count}</span>}</h2>
      {count === 0 ? <p className="muted">{empty}</p> : children}
    </section>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const toast = useToast()
  const { data: d, error, loading, reload } = useAsync(() => dashboard.get())

  async function complete(t) {
    try { await tasksApi.complete(t.id); toast.success('Task completed'); reload() } catch (err) { toast.error(err.message) }
  }

  if (loading && !d) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />

  const { stats, study_time: st } = d
  const maxBar = Math.max(60, ...d.workload.map((w) => Math.max(w.task_minutes_due, w.planned_study_minutes, w.available_minutes)))
  const studyPct = st.planned_minutes ? Math.min(100, Math.round((st.completed_minutes / st.planned_minutes) * 100)) : 0
  const brandNew = stats.total === 0

  return (
    <>
      <PageHeader title={`Hello, ${user.name.split(' ')[0]}`} subtitle={formatDateOnly(d.today, { weekday: 'long', day: 'numeric', month: 'long' })}
        actions={<Link className="btn btn-primary" to="/planner">Open planner</Link>} />

      {brandNew && (
        <EmptyState title="Welcome to StudyOS" action={<Link className="btn btn-primary" to="/subjects">Add your first subject</Link>}>
          Start by adding a subject, then tasks and exams. Set your weekly availability in the Planner to get a study plan.
        </EmptyState>
      )}

      <div className="stat-grid">
        <div className="card stat"><span className="stat-num">{stats.total}</span><span className="muted">Total tasks</span></div>
        <div className="card stat"><span className="stat-num">{percent(stats.completion_rate)}</span><span className="muted">Completed ({stats.completed})</span></div>
        <div className="card stat"><span className="stat-num">{stats.pending + stats.in_progress}</span><span className="muted">Incomplete</span></div>
        <div className={`card stat ${stats.overdue ? 'stat-alert' : ''}`}><span className="stat-num">{stats.overdue}</span><span className="muted">Overdue</span></div>
      </div>

      <div className="two-col">
        <Section title="Overdue" count={d.overdue.length} empty="Nothing overdue. 🎉">
          <ul className="list">{d.overdue.map((t) => <TaskRow key={t.id} t={t} tz={user.timezone} onComplete={complete} />)}</ul>
        </Section>
        <Section title="Due today" count={d.due_today.length} empty="Nothing else due today.">
          <ul className="list">{d.due_today.map((t) => <TaskRow key={t.id} t={t} tz={user.timezone} onComplete={complete} />)}</ul>
        </Section>
        <Section title="Upcoming (next 7 days)" count={d.upcoming.length} empty="No deadlines in the next 7 days.">
          <ul className="list">{d.upcoming.map((t) => <TaskRow key={t.id} t={t} tz={user.timezone} onComplete={complete} />)}</ul>
        </Section>
        <Section title="Upcoming exams" count={d.exams.length} empty="No exams in the next 30 days.">
          <ul className="list">
            {d.exams.map((e) => (
              <li key={e.id}>
                <span><strong>{e.title}</strong> <SubjectDot subject={e.subject} /></span>
                <span className="meta">{formatDateOnly(e.exam_date)} · {e.days_until === 0 ? 'today' : `${e.days_until} d`} · prep <Minutes value={e.prep_minutes} /></span>
              </li>
            ))}
          </ul>
        </Section>
      </div>

      <section className="card">
        <h2>Study time, last 7 days</h2>
        <div className="progress" role="progressbar" aria-valuenow={studyPct} aria-valuemin="0" aria-valuemax="100"><div style={{ width: `${studyPct}%` }} /></div>
        <p><strong><Minutes value={st.completed_minutes} /></strong> completed of <strong><Minutes value={st.planned_minutes} /></strong> planned</p>
        {st.planned_minutes === 0 && <p className="muted">No sessions planned in this period yet.</p>}
      </section>

      <section className="card">
        <h2>Workload: next 7 days</h2>
        <div className="legend"><span className="lg lg-due">Task effort due</span><span className="lg lg-plan">Planned study</span><span className="lg lg-avail">Available time</span></div>
        <div className="bars">
          {d.workload.map((w) => (
            <div key={w.date} className="bar-col" title={`${w.date}: due ${w.task_minutes_due} min, planned ${w.planned_study_minutes} min, available ${w.available_minutes} min`}>
              <div className="bar-group">
                <div className="bar lg-due" style={{ height: `${(w.task_minutes_due / maxBar) * 100}%` }} />
                <div className="bar lg-plan" style={{ height: `${(w.planned_study_minutes / maxBar) * 100}%` }} />
                <div className="bar lg-avail" style={{ height: `${(w.available_minutes / maxBar) * 100}%` }} />
              </div>
              <span className="bar-label">{shortWeekday(weekdayIndex(w.date))}</span>
              <span className="bar-sub">{w.task_minutes_due}m due</span>
            </div>
          ))}
        </div>
        {d.workload.every((w) => w.available_minutes === 0) && <p className="muted">Set your available study hours in the <Link to="/planner">Planner</Link> to compare workload with capacity.</p>}
      </section>
    </>
  )
}
