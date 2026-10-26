import { FormEvent, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { confirmPasswordReset } from '../api/auth'
import { getErrorMessage } from '../lib/errors'

export default function ResetPassword() {
  const [params] = useSearchParams()
  const uid = params.get('uid') ?? ''
  const token = params.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setMessage(null)
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      setMessage(await confirmPasswordReset(uid, token, password))
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-bg">
      <section className="auth-story"><h1>Choose a new password</h1><p>Use a strong password you haven’t used elsewhere.</p></section>
      <div className="auth-side">
        <header className="auth-topline"><Link to="/login">Back to sign in</Link></header>
        <main className="auth-main">
          <form className="auth-card" onSubmit={handleSubmit}>
            <h1>Reset password</h1>
            {!uid || !token ? (
              <p className="error" role="alert">This password reset link is incomplete or invalid.</p>
            ) : message ? (
              <><p className="notice" role="status">{message}</p><Link to="/login">Sign in</Link></>
            ) : (
              <>
                <label>New password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" required /></label>
                <label>Confirm new password<input type="password" value={confirm} onChange={(event) => setConfirm(event.target.value)} autoComplete="new-password" required /></label>
                {error && <p className="error" role="alert">{error}</p>}
                <button type="submit" disabled={submitting}>{submitting ? 'Resetting…' : 'Set new password'}</button>
              </>
            )}
          </form>
        </main>
      </div>
    </div>
  )
}
