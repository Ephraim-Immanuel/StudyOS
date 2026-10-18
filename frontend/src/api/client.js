// The ONLY place that calls fetch(). Components never talk to the network directly.
const BASE = import.meta.env.VITE_API_BASE_URL || '/api'

export class ApiError extends Error {
  constructor(status, message, fieldErrors = {}) {
    super(message)
    this.status = status
    this.fieldErrors = fieldErrors // { fieldName: "message" } for form validation
  }
}

let onUnauthorized = () => {}
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn
}

// FastAPI sends 422 errors as a list: [{loc: ["body","title"], msg: "..."}]
function parseError(status, data) {
  const fieldErrors = {}
  let message = `Request failed (${status})`
  if (data && typeof data.detail === 'string') {
    message = data.detail
  } else if (data && Array.isArray(data.detail)) {
    for (const err of data.detail) {
      const field = err.loc?.[err.loc.length - 1]
      const msg = String(err.msg || 'Invalid value').replace(/^Value error, /, '')
      if (field !== undefined) fieldErrors[field] = msg
    }
    message = Object.values(fieldErrors).join('. ') || 'Please check the form.'
  }
  return new ApiError(status, message, fieldErrors)
}

export async function request(method, path, { body, params } = {}) {
  const qs = new URLSearchParams()
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') qs.set(k, v)
  })
  const url = `${BASE}${path}${qs.toString() ? `?${qs}` : ''}`
  let res
  try {
    res = await fetch(url, {
      method,
      credentials: 'include', // send the HttpOnly session cookie
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Is the backend running?')
  }
  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith('/auth/')) onUnauthorized()
    throw parseError(res.status, data)
  }
  return data
}

export const get = (path, params) => request('GET', path, { params })
export const post = (path, body) => request('POST', path, { body: body ?? {} })
export const patch = (path, body) => request('PATCH', path, { body })
export const put = (path, body) => request('PUT', path, { body })
export const del = (path) => request('DELETE', path)
