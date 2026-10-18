import { useState } from 'react'
import { Field } from '../components/Field'
import { PageHeader } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

export default function Settings() {
  const { user, updateProfile } = useAuth()
  const toast = useToast()
  const [form, setForm] = useState({ name: user.name, timezone: user.timezone })
  const [errors, setErrors] = useState({})
  const zones = Intl.supportedValuesOf ? Intl.supportedValuesOf('timeZone') : [user.timezone]

  async function submit(e) {
    e.preventDefault()
    setErrors({})
    try {
      await updateProfile(form)
      toast.success('Settings saved')
    } catch (err) {
      setErrors(err.fieldErrors || {})
      toast.error(err.message)
    }
  }

  return (
    <>
      <PageHeader title="Settings" subtitle={user.email} />
      <form className="card form-narrow" onSubmit={submit}>
        <Field label="Name" error={errors.name}>
          {(p) => <input {...p} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />}
        </Field>
        <Field label="Timezone" error={errors.timezone}
          hint="Decides what “today” means and how due dates are shown. Times are stored in UTC.">
          {(p) => (
            <select {...p} value={form.timezone} onChange={(e) => setForm({ ...form, timezone: e.target.value })}>
              {!zones.includes(form.timezone) && <option>{form.timezone}</option>}
              {zones.map((z) => <option key={z}>{z}</option>)}
            </select>
          )}
        </Field>
        <button className="btn btn-primary">Save</button>
      </form>
    </>
  )
}
