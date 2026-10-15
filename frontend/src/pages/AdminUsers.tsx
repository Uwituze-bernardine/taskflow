import { FormEvent, useCallback, useEffect, useState } from 'react'
import {
  createUser, deactivateUser, listUsersPage, reactivateUser, resetUserPassword, updateUser,
} from '../api/users'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../lib/errors'
import { ROLE_LABELS, ROLE_OPTIONS } from '../lib/roles'
import type { Role, User } from '../types'

const PAGE_SIZE = 25
const EMPTY_FORM = { username: '', email: '', first_name: '', last_name: '', password: '', role: 'TEAM_MEMBER' as Role }

// FR-004 / FR-005 / FR-007: administrators create, deactivate/reactivate,
// assign roles to, and reset the access of user accounts.
export default function AdminUsers() {
  const { user: me } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [role, setRole] = useState<Role | ''>('')
  const [active, setActive] = useState<'' | 'true' | 'false'>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [resetTarget, setResetTarget] = useState<User | null>(null)

  useEffect(() => {
    const t = setTimeout(() => { setDebouncedSearch(search); setPage(1) }, 300)
    return () => clearTimeout(t)
  }, [search])

  const load = useCallback(() => {
    setLoading(true)
    listUsersPage({
      search: debouncedSearch,
      role,
      is_active_member: active === '' ? '' : active === 'true',
      page,
    })
      .then((data) => { setUsers(data.results); setCount(data.count) })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [debouncedSearch, role, active, page])

  useEffect(load, [load])

  async function run(action: () => Promise<unknown>, success?: string) {
    setError(null)
    setNotice(null)
    try {
      await action()
      if (success) setNotice(success)
      load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    await run(async () => {
      await createUser(form)
      setForm(EMPTY_FORM)
      setShowForm(false)
    }, 'User created.')
  }

  async function handleDeactivate(u: User) {
    if (!confirm(`Deactivate ${u.username}? They will be signed out and unable to log in.`)) return
    await run(() => deactivateUser(u.id), `${u.username} deactivated.`)
  }

  const setField = (key: keyof typeof EMPTY_FORM) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>User management</h1>
          <p className="muted">{count} account{count === 1 ? '' : 's'}</p>
        </div>
        <button onClick={() => setShowForm((s) => !s)}>{showForm ? 'Cancel' : 'New user'}</button>
      </div>

      {showForm && (
        <form className="panel" onSubmit={handleCreate}>
          <h2>Create user</h2>
          <div className="form-grid">
            <label>First name<input value={form.first_name} onChange={setField('first_name')} required /></label>
            <label>Last name<input value={form.last_name} onChange={setField('last_name')} required /></label>
            <label>Username<input value={form.username} onChange={setField('username')} required /></label>
            <label>Email<input type="email" value={form.email} onChange={setField('email')} required /></label>
            <label>Initial password<input type="password" value={form.password} onChange={setField('password')} required autoComplete="new-password" /></label>
            <label>
              Role
              <select value={form.role} onChange={setField('role')}>
                {ROLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
          </div>
          <button type="submit">Create user</button>
        </form>
      )}

      <div className="filter-bar">
        <input placeholder="Search name, username or email…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select value={role} onChange={(e) => { setRole(e.target.value as Role | ''); setPage(1) }}>
          <option value="">All roles</option>
          {ROLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select value={active} onChange={(e) => { setActive(e.target.value as '' | 'true' | 'false'); setPage(1) }}>
          <option value="">Active &amp; deactivated</option>
          <option value="true">Active only</option>
          <option value="false">Deactivated only</option>
        </select>
      </div>

      {error && <p className="error">{error}</p>}
      {notice && <p className="notice">{notice}</p>}

      {loading ? (
        <p>Loading…</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>User</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isMe = u.id === me?.id
                return (
                  <tr key={u.id} className={u.is_active_member ? '' : 'row-inactive'}>
                    <td>
                      <strong>{u.first_name} {u.last_name}</strong>
                      <div className="muted">@{u.username}{isMe && ' (you)'}</div>
                    </td>
                    <td>{u.email}</td>
                    <td>
                      <select
                        value={u.role}
                        disabled={isMe}
                        title={isMe ? 'You cannot change your own role' : ROLE_LABELS[u.role]}
                        onChange={(e) => run(() => updateUser(u.id, { role: e.target.value as Role }), `${u.username} is now ${ROLE_LABELS[e.target.value as Role]}.`)}
                      >
                        {ROLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                      </select>
                    </td>
                    <td>
                      <span className={`badge ${u.is_active_member ? 'status-active' : 'status-inactive'}`}>
                        {u.is_active_member ? 'Active' : 'Deactivated'}
                      </span>
                    </td>
                    <td className="actions">
                      <button className="btn-secondary" onClick={() => setResetTarget(u)}>Reset password</button>
                      {u.is_active_member ? (
                        <button className="btn-danger" disabled={isMe} onClick={() => handleDeactivate(u)}>Deactivate</button>
                      ) : (
                        <button onClick={() => run(() => reactivateUser(u.id), `${u.username} reactivated.`)}>Reactivate</button>
                      )}
                    </td>
                  </tr>
                )
              })}
              {users.length === 0 && (
                <tr><td colSpan={5} className="muted">No users match these filters.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {pages > 1 && (
        <div className="pager">
          <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
          <span className="muted">Page {page} of {pages}</span>
          <button className="btn-secondary" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      )}

      {resetTarget && (
        <ResetPasswordModal
          user={resetTarget}
          onClose={() => setResetTarget(null)}
          onDone={(message) => { setResetTarget(null); setNotice(message); setError(null) }}
        />
      )}
    </div>
  )
}

// FR-007: reset a user's access - generate a one-time temporary password, or set a specific one.
function ResetPasswordModal({ user, onClose, onDone }: { user: User; onClose: () => void; onDone: (message: string) => void }) {
  const [mode, setMode] = useState<'generate' | 'custom'>('generate')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const { temporary_password } = await resetUserPassword(user.id, mode === 'custom' ? password : undefined)
      onDone(
        temporary_password
          ? `Temporary password for ${user.username}: ${temporary_password} — shown only once, share it securely.`
          : `Password set for ${user.username}. They've been signed out of their other sessions.`
      )
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal-panel" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Reset password for {user.first_name} {user.last_name}</h2>
        <p className="muted">This ends all of @{user.username}'s current sessions - they'll need to sign in again.</p>

        <label className="radio-row">
          <input type="radio" name="reset-mode" checked={mode === 'generate'} onChange={() => setMode('generate')} />
          Generate a one-time temporary password
        </label>
        <label className="radio-row">
          <input type="radio" name="reset-mode" checked={mode === 'custom'} onChange={() => setMode('custom')} />
          Set a specific password
        </label>
        {mode === 'custom' && (
          <input
            type="password"
            placeholder="New password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
            autoFocus
          />
        )}

        {error && <p className="error">{error}</p>}
        <div className="form-actions">
          <button type="submit" disabled={submitting || (mode === 'custom' && !password)}>
            {submitting ? 'Resetting…' : 'Reset password'}
          </button>
          <button type="button" className="secondary" onClick={onClose}>Cancel</button>
        </div>
      </form>
    </div>
  )
}
