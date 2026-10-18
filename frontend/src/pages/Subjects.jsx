import { useState } from 'react'
import { Link } from 'react-router-dom'
import { subjects as api } from '../api'
import ConfirmDialog from '../components/ConfirmDialog'
import { Field } from '../components/Field'
import Modal from '../components/Modal'
import { EmptyState, ErrorBox, Loading, PageHeader } from '../components/ui'
import { useToast } from '../context/ToastContext'
import { useAsync } from '../lib/useAsync'

function SubjectForm({ initial, onSaved, onClose }) {
  const toast = useToast()
  const [form, setForm] = useState({
    name: initial?.name || '', description: initial?.description || '', color: initial?.color || '#4f46e5',
  })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    try {
      const body = { ...form, description: form.description || null }
      if (initial) await api.update(initial.id, body)
      else await api.create(body)
      toast.success(initial ? 'Subject updated' : 'Subject created')
      onSaved()
    } catch (err) {
      setErrors(err.status === 409 ? { name: err.message } : err.fieldErrors || {})
      if (!Object.keys(err.fieldErrors || {}).length && err.status !== 409) toast.error(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit}>
      <Field label="Name" error={errors.name}>
        {(p) => <input {...p} required maxLength={100} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />}
      </Field>
      <Field label="Description (optional)" error={errors.description}>
        {(p) => <textarea {...p} rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />}
      </Field>
      <Field label="Colour" error={errors.color}>
        {(p) => <input {...p} type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />}
      </Field>
      <div className="form-actions">
        <button type="button" className="btn" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" disabled={busy}>{busy ? 'Saving…' : 'Save'}</button>
      </div>
    </form>
  )
}

export default function Subjects() {
  const toast = useToast()
  const { data, error, loading, reload } = useAsync(() => api.list())
  const [editing, setEditing] = useState(null) // null | 'new' | subject
  const [deleting, setDeleting] = useState(null)

  async function remove() {
    try {
      await api.remove(deleting.id)
      toast.success('Subject deleted')
      setDeleting(null)
      reload()
    } catch (err) {
      toast.error(err.message) // e.g. "This subject still has 3 task(s)…"
      setDeleting(null)
    }
  }

  return (
    <>
      <PageHeader title="Subjects" subtitle="The courses you are studying."
        actions={<button className="btn btn-primary" onClick={() => setEditing('new')}>+ New subject</button>} />
      <ErrorBox error={error} onRetry={reload} />
      {loading && !data && <Loading />}
      {data && data.length === 0 && (
        <EmptyState title="No subjects yet" action={<button className="btn btn-primary" onClick={() => setEditing('new')}>Add your first subject</button>}>
          Create a subject for each course. Tasks, exams and study sessions all belong to a subject.
        </EmptyState>
      )}
      <div className="grid">
        {data?.map((s) => (
          <article key={s.id} className="card subject-card" style={{ borderTopColor: s.color || '#94a3b8' }}>
            <h2><Link to={`/subjects/${s.id}`}>{s.name}</Link></h2>
            {s.description && <p className="muted clamp">{s.description}</p>}
            <p className="stats-line">
              <strong>{s.open_tasks}</strong> open of {s.total_tasks} tasks · {s.exam_count} exams · {s.session_count} sessions
            </p>
            <div className="row-actions">
              <button className="btn btn-small" onClick={() => setEditing(s)}>Edit</button>
              <button className="btn btn-small btn-danger-outline" onClick={() => setDeleting(s)}>Delete</button>
            </div>
          </article>
        ))}
      </div>
      {editing && (
        <Modal title={editing === 'new' ? 'New subject' : 'Edit subject'} onClose={() => setEditing(null)}>
          <SubjectForm initial={editing === 'new' ? null : editing} onClose={() => setEditing(null)}
            onSaved={() => { setEditing(null); reload() }} />
        </Modal>
      )}
      {deleting && (
        <ConfirmDialog title="Delete subject?" message={`Delete “${deleting.name}”? Subjects that still have tasks, exams or sessions cannot be deleted.`}
          onConfirm={remove} onCancel={() => setDeleting(null)} />
      )}
    </>
  )
}
