import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Link } from 'react-router-dom'
import AuthSlideshow from '../components/AuthSlideshow'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../lib/errors'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(username, password)
      navigate('/dashboard')
    } catch (err) {
      setError(getErrorMessage(err, 'Could not sign in.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-bg">
      <section className="auth-story">
        <AuthSlideshow />
        <div className="auth-brand">
          <span className="auth-brand-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32" fill="none">
              <rect x="2.5" y="2.5" width="27" height="27" rx="6" />
              <path d="m8 16 5.2 5.2L24 10.5" />
            </svg>
          </span>
          <span>TaskFlow</span>
        </div>
        <p className="auth-tagline">Plan&nbsp; · &nbsp;Assign&nbsp; · &nbsp;Track&nbsp; · &nbsp;Achieve</p>
        <div className="auth-story-copy">
          <h2>Work smarter,<br />not harder.</h2>
          <p>Bring your tasks, projects, and team together — and make every day count.</p>
        </div>
        <ul className="auth-highlights">
          <li><span aria-hidden="true">✦</span><strong>Manage teams</strong><small>Keep everyone moving together</small></li>
          <li><span aria-hidden="true">✓</span><strong>Organize projects</strong><small>Turn big goals into clear steps</small></li>
          <li><span aria-hidden="true">↗</span><strong>Track progress</strong><small>See how far your team has come</small></li>
        </ul>
      </section>
      <div className="auth-side">
        <header className="auth-topline">
          <span>Don’t have an account?</span> <Link to="/register">Create one</Link>
        </header>
        <main className="auth-main">
          <form className="auth-card" onSubmit={handleSubmit}>
            <div className="auth-form-brand">
              <span className="auth-brand-mark" aria-hidden="true">
                <svg viewBox="0 0 32 32" fill="none">
                  <rect x="2.5" y="2.5" width="27" height="27" rx="6" />
                  <path d="m8 16 5.2 5.2L24 10.5" />
                </svg>
              </span>
              <span>TaskFlow</span>
            </div>
            <h1>Welcome back!</h1>
            <p className="muted">Sign in to continue to your workspace.</p>
            <label>
              Username
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </label>
            {error && <p className="error">{error}</p>}
            <button type="submit" disabled={submitting}>
              {submitting ? 'Signing in…' : 'Sign in'} <span aria-hidden="true">→</span>
            </button>
          </form>
        </main>
        <footer className="auth-footer">
          <span>© {new Date().getFullYear()} TaskFlow. All rights reserved.</span>
          <span>Task Management System</span>
        </footer>
      </div>
    </div>
  )
}
