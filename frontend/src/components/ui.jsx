import { formatMinutes } from '../lib/format'

export function Loading({ label = 'Loading…' }) {
  return <p className="loading" role="status">{label}</p>
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null
  return (
    <div className="alert alert-error" role="alert">
      <span>{error.message || String(error)}</span>
      {onRetry && <button className="btn btn-small" onClick={onRetry}>Try again</button>}
    </div>
  )
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action}
    </div>
  )
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      <div className="page-actions">{actions}</div>
    </div>
  )
}

export function SubjectDot({ subject }) {
  return (
    <span className="subject-chip">
      <span className="dot" style={{ background: subject?.color || '#94a3b8' }} aria-hidden="true" />
      {subject?.name}
    </span>
  )
}

const PRIORITY_LABEL = { low: 'Low', medium: 'Medium', high: 'High' }
export const PriorityBadge = ({ value }) => <span className={`badge prio-${value}`}>{PRIORITY_LABEL[value]}</span>

const STATUS_LABEL = {
  pending: 'Pending', in_progress: 'In progress', completed: 'Completed', planned: 'Planned', missed: 'Missed',
}
export const StatusBadge = ({ value }) => <span className={`badge status-${value}`}>{STATUS_LABEL[value] || value}</span>

export const Minutes = ({ value }) => <span>{formatMinutes(value)}</span>
