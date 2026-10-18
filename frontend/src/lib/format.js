// Pure helpers for dates and durations. Covered by src/lib/format.test.js.
const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
export const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export function formatMinutes(total) {
  const m = Math.max(0, Math.round(Number(total) || 0))
  if (m < 60) return `${m} min`
  const h = Math.floor(m / 60)
  const r = m % 60
  return r ? `${h} h ${r} min` : `${h} h`
}

// "2026-03-10" (a calendar date, no timezone) -> Date at local midnight, WITHOUT the UTC shift bug.
export function parseDateOnly(s) {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function formatDateOnly(s, opts = { weekday: 'short', day: 'numeric', month: 'short' }) {
  return parseDateOnly(s).toLocaleDateString(undefined, opts)
}

export function weekdayIndex(dateStr) {
  // JS: Sunday=0. Backend: Monday=0.
  return (parseDateOnly(dateStr).getDay() + 6) % 7
}

export function shortWeekday(i) {
  return DAY_NAMES[i]
}

// ISO instant (UTC) -> readable text in the USER'S profile timezone.
export function formatDateTime(iso, tz) {
  if (!iso) return ''
  return new Date(iso).toLocaleString(undefined, {
    timeZone: tz, weekday: 'short', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit',
  })
}

// ISO instant -> value for <input type="datetime-local"> in the user's timezone.
export function toInputValue(iso, tz) {
  if (!iso) return ''
  const parts = new Intl.DateTimeFormat('sv-SE', {
    timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).format(new Date(iso))
  return parts.replace(' ', 'T') // "2026-03-10 14:30" -> "2026-03-10T14:30"
}

// We send the datetime-local text as-is (no offset); the server reads it in the profile timezone.
export function fromInputValue(value) {
  return value ? value : null
}

export function percent(x) {
  return `${Math.round((x || 0) * 100)}%`
}
