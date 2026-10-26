import { FormEvent, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { resendVerification } from '../api/auth'
import { getErrorMessage } from '../lib/errors'

export default function ResendVerification() {
  const [params] = useSearchParams()
  const [email, setEmail] = useState(params.get('email') ?? '')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setMessage(null)
    setSubmitting(true)
    try {
      setMessage(await resendVerification(email))
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-bg">
      <section className="auth-story"><h1>Verify your email</h1><p>We can send you a fresh verification link.</p></section>
      <div className="auth-side">
        <header className="auth-topline"><Link to="/login">Back to sign in</Link></header>
        <main className="auth-main">
          <form className="auth-card" onSubmit={handleSubmit}>
            <h1>Resend verification</h1>
            <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></label>
            {message && <p className="notice" role="status">{message}</p>}
            {error && <p className="error" role="alert">{error}</p>}
            <button type="submit" disabled={submitting}>{submitting ? 'Sending…' : 'Send verification email'}</button>
          </form>
        </main>
      </div>
    </div>
  )
}
