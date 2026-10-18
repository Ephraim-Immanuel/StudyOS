import { useState } from 'react'
import { sessions as api, subjects as subjectsApi, tasks as tasksApi } from '../api'
import ConfirmDialog from '../components/ConfirmDialog'
import { Field } from '../components/Field'
import Modal from '../components/Modal'
import { EmptyState, ErrorBox, Loading, Minutes, PageHeader, StatusBadge, SubjectDot } from '../components/ui'
import { useToast } from '../context/ToastContext'
import { formatDateOnly } from '../lib/format'
import { useAsync } from '../lib/useAsync'

function SessionForm({ subjects, onSaved, onClose }) {
  const toast = useToast()
  const [form, setForm] = useState({
    subject_id: subjects[0]?.id || '', task_id: '', planned_date: new Date().toLocaleDateString('sv-SE'), planned_minutes: 45,
  })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const taskList = useAsync(() => (form.subject_id ? tasksApi.list({ subject_id: form.subject_id, limit: 200 }) : Promise.resolve({ items: [] })), [form.subject_id])
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    try {
      await api.create({ ...form, subject_id: Number(form.subject_id), task_id: form.task_id ? Number(form.task_id) : null, planned_minutes: Number(form.planned_minutes) })
      toast.success('Study session added')
      onSaved()
    } catch (err) {
      setErrors(err.fieldErrors || {})
      toast.error(err.message)
    } finally { setBusy(false) }
  }

  return (
    <form onSubmit={submit}>
      <div className="form-row">
        <Field label="Subject" error={errors.subject_id}>
          {(p) => <select {...p} required value={form.subject_id} onChange={(e) => setForm({ ...form, subject_id: e.target.value, task_id: '' })}>
            {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>}
        </Field>
        <Field label="Task (optional)" error={errors.task_id}>
          {(p) => <select {...p} value={form.task_id} onChange={set('task_id')}>
            <option value="">— none —</option>
            {taskList.data?.items.filter((t) => t.status !== 'completed').map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}</select>}
        </Field>
      </div>
      <div className="form-row">
        <Field label="Date" error={errors.planned_date}>{(p) => <input {...p} type="date" required value={form.planned_date} onChange={set('planned_date')} />}</Field>
        <Field label="Planned minutes" error={errors.planned_minutes}>{(p) => <input {...p} type="number" min="1" max="1440" step="5" required value={form.planned_minutes} onChange={set('planned_minutes')} />}</Field>
      </div>
      <div className="form-actions">
        <button type="button" className="btn" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" disabled={busy}>{busy ? 'Saving…' : 'Add session'}</button>
      </div>
    </form>
  )
}

function CompleteForm({ session, onSaved, onClose }) {
  const toast = useToast()
  const [minutes, setMinutes] = useState(session.planned_minutes)
  const [busy, setBusy] = useState(false)
  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    try { await api.complete(session.id, Number(minutes)); toast.success('Session completed'); onSaved() }
    catch (err) { toast.error(err.message) } finally { setBusy(false) }
  }
  return (
    <form onSubmit={submit}>
      <p>How long did you actually study? (planned: <Minutes value={session.planned_minutes} />)</p>
      <Field label="Actual minutes">{(p) => <input {...p} type="number" min="0" max="1440" required value={minutes} onChange={(e) => setMinutes(e.target.value)} />}</Field>
      <div className="form-actions">
        <button type="button" className="btn" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" disabled={busy}>Mark complete</button>
      </div>
    </form>
  )
}

export default function Sessions() {
  const toast = useToast()
  const [statusFilter, setStatusFilter] = useState('')
  const subjects = useAsync(() => subjectsApi.list())
  const list = useAsync(() => api.list({ status: statusFilter }), [statusFilter])
  const summary = useAsync(() => api.summary())
  const [adding, setAdding] = useState(false)
  const [completing, setCompleting] = useState(null)
  const [deleting, setDeleting] = useState(null)

  const reloadAll = () => { list.reload(); summary.reload() }
  async function markMissed(s) {
    try { await api.update(s.id, { status: 'missed' }); toast.success('Marked as missed'); reloadAll() } catch (err) { toast.error(err.message) }
  }
  async function remove() {
    try { await api.remove(deleting.id); toast.success('Session deleted'); setDeleting(null); reloadAll() }
    catch (err) { toast.error(err.message); setDeleting(null) }
  }

  const s = summary.data
  const pct = s && s.planned_minutes ? Math.min(100, Math.round((s.completed_minutes / s.planned_minutes) * 100)) : 0

  return (
    <>
      <PageHeader title="Study sessions" subtitle="Plan study blocks and record what you actually did."
        actions={<button className="btn btn-primary" disabled={!subjects.data?.length} onClick={() => setAdding(true)}>+ New session</button>} />
      {subjects.data?.length === 0 && <div className="alert alert-info">Create a subject first — sessions belong to a subject.</div>}
      {s && (
        <section className="card" aria-label="Weekly summary">
          <h2>Last 7 days: planned vs completed</h2>
          <div className="progress" role="progressbar" aria-valuenow={pct} aria-valuemin="0" aria-valuemax="100"><div style={{ width: `${pct}%` }} /></div>
          <p><strong><Minutes value={s.completed_minutes} /></strong> completed of <strong><Minutes value={s.planned_minutes} /></strong> planned
            {s.missed_minutes > 0 && <> · <span className="text-danger"><Minutes value={s.missed_minutes} /> missed</span></>}</p>
        </section>
      )}
      <label className="inline-check">Show{' '}
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All sessions</option><option value="planned">Planned</option><option value="completed">Completed</option><option value="missed">Missed</option>
        </select>
      </label>
      <ErrorBox error={list.error} onRetry={list.reload} />
      {list.loading && !list.data && <Loading />}
      {list.data?.length === 0 && <EmptyState title="No study sessions">Add one here, or generate a plan in the Planner.</EmptyState>}
      <ul className="task-list">
        {list.data?.map((x) => (
          <li key={x.id} className="card task">
            <div className="task-main">
              <h3>{formatDateOnly(x.planned_date)} <StatusBadge value={x.status} />{x.source === 'planner' && <span className="badge badge-plan">From planner</span>}</h3>
              <div className="meta"><SubjectDot subject={x.subject} />{x.task && <span> · {x.task.title}</span>}
                <span className="muted"> · planned <Minutes value={x.planned_minutes} />{x.status === 'completed' && <> · actual <Minutes value={x.actual_minutes} /></>}</span></div>
            </div>
            <div className="row-actions">
              {x.status === 'planned' && <button className="btn btn-small btn-success" onClick={() => setCompleting(x)}>✓ Complete</button>}
              {x.status === 'planned' && <button className="btn btn-small" onClick={() => markMissed(x)}>Missed</button>}
              <button className="btn btn-small btn-danger-outline" onClick={() => setDeleting(x)}>Delete</button>
            </div>
          </li>
        ))}
      </ul>
      {adding && subjects.data && <Modal title="New study session" onClose={() => setAdding(false)} wide>
        <SessionForm subjects={subjects.data} onClose={() => setAdding(false)} onSaved={() => { setAdding(false); reloadAll() }} /></Modal>}
      {completing && <Modal title="Complete session" onClose={() => setCompleting(null)}>
        <CompleteForm session={completing} onClose={() => setCompleting(null)} onSaved={() => { setCompleting(null); reloadAll() }} /></Modal>}
      {deleting && <ConfirmDialog title="Delete session?" message="This removes the session from your history." onConfirm={remove} onCancel={() => setDeleting(null)} />}
    </>
  )
}
