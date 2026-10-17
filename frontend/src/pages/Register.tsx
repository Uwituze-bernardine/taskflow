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
    <div className="auth-bg auth-register">
      <section className="auth-story">
        <Link to="/" className="auth-brand"><span className="auth-brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none"><rect x="2.5" y="2.5" width="27" height="27" rx="6" /><path d="m8 16 5.2 5.2L24 10.5" /></svg></span>TaskFlow</Link>
        <p className="auth-tagline">Plan&nbsp; · &nbsp;Assign&nbsp; · &nbsp;Track&nbsp; · &nbsp;Achieve</p>
        <div className="auth-story-copy">
          <h2>Make great work happen.</h2>
          <p>Bring your team and projects together. Start with a clear plan and build momentum, one task at a time.</p>
        </div>
        <div className="register-story-note"><span aria-hidden="true">✦</span><span><strong>Your team’s work, in sync.</strong><small>One shared space for projects, tasks, and progress.</small></span></div>
      </section>
      <div className="auth-side">
        <header className="auth-topline"><span>Already have an account?</span> <Link to="/login">Sign in</Link></header>
        <main className="auth-main">
          <form className="auth-card wide" onSubmit={handleSubmit}>
            <div className="auth-form-brand"><span className="auth-brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none"><rect x="2.5" y="2.5" width="27" height="27" rx="6" /><path d="m8 16 5.2 5.2L24 10.5" /></svg></span>TaskFlow</div>
            <h1>Create your account</h1>
            <p className="muted">Set up your profile to get started with your workspace.</p>
            <div className="form-grid">
              <label>First name<input value={form.first_name} onChange={set('first_name')} required autoComplete="given-name" /></label>
              <label>Last name<input value={form.last_name} onChange={set('last_name')} required autoComplete="family-name" /></label>
            </div>
            <label>Username<input value={form.username} onChange={set('username')} required autoComplete="username" /></label>
            <label>Email<input type="email" value={form.email} onChange={set('email')} required autoComplete="email" /></label>
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
            <button type="submit" disabled={submitting}>{submitting ? 'Creating account…' : 'Create account'} <span aria-hidden="true">→</span></button>
          </form>
        </main>
        <footer className="auth-footer"><span>© {new Date().getFullYear()} TaskFlow</span><span>Plan · Assign · Track · Achieve</span></footer>
      </div>
    </div>
  )
}
