import { useId } from 'react'

// A label + input + error message, wired together for screen readers.
export function Field({ label, error, hint, children }) {
  const id = useId()
  const child = children({ id, 'aria-invalid': !!error || undefined, 'aria-describedby': error ? `${id}-err` : hint ? `${id}-hint` : undefined })
  return (
    <div className={`field ${error ? 'has-error' : ''}`}>
      <label htmlFor={id}>{label}</label>
      {child}
      {hint && !error && <small id={`${id}-hint`} className="muted">{hint}</small>}
      {error && <small id={`${id}-err`} className="field-error">{error}</small>}
    </div>
  )
}
