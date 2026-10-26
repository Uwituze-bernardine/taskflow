import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { verifyEmail } from '../api/auth'
import { getErrorMessage } from '../lib/errors'

export default function VerifyEmail() {
  const [params] = useSearchParams()
  const uid = params.get('uid') ?? ''
  const token = params.get('token') ?? ''
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!uid || !token) {
      setError('This verification link is incomplete or invalid.')
      return
    }
    verifyEmail(uid, token)
      .then(setMessage)
      .catch((err: unknown) => setError(getErrorMessage(err)))
  }, [uid, token])

  return (
    <div className="auth-bg">
      <section className="auth-story"><h1>Verify your email</h1><p>One last step to activate your TaskFlow account.</p></section>
      <div className="auth-side">
        <main className="auth-main">
          <div className="auth-card">
            <h1>Email verification</h1>
            {!message && !error && <p className="muted" role="status">Verifying your email…</p>}
            {message && <><p className="notice" role="status">{message}</p><Link to="/login">Continue to sign in</Link></>}
            {error && <><p className="error" role="alert">{error}</p><Link to="/resend-verification">Request a new verification link</Link></>}
          </div>
        </main>
      </div>
    </div>
  )
}
