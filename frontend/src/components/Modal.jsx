import { useEffect, useRef } from 'react'

// Accessible dialog: Escape closes it, focus moves inside, background is announced as hidden.
export default function Modal({ title, onClose, children, wide }) {
  const ref = useRef(null)

  useEffect(() => {
    const previous = document.activeElement
    const first = ref.current?.querySelector('input, select, textarea, button')
    first?.focus()
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      previous?.focus?.()
    }
  }, [onClose])

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? 'modal-wide' : ''}`} role="dialog" aria-modal="true" aria-label={title} ref={ref}>
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Close dialog">×</button>
        </div>
        {children}
      </div>
    </div>
  )
}
