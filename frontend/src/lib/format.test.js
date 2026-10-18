import { describe, expect, it } from 'vitest'
import { formatMinutes, fromInputValue, parseDateOnly, percent, toInputValue, weekdayIndex } from './format'

describe('formatMinutes', () => {
  it('formats minutes and hours', () => {
    expect(formatMinutes(0)).toBe('0 min')
    expect(formatMinutes(45)).toBe('45 min')
    expect(formatMinutes(60)).toBe('1 h')
    expect(formatMinutes(95)).toBe('1 h 35 min')
  })
  it('is safe with bad input', () => {
    expect(formatMinutes(undefined)).toBe('0 min')
    expect(formatMinutes(-5)).toBe('0 min')
  })
})

describe('dates', () => {
  it('parses date-only strings without timezone shift', () => {
    const d = parseDateOnly('2026-03-10')
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 2, 10])
  })
  it('maps weekdays Monday=0 like the backend', () => {
    expect(weekdayIndex('2026-03-02')).toBe(0) // Monday
    expect(weekdayIndex('2026-03-04')).toBe(2) // Wednesday
    expect(weekdayIndex('2026-03-08')).toBe(6) // Sunday
  })
  it('converts a UTC instant to the profile timezone for the input box', () => {
    expect(toInputValue('2026-03-10T06:30:00Z', 'Asia/Kolkata')).toBe('2026-03-10T12:00')
    expect(toInputValue('2026-03-10T06:30:00Z', 'UTC')).toBe('2026-03-10T06:30')
    expect(toInputValue(null, 'UTC')).toBe('')
  })
  it('sends empty input as null', () => {
    expect(fromInputValue('')).toBeNull()
    expect(fromInputValue('2026-03-10T12:00')).toBe('2026-03-10T12:00')
  })
  it('formats percentages', () => {
    expect(percent(0.1667)).toBe('17%')
  })
})
