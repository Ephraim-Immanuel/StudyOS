import { useState } from 'react'
import { subjects as subjectsApi, tasks as api } from '../api'
import ConfirmDialog from '../components/ConfirmDialog'
import Modal from '../components/Modal'
import TaskForm from '../components/TaskForm'
import { EmptyState, ErrorBox, Loading, Minutes, PageHeader, PriorityBadge, StatusBadge, SubjectDot } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { formatDateTime } from '../lib/format'
import { useAsync } from '../lib/useAsync'

const PAGE = 20
const EMPTY_FILTERS = { status: '', priority: '', subject_id: '', due: '', q: '', sort: 'due_at', order: 'asc' }

export default function Tasks() {
  const { user } = useAuth()
  const toast = useToast()
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [offset, setOffset] = useState(0)
  const [editing, setEditing] = useState(null)
  const [deleting, setDeleting] = useState(null)

  const subjects = useAsync(() => subjectsApi.list())
  const { data, error, loading, reload } = useAsync(
    () => api.list({ ...filters, limit: PAGE, offset }), [JSON.stringify(filters), offset])

  const setFilter = (k) => (e) => { setFilters({ ...filters, [k]: e.target.value }); setOffset(0) }
  const filtered = JSON.stringify(filters) !== JSON.stringify(EMPTY_FILTERS)

  async function complete(t) {
    try { await api.complete(t.id); toast.success('Task completed'); reload() } catch (err) { toast.error(err.message) }
  }
  async function remove() {
    try { await api.remove(deleting.id); toast.success('Task deleted'); setDeleting(null); reload() }
    catch (err) { toast.error(err.message); setDeleting(null) }
  }

  const noSubjects = subjects.data && subjects.data.length === 0

  return (
    <>
      <PageHeader title="Tasks" subtitle="Assignments and anything else you need to finish."
        actions={<button className="btn btn-primary" disabled={!subjects.data?.length} onClick={() => setEditing('new')}>+ New task</button>} />
      {noSubjects && <div className="alert alert-info">Create a subject first — every task belongs to one.</div>}

      <form className="filters card" onSubmit={(e) => e.preventDefault()} aria-label="Task filters">
        <label>Search<input type="search" value={filters.q} onChange={setFilter('q')} placeholder="Title…" /></label>
        <label>Status
          <select value={filters.status} onChange={setFilter('status')}>
            <option value="">All</option><option value="pending">Pending</option><option value="in_progress">In progress</option><option value="completed">Completed</option>
          </select>
        </label>
        <label>Priority
          <select value={filters.priority} onChange={setFilter('priority')}>
            <option value="">All</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
          </select>
        </label>
        <label>Subject
          <select value={filters.subject_id} onChange={setFilter('subject_id')}>
            <option value="">All</option>
            {subjects.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </label>
        <label>Deadline
          <select value={filters.due} onChange={setFilter('due')}>
            <option value="">Any</option><option value="overdue">Overdue</option><option value="today">Due today</option>
            <option value="upcoming">Next 7 days</option><option value="none">No due date</option>
          </select>
        </label>
        <label>Sort by
          <select value={filters.sort} onChange={setFilter('sort')}>
            <option value="due_at">Deadline</option><option value="priority">Priority</option><option value="created_at">Newest</option>
          </select>
        </label>
        <label>Order
          <select value={filters.order} onChange={setFilter('order')}>
            <option value="asc">Ascending</option><option value="desc">Descending</option>
          </select>
        </label>
        {filtered && <button type="button" className="btn btn-small" onClick={() => { setFilters(EMPTY_FILTERS); setOffset(0) }}>Clear</button>}
      </form>

      <ErrorBox error={error} onRetry={reload} />
      {loading && !data && <Loading />}
      {data && data.total === 0 && (
        <EmptyState title={filtered ? 'No tasks match these filters' : 'No tasks yet'}>
          {filtered ? 'Try clearing a filter.' : 'Add your first assignment to start planning.'}
        </EmptyState>
      )}
      {data && data.items.length > 0 && (
        <ul className="task-list">
          {data.items.map((t) => (
            <li key={t.id} className={`card task ${t.status === 'completed' ? 'is-done' : ''}`}>
              <div className="task-main">
                <h3 className={t.status === 'completed' ? 'done' : ''}>{t.title}</h3>
                <div className="meta">
                  <SubjectDot subject={t.subject} /> <PriorityBadge value={t.priority} /> <StatusBadge value={t.status} />
                  {t.is_overdue && <span className="badge badge-overdue">Overdue</span>}
                  <span className="muted">· <Minutes value={t.estimated_minutes} /></span>
                  <span className="muted">· {t.due_at ? `Due ${formatDateTime(t.due_at, user.timezone)}` : 'No due date'}</span>
                </div>
                {t.description && <p className="muted clamp">{t.description}</p>}
              </div>
              <div className="row-actions">
                {t.status !== 'completed' && <button className="btn btn-small btn-success" onClick={() => complete(t)} aria-label={`Complete ${t.title}`}>✓ Done</button>}
                <button className="btn btn-small" onClick={() => setEditing(t)} aria-label={`Edit ${t.title}`}>Edit</button>
                <button className="btn btn-small btn-danger-outline" onClick={() => setDeleting(t)} aria-label={`Delete ${t.title}`}>Delete</button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {data && data.total > PAGE && (
        <div className="pager">
          <button className="btn btn-small" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>← Previous</button>
          <span className="muted">{offset + 1}–{Math.min(offset + PAGE, data.total)} of {data.total}</span>
          <button className="btn btn-small" disabled={offset + PAGE >= data.total} onClick={() => setOffset(offset + PAGE)}>Next →</button>
        </div>
      )}

      {editing && subjects.data && (
        <Modal title={editing === 'new' ? 'New task' : 'Edit task'} onClose={() => setEditing(null)} wide>
          <TaskForm initial={editing === 'new' ? null : editing} subjects={subjects.data}
            onClose={() => setEditing(null)} onSaved={() => { setEditing(null); reload() }} />
        </Modal>
      )}
      {deleting && <ConfirmDialog title="Delete task?" message={`Delete “${deleting.title}”? Study sessions linked to it are kept.`}
        onConfirm={remove} onCancel={() => setDeleting(null)} />}
    </>
  )
}
