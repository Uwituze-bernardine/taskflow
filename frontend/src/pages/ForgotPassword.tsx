import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { requestPasswordReset } from '../api/auth'
import { getErrorMessage } from '../lib/errors'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setMessage(null)
    setError(null)
    setSubmitting(true)
    try {
      setMessage(await requestPasswordReset(email))
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-bg">
      <section className="auth-story"><h1>Reset your password</h1><p>We’ll send a secure reset link to your email.</p></section>
      <div className="auth-side">
        <header className="auth-topline"><Link to="/login">Back to sign in</Link></header>
        <main className="auth-main">
          <form className="auth-card" onSubmit={handleSubmit}>
            <h1>Forgot password?</h1>
            <p className="muted">Enter the email address associated with your account.</p>
            <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></label>
            {message && <p className="notice" role="status">{message}</p>}
            {error && <p className="error" role="alert">{error}</p>}
            <button type="submit" disabled={submitting}>{submitting ? 'Sending…' : 'Send reset link'}</button>
          </form>
        </main>
      </div>
    </div>
  )
}
