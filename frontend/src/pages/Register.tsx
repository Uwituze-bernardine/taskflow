import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../lib/errors'

// FR-001: self-registration. New accounts are always Team Members;
// an administrator can grant a higher role afterwards.
export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    username: '', email: '', first_name: '', last_name: '', password: '', confirm: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (form.password !== form.confirm) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      const { confirm: _confirm, ...payload } = form
      await register(payload)
      navigate('/dashboard')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-center">
      <form className="auth-card wide" onSubmit={handleSubmit}>
        <h1>Create your account</h1>
        <div className="form-grid">
          <label>First name<input value={form.first_name} onChange={set('first_name')} required /></label>
          <label>Last name<input value={form.last_name} onChange={set('last_name')} required /></label>
        </div>
        <label>Username<input value={form.username} onChange={set('username')} required autoComplete="username" /></label>
        <label>Email<input type="email" value={form.email} onChange={set('email')} required /></label>
        <label>
          Password
          <input type="password" value={form.password} onChange={set('password')} required autoComplete="new-password" />
        </label>
        <label>
          Confirm password
          <input type="password" value={form.confirm} onChange={set('confirm')} required autoComplete="new-password" />
        </label>
        <p className="muted">At least 8 characters, not too common, and not entirely numeric.</p>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={submitting}>{submitting ? 'Creating account…' : 'Create account'}</button>
        <p className="muted center">Already have an account? <Link to="/login">Sign in</Link></p>
      </form>
    </div>
  )
}
