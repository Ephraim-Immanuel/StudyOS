import { Link, useParams } from 'react-router-dom'
import { exams, sessions, subjects, tasks } from '../api'
import { EmptyState, ErrorBox, Loading, Minutes, PageHeader, PriorityBadge, StatusBadge } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { formatDateOnly, formatDateTime } from '../lib/format'
import { useAsync } from '../lib/useAsync'

export default function SubjectDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const { data, error, loading, reload } = useAsync(async () => {
    const [subject, t, s, e] = await Promise.all([
      subjects.get(id), tasks.list({ subject_id: id, limit: 200 }), sessions.list({ subject_id: id }), exams.list({ subject_id: id }),
    ])
    return { subject, tasks: t.items, sessions: s, exams: e }
  }, [id])

  if (loading && !data) return <Loading />
  if (error) return <><ErrorBox error={error} onRetry={reload} /><Link to="/subjects">← Back to subjects</Link></>

  const { subject } = data
  return (
    <>
      <p><Link to="/subjects">← All subjects</Link></p>
      <PageHeader title={subject.name} subtitle={subject.description} />
      <section className="card">
        <h2>Tasks ({data.tasks.length})</h2>
        {data.tasks.length === 0 ? <EmptyState title="No tasks in this subject yet">Add one from the Tasks page.</EmptyState> : (
          <ul className="list">
            {data.tasks.map((t) => (
              <li key={t.id}>
                <span className={t.status === 'completed' ? 'done' : ''}>{t.title}</span>
                <span className="meta">
                  <PriorityBadge value={t.priority} /> <StatusBadge value={t.status} />
                  {t.is_overdue && <span className="badge badge-overdue">Overdue</span>}
                  {t.due_at && <span className="muted"> {formatDateTime(t.due_at, user.timezone)}</span>}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="card">
        <h2>Study sessions ({data.sessions.length})</h2>
        {data.sessions.length === 0 ? <p className="muted">No sessions yet.</p> : (
          <ul className="list">
            {data.sessions.map((s) => (
              <li key={s.id}>
                <span>{formatDateOnly(s.planned_date)}{s.task ? ` · ${s.task.title}` : ''}</span>
                <span className="meta"><Minutes value={s.status === 'completed' ? s.actual_minutes : s.planned_minutes} /> <StatusBadge value={s.status} /></span>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="card">
        <h2>Exams ({data.exams.length})</h2>
        {data.exams.length === 0 ? <p className="muted">No exams recorded.</p> : (
          <ul className="list">
            {data.exams.map((e) => (
              <li key={e.id}><span>{e.title}</span><span className="meta">{formatDateOnly(e.exam_date)} ({e.days_until} days)</span></li>
            ))}
          </ul>
        )}
      </section>
    </>
  )
}
