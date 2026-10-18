import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Field } from '../components/Field'
import { useAuth } from '../context/AuthContext'

function AuthShell({ title, children, footer }) {
  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h1>📚 StudyOS</h1>
        <p className="muted">{title}</p>
        {children}
        <p className="auth-footer">{footer}</p>
      </div>
    </div>
  )
}

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(form)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell title="Log in to your study planner" footer={<>New here? <Link to="/register">Create an account</Link></>}>
      <form onSubmit={submit} noValidate>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <Field label="Email">
          {(p) => <input {...p} type="email" autoComplete="email" required value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} />}
        </Field>
        <Field label="Password">
          {(p) => <input {...p} type="password" autoComplete="current-password" required value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })} />}
        </Field>
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? 'Logging in…' : 'Log in'}</button>
      </form>
    </AuthShell>
  )
}

export function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [errors, setErrors] = useState({})
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    setError(null)
    try {
      // The browser's timezone becomes the default profile timezone (changeable in Settings).
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
      await register({ ...form, timezone })
      navigate('/')
    } catch (err) {
      setErrors(err.fieldErrors || {})
      setError(Object.keys(err.fieldErrors || {}).length ? null : err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell title="Create your account" footer={<>Already registered? <Link to="/login">Log in</Link></>}>
      <form onSubmit={submit} noValidate>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <Field label="Name" error={errors.name}>
          {(p) => <input {...p} autoComplete="name" required value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })} />}
        </Field>
        <Field label="Email" error={errors.email}>
          {(p) => <input {...p} type="email" autoComplete="email" required value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} />}
        </Field>
        <Field label="Password" error={errors.password} hint="At least 8 characters.">
          {(p) => <input {...p} type="password" autoComplete="new-password" required minLength={8} value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })} />}
        </Field>
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? 'Creating…' : 'Create account'}</button>
      </form>
    </AuthShell>
  )
}
