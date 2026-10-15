import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import loginBackground from '../assets/login-bg.jpg'
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
    <div className="auth-bg" style={{ backgroundImage: `url(${loginBackground})` }}>
      <main className="auth-main">
        <form className="auth-card" onSubmit={handleSubmit}>
          <h1>TaskFlow</h1>
          <p className="muted">Sign in to your account</p>
          <label>
            Username
            <input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
          <p className="muted center">
            No account yet? <Link to="/register">Create one</Link>
          </p>
        </form>
      </main>
      <footer className="auth-footer">
        <span>© {new Date().getFullYear()} TaskFlow. All rights reserved.</span>
        <span>Task Management System</span>
      </footer>
    </div>
  )
}
