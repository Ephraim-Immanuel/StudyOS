import { useState } from 'react'
import { tasks } from '../api'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { fromInputValue, toInputValue } from '../lib/format'
import { Field } from './Field'

export default function TaskForm({ initial, subjects, defaultSubjectId, onSaved, onClose }) {
  const { user } = useAuth()
  const toast = useToast()
  const [form, setForm] = useState({
    title: initial?.title || '',
    description: initial?.description || '',
    subject_id: initial?.subject_id || defaultSubjectId || subjects[0]?.id || '',
    due_at: toInputValue(initial?.due_at, user.timezone),
    priority: initial?.priority || 'medium',
    estimated_minutes: initial?.estimated_minutes ?? 60,
    status: initial?.status || 'pending',
  })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    const body = {
      ...form,
      subject_id: Number(form.subject_id),
      estimated_minutes: Number(form.estimated_minutes),
      description: form.description || null,
      due_at: fromInputValue(form.due_at),
    }
    try {
      if (initial) await tasks.update(initial.id, body)
      else await tasks.create(body)
      toast.success(initial ? 'Task updated' : 'Task created')
      onSaved()
    } catch (err) {
      setErrors(err.fieldErrors || {})
      toast.error(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit}>
      <Field label="Title" error={errors.title}>
        {(p) => <input {...p} required maxLength={200} value={form.title} onChange={set('title')} />}
      </Field>
      <Field label="Description (optional)" error={errors.description}>
        {(p) => <textarea {...p} rows={3} value={form.description} onChange={set('description')} />}
      </Field>
      <div className="form-row">
        <Field label="Subject" error={errors.subject_id}>
          {(p) => (
            <select {...p} required value={form.subject_id} onChange={set('subject_id')}>
              {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          )}
        </Field>
        <Field label="Priority" error={errors.priority}>
          {(p) => (
            <select {...p} value={form.priority} onChange={set('priority')}>
              <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
            </select>
          )}
        </Field>
      </div>
      <div className="form-row">
        <Field label={`Due (${user.timezone})`} error={errors.due_at} hint="Optional">
          {(p) => <input {...p} type="datetime-local" value={form.due_at} onChange={set('due_at')} />}
        </Field>
        <Field label="Estimated effort (minutes)" error={errors.estimated_minutes}>
          {(p) => <input {...p} type="number" min="1" max="1440" step="5" required value={form.estimated_minutes} onChange={set('estimated_minutes')} />}
        </Field>
      </div>
      {initial && (
        <Field label="Status" error={errors.status}>
          {(p) => (
            <select {...p} value={form.status} onChange={set('status')}>
              <option value="pending">Pending</option><option value="in_progress">In progress</option><option value="completed">Completed</option>
            </select>
          )}
        </Field>
      )}
      <div className="form-actions">
        <button type="button" className="btn" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" disabled={busy}>{busy ? 'Saving…' : 'Save task'}</button>
      </div>
    </form>
  )
}
