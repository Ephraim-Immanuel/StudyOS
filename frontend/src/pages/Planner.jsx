import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { planner as api } from '../api'
import { EmptyState, ErrorBox, Loading, Minutes, PageHeader, StatusBadge } from '../components/ui'
import { useToast } from '../context/ToastContext'
import { WEEKDAYS, formatDateOnly } from '../lib/format'
import { useAsync } from '../lib/useAsync'

function Availability() {
  const toast = useToast()
  const { data, error, loading, reload } = useAsync(() => api.availability())
  const [minutes, setMinutes] = useState(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => { if (data) setMinutes(data.map((d) => d.minutes)) }, [data])

  async function save(e) {
    e.preventDefault()
    setBusy(true)
    try {
      await api.saveAvailability(minutes.map((m, weekday) => ({ weekday, minutes: Number(m) || 0 })))
      toast.success('Availability saved')
      reload()
    } catch (err) { toast.error(err.message) } finally { setBusy(false) }
  }

  if (loading && !data) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!minutes) return null
  const total = minutes.reduce((a, m) => a + (Number(m) || 0), 0)
  return (
    <form className="card" onSubmit={save}>
      <h2>1. Your weekly study time</h2>
      <p className="muted">How many minutes can you study on each weekday? Total: <strong><Minutes value={total} /></strong> per week.</p>
      <div className="avail-grid">
        {WEEKDAYS.map((name, i) => (
          <label key={name}>{name.slice(0, 3)}
            <input type="number" min="0" max="1440" step="15" value={minutes[i]}
              onChange={(e) => setMinutes(minutes.map((m, j) => (j === i ? e.target.value : m)))} aria-label={`${name} study minutes`} />
          </label>
        ))}
      </div>
      <button className="btn" disabled={busy}>{busy ? 'Saving…' : 'Save availability'}</button>
    </form>
  )
}

function Missed({ onChanged }) {
  const toast = useToast()
  const { data, error, loading, reload } = useAsync(() => api.missed())
  const [picked, setPicked] = useState({})
  useEffect(() => { if (data) setPicked(Object.fromEntries(data.map((s) => [s.id, true]))) }, [data])
  if (loading && !data) return null
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!data?.length) return null
  const ids = Object.keys(picked).filter((k) => picked[k]).map(Number)

  async function mark() {
    try {
      await api.markMissed(ids)
      toast.success(`${ids.length} session(s) marked as missed. Their work will be re-planned.`)
      reload(); onChanged()
    } catch (err) { toast.error(err.message) }
  }
  return (
    <section className="card card-warn">
      <h2>Missed work</h2>
      <p>These sessions were planned for earlier days but never completed. Mark them as <strong>missed</strong> (they stay in your history) so the planner can fit that work back in.</p>
      <ul className="list">
        {data.map((s) => (
          <li key={s.id}>
            <label className="inline-check">
              <input type="checkbox" checked={!!picked[s.id]} onChange={(e) => setPicked({ ...picked, [s.id]: e.target.checked })} />
              {formatDateOnly(s.planned_date)} · {s.subject.name}{s.task ? ` · ${s.task.title}` : ''}
            </label>
            <Minutes value={s.planned_minutes} />
          </li>
        ))}
      </ul>
      <button className="btn btn-primary" disabled={!ids.length} onClick={mark}>Mark selected as missed</button>
    </section>
  )
}

function PlanView({ plan, onAccepted, onDiscard }) {
  const toast = useToast()
  const [chosen, setChosen] = useState({})
  const [busy, setBusy] = useState(false)
  useEffect(() => { setChosen(Object.fromEntries(plan.suggestions.map((_, i) => [i, true]))) }, [plan])

  const selected = plan.suggestions.filter((_, i) => chosen[i])
  const selectedMinutes = selected.reduce((a, s) => a + s.minutes, 0)
  const unplaced = plan.tasks.filter((t) => t.unscheduled_minutes > 0)

  async function accept() {
    setBusy(true)
    try {
      await api.accept(selected.map((s) => ({ task_id: s.task_id, date: s.date, minutes: s.minutes })))
      toast.success(`${selected.length} study session(s) added to your plan`)
      onAccepted()
    } catch (err) { toast.error(err.message) } finally { setBusy(false) }
  }

  return (
    <section className="card">
      <h2>3. Suggested plan <span className="muted">({formatDateOnly(plan.start_date)} → {formatDateOnly(plan.end_date)})</span></h2>

      {plan.overloaded && (
        <div className="alert alert-error" role="alert">
          <strong>Your workload is more than your available time.</strong> At least <strong><Minutes value={plan.shortfall_minutes} /></strong> more
          study time is needed before the deadlines, or some work must be moved or dropped.
        </div>
      )}
      {plan.warnings.filter((w) => !w.startsWith('Overloaded')).map((w) => <div key={w} className="alert alert-info">{w}</div>)}

      <div className="stat-grid">
        <div className="card stat"><span className="stat-num"><Minutes value={plan.total_capacity_minutes} /></span><span className="muted">Free time</span></div>
        <div className="card stat"><span className="stat-num"><Minutes value={plan.total_demand_minutes} /></span><span className="muted">Work to place</span></div>
        <div className="card stat"><span className="stat-num"><Minutes value={plan.scheduled_minutes} /></span><span className="muted">Scheduled</span></div>
        <div className={`card stat ${plan.shortfall_minutes ? 'stat-alert' : ''}`}><span className="stat-num"><Minutes value={plan.shortfall_minutes} /></span><span className="muted">Shortfall</span></div>
      </div>

      {plan.tasks.length === 0 ? (
        <EmptyState title="Nothing to plan">Every unfinished task already has enough study time planned, or you have no unfinished tasks.</EmptyState>
      ) : (
        <>
          <h3>Day by day</h3>
          {plan.days.map((day) => {
            const items = plan.suggestions.map((s, i) => ({ s, i })).filter(({ s }) => s.date === day.date)
            const cap = day.free_minutes
            return (
              <div key={day.date} className="plan-day">
                <div className="plan-day-head">
                  <strong>{formatDateOnly(day.date, { weekday: 'long', day: 'numeric', month: 'short' })}</strong>
                  <span className="muted"><Minutes value={day.allocated_minutes} /> of <Minutes value={cap} /> free</span>
                </div>
                <div className="progress small"><div style={{ width: `${cap ? (day.allocated_minutes / cap) * 100 : 0}%` }} /></div>
                {items.length === 0 ? <p className="muted small-text">{cap === 0 ? 'No free study time.' : 'Nothing scheduled.'}</p> : (
                  <ul className="list">
                    {items.map(({ s, i }) => (
                      <li key={i}>
                        <label className="inline-check"><input type="checkbox" checked={!!chosen[i]} onChange={(e) => setChosen({ ...chosen, [i]: e.target.checked })} />{s.title}</label>
                        <Minutes value={s.minutes} />
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )
          })}

          <h3>Why this plan? (task ranking)</h3>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Task</th><th>Due</th><th>Score</th><th title="urgency + priority + exam + workload">Breakdown</th><th>Scheduled</th><th>Result</th></tr></thead>
              <tbody>
                {plan.tasks.map((t) => (
                  <tr key={t.task_id} className={t.counts_as_shortfall ? 'row-bad' : ''}>
                    <td>{t.title}{t.overdue && <span className="badge badge-overdue">Overdue</span>}</td>
                    <td>{t.due_date ? formatDateOnly(t.due_date) : '—'}</td>
                    <td><strong>{t.score}</strong></td>
                    <td className="small-text">{t.breakdown.urgency} + {t.breakdown.priority} + {t.breakdown.exam} + {t.breakdown.workload}</td>
                    <td><Minutes value={t.scheduled_minutes} /> / <Minutes value={t.remaining_minutes} /></td>
                    <td className="small-text">{t.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {unplaced.length > 0 && (
            <div className="alert alert-info">
              <strong>Not fully scheduled:</strong> {unplaced.map((t) => `${t.title} (${t.unscheduled_minutes} min)`).join(', ')}.
              Nothing was deleted or marked complete. You can increase your availability, change deadlines on the <Link to="/tasks">Tasks</Link> page, or re-plan later.
            </div>
          )}

          <div className="form-actions">
            <button className="btn" onClick={onDiscard}>Discard suggestion</button>
            <button className="btn btn-primary" disabled={busy || selected.length === 0} onClick={accept}>
              {busy ? 'Saving…' : `Accept ${selected.length} session(s) · ${selectedMinutes} min`}
            </button>
          </div>
          <p className="muted small-text">Nothing is saved until you accept. Accepting adds planned study sessions; it never changes your tasks.</p>
        </>
      )}
    </section>
  )
}

export default function Planner() {
  const [days, setDays] = useState(7)
  const [plan, setPlan] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [missedKey, setMissedKey] = useState(0)

  async function generate() {
    setBusy(true)
    setError(null)
    try { setPlan(await api.generate(Number(days))) } catch (err) { setError(err) } finally { setBusy(false) }
  }

  return (
    <>
      <PageHeader title="Weekly planner" subtitle="Fit your unfinished work into the time you really have, and recover when you fall behind." />
      <Availability />
      <Missed key={missedKey} onChanged={() => { setMissedKey((k) => k + 1); if (plan) generate() }} />
      <section className="card">
        <h2>2. Generate a plan</h2>
        <p className="muted">The planner ranks unfinished tasks by urgency, priority, upcoming exams and effort, then places them into your free time. It is a transparent heuristic, not a guarantee.</p>
        <div className="form-actions left">
          <label className="inline-check">Plan the next{' '}
            <select value={days} onChange={(e) => setDays(e.target.value)}>
              <option value="7">7 days</option><option value="14">14 days</option><option value="21">21 days</option>
            </select>
          </label>
          <button className="btn btn-primary" onClick={generate} disabled={busy}>{busy ? 'Planning…' : plan ? 'Re-generate plan' : 'Generate plan'}</button>
        </div>
      </section>
      <ErrorBox error={error} />
      {plan && <PlanView plan={plan} onDiscard={() => setPlan(null)} onAccepted={() => { setPlan(null); setMissedKey((k) => k + 1) }} />}
    </>
  )
}
