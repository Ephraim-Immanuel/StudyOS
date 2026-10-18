// One small function per backend endpoint. Components import from here.
import { get, post, patch, put, del } from './client'

export const auth = {
  me: () => get('/auth/me'),
  register: (data) => post('/auth/register', data),
  login: (data) => post('/auth/login', data),
  logout: () => post('/auth/logout'),
  update: (data) => patch('/auth/me', data),
}
export const subjects = {
  list: () => get('/subjects'),
  get: (id) => get(`/subjects/${id}`),
  create: (d) => post('/subjects', d),
  update: (id, d) => patch(`/subjects/${id}`, d),
  remove: (id) => del(`/subjects/${id}`),
}
export const tasks = {
  list: (params) => get('/tasks', params),
  create: (d) => post('/tasks', d),
  update: (id, d) => patch(`/tasks/${id}`, d),
  complete: (id) => post(`/tasks/${id}/complete`),
  remove: (id) => del(`/tasks/${id}`),
}
export const exams = {
  list: (params) => get('/exams', params),
  create: (d) => post('/exams', d),
  update: (id, d) => patch(`/exams/${id}`, d),
  remove: (id) => del(`/exams/${id}`),
}
export const sessions = {
  list: (params) => get('/sessions', params),
  summary: (params) => get('/sessions/summary', params),
  create: (d) => post('/sessions', d),
  update: (id, d) => patch(`/sessions/${id}`, d),
  complete: (id, actual_minutes) => post(`/sessions/${id}/complete`, actual_minutes == null ? {} : { actual_minutes }),
  remove: (id) => del(`/sessions/${id}`),
}
export const planner = {
  availability: () => get('/availability'),
  saveAvailability: (days) => put('/availability', { days }),
  generate: (days) => post('/planner/generate', { days }),
  accept: (items) => post('/planner/accept', { items }),
  missed: () => get('/planner/missed'),
  markMissed: (session_ids) => post('/planner/mark-missed', { session_ids }),
}
export const dashboard = { get: () => get('/dashboard') }
