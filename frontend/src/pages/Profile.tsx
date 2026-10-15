import { FormEvent, useEffect, useState } from 'react'
import { getNotificationPreferences, updateNotificationPreferences } from '../api/notifications'
import { changePassword, updateMe } from '../api/users'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../lib/errors'
import { ROLE_LABELS } from '../lib/roles'
import type { NotificationCategory, NotificationPreferences } from '../types'

const PREFERENCE_LABELS: Record<Exclude<NotificationCategory, 'other'>, string> = {
  assigned: 'A task is assigned to you',
  status_changed: "A task's status changes",
  mentioned: 'You are mentioned in a comment',
  due_soon: 'A task you own is due soon',
  overdue: 'A task you own becomes overdue',
}

// FR-003: users update their own profile information. Also hosts FR-059 notification preferences.
export default function Profile() {
  const { user, setCurrentUser } = useAuth()
  const [form, setForm] = useState({
    first_name: user?.first_name ?? '',
    last_name: user?.last_name ?? '',
    email: user?.email ?? '',
    job_title: user?.job_title ?? '',
    phone: user?.phone ?? '',
  })
  const [profileMsg, setProfileMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [pw, setPw] = useState({ current: '', next: '', confirm: '' })
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [prefs, setPrefs] = useState<NotificationPreferences | null>(null)
  const [prefsMsg, setPrefsMsg] = useState<string | null>(null)

  useEffect(() => {
    getNotificationPreferences().then(setPrefs).catch(() => {})
  }, [])

  async function togglePreference(key: keyof NotificationPreferences) {
    if (!prefs) return
    const next = !prefs[key]
    setPrefs({ ...prefs, [key]: next }) // optimistic
    setPrefsMsg(null)
    try {
      setPrefs(await updateNotificationPreferences({ [key]: next }))
    } catch (err) {
      setPrefs((p) => (p ? { ...p, [key]: !next } : p)) // revert on failure
      setPrefsMsg(getErrorMessage(err))
    }
  }

  if (!user) return null

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  async function saveProfile(e: FormEvent) {
    e.preventDefault()
    setProfileMsg(null)
    try {
      setCurrentUser(await updateMe(form))
      setProfileMsg({ ok: true, text: 'Profile updated.' })
    } catch (err) {
      setProfileMsg({ ok: false, text: getErrorMessage(err) })
    }
  }

  async function savePassword(e: FormEvent) {
    e.preventDefault()
    setPwMsg(null)
    if (pw.next !== pw.confirm) {
      setPwMsg({ ok: false, text: 'New passwords do not match.' })
      return
    }
    try {
      await changePassword(pw.current, pw.next)
      setPw({ current: '', next: '', confirm: '' })
      setPwMsg({ ok: true, text: 'Password changed.' })
    } catch (err) {
      setPwMsg({ ok: false, text: getErrorMessage(err) })
    }
  }

  return (
    <div>
      <h1>My profile</h1>
      <p className="muted">
        Signed in as <strong>{user.username}</strong> · {ROLE_LABELS[user.role]}
      </p>

      <form className="panel" onSubmit={saveProfile}>
        <h2>Profile information</h2>
        <div className="form-grid">
          <label>First name<input value={form.first_name} onChange={set('first_name')} required /></label>
          <label>Last name<input value={form.last_name} onChange={set('last_name')} required /></label>
          <label>Email<input type="email" value={form.email} onChange={set('email')} required /></label>
          <label>Job title<input value={form.job_title} onChange={set('job_title')} /></label>
          <label>Phone<input value={form.phone} onChange={set('phone')} /></label>
        </div>
        {profileMsg && <p className={profileMsg.ok ? 'success' : 'error'}>{profileMsg.text}</p>}
        <button type="submit">Save changes</button>
      </form>

      <form className="panel" onSubmit={savePassword}>
        <h2>Change password</h2>
        <div className="form-grid">
          <label>
            Current password
            <input type="password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} required autoComplete="current-password" />
          </label>
          <span />
          <label>
            New password
            <input type="password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} required autoComplete="new-password" />
          </label>
          <label>
            Confirm new password
            <input type="password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} required autoComplete="new-password" />
          </label>
        </div>
        {pwMsg && <p className={pwMsg.ok ? 'success' : 'error'}>{pwMsg.text}</p>}
        <button type="submit">Change password</button>
      </form>

      <div className="panel">
        <h2>Notification preferences</h2>
        <p className="muted">Choose what you get notified about.</p>
        {prefs ? (
          <div className="preference-list">
            {(Object.keys(PREFERENCE_LABELS) as (keyof NotificationPreferences)[]).map((key) => (
              <label key={key} className="checkbox-row">
                <input type="checkbox" checked={prefs[key]} onChange={() => togglePreference(key)} />
                {PREFERENCE_LABELS[key]}
              </label>
            ))}
          </div>
        ) : (
          <p className="muted">Loading…</p>
        )}
        {prefsMsg && <p className="error">{prefsMsg}</p>}
      </div>
    </div>
  )
}
