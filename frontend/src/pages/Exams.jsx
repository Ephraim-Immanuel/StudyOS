import { useState } from 'react'
import { exams as api, subjects as subjectsApi } from '../api'
import ConfirmDialog from '../components/ConfirmDialog'
import { Field } from '../components/Field'
import Modal from '../components/Modal'
import { EmptyState, ErrorBox, Loading, Minutes, PageHeader, SubjectDot } from '../components/ui'
import { useToast } from '../context/ToastContext'
import { formatDateOnly } from '../lib/format'
import { useAsync } from '../lib/useAsync'

function ExamForm({ initial, subjects, onSaved, onClose }) {
  const toast = useToast()
  const [form, setForm] = useState({
    subject_id: initial?.subject_id || subjects[0]?.id || '', title: initial?.title || '',
    exam_date: initial?.exam_date || '', topics: initial?.topics || '', importance: initial?.importance ?? 3,
  })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    const body = { ...form, subject_id: Number(form.subject_id), importance: Number(form.importance), topics: form.topics || null }
    try {
      if (initial) await api.update(initial.id, body)
      else await api.create(body)
      toast.success(initial ? 'Exam updated' : 'Exam added')
      onSaved()
    } catch (err) {
      setErrors(err.fieldErrors || {})
      toast.error(err.message)
    } finally { setBusy(false) }
  }

  return (
    <form onSubmit={submit}>
      <Field label="Title" error={errors.title}>{(p) => <input {...p} required value={form.title} onChange={set('title')} placeholder="Midterm" />}</Field>
      <div className="form-row">
        <Field label="Subject" error={errors.subject_id}>
          {(p) => <select {...p} required value={form.subject_id} onChange={set('subject_id')}>{subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>}
        </Field>
        <Field label="Exam date" error={errors.exam_date}>{(p) => <input {...p} type="date" required value={form.exam_date} onChange={set('exam_date')} />}</Field>
      </div>
      <Field label="Importance (1 = minor, 5 = critical)" error={errors.importance}>
        {(p) => <input {...p} type="range" min="1" max="5" value={form.importance} onChange={set('importance')} />}
      </Field>
      <small className="muted">Selected: {form.importance}</small>
      <Field label="Syllabus / topics (optional)" error={errors.topics}>{(p) => <textarea {...p} rows={3} value={form.topics} onChange={set('topics')} />}</Field>
      <div className="form-actions">
        <button type="button" className="btn" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" disabled={busy}>{busy ? 'Saving…' : 'Save exam'}</button>
      </div>
    </form>
  )
}

export default function Exams() {
  const toast = useToast()
  const [upcomingOnly, setUpcomingOnly] = useState(true)
  const subjects = useAsync(() => subjectsApi.list())
  const { data, error, loading, reload } = useAsync(() => api.list({ upcoming_only: upcomingOnly }), [upcomingOnly])
  const [editing, setEditing] = useState(null)
  const [deleting, setDeleting] = useState(null)

  async function remove() {
    try { await api.remove(deleting.id); toast.success('Exam deleted'); setDeleting(null); reload() }
    catch (err) { toast.error(err.message); setDeleting(null) }
  }

  return (
    <>
      <PageHeader title="Exams" subtitle="Upcoming exams and the unfinished work behind them."
        actions={<button className="btn btn-primary" disabled={!subjects.data?.length} onClick={() => setEditing('new')}>+ New exam</button>} />
      {subjects.data?.length === 0 && <div className="alert alert-info">Create a subject first — every exam belongs to one.</div>}
      <label className="inline-check"><input type="checkbox" checked={upcomingOnly} onChange={(e) => setUpcomingOnly(e.target.checked)} /> Upcoming only</label>
      <ErrorBox error={error} onRetry={reload} />
      {loading && !data && <Loading />}
      {data?.length === 0 && <EmptyState title="No exams">{upcomingOnly ? 'No upcoming exams recorded.' : 'You have not added any exams.'}</EmptyState>}
      <div className="grid">
        {data?.map((e) => (
          <article key={e.id} className="card">
            <h2>{e.title}</h2>
            <p><SubjectDot subject={e.subject} /></p>
            <p><strong>{formatDateOnly(e.exam_date, { weekday: 'long', day: 'numeric', month: 'long' })}</strong>
              {' '}<span className={`badge ${e.days_until < 0 ? 'status-completed' : e.days_until <= 3 ? 'badge-overdue' : 'status-pending'}`}>
                {e.days_until < 0 ? 'Past' : e.days_until === 0 ? 'Today' : `in ${e.days_until} day${e.days_until === 1 ? '' : 's'}`}</span></p>
            <p className="muted">Importance {e.importance}/5</p>
            {e.topics && <p className="clamp">{e.topics}</p>}
            <p className="stats-line">Preparation workload: <strong><Minutes value={e.prep_minutes} /></strong> across {e.open_tasks} unfinished task{e.open_tasks === 1 ? '' : 's'}</p>
            <div className="row-actions">
              <button className="btn btn-small" onClick={() => setEditing(e)}>Edit</button>
              <button className="btn btn-small btn-danger-outline" onClick={() => setDeleting(e)}>Delete</button>
            </div>
          </article>
        ))}
      </div>
      {editing && subjects.data && (
        <Modal title={editing === 'new' ? 'New exam' : 'Edit exam'} onClose={() => setEditing(null)} wide>
          <ExamForm initial={editing === 'new' ? null : editing} subjects={subjects.data} onClose={() => setEditing(null)}
            onSaved={() => { setEditing(null); reload() }} />
        </Modal>
      )}
      {deleting && <ConfirmDialog title="Delete exam?" message={`Delete “${deleting.title}”?`} onConfirm={remove} onCancel={() => setDeleting(null)} />}
    </>
  )
}
