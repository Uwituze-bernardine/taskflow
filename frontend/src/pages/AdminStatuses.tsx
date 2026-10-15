import { FormEvent, useEffect, useState } from 'react'
import {
  createCustomStatus, deleteCustomStatus, listCustomStatuses, updateCustomStatus,
} from '../api/customStatuses'
import { getErrorMessage } from '../lib/errors'
import { TASK_STATUSES, TASK_STATUS_LABELS } from '../lib/labels'
import type { CustomTaskStatus, TaskStatus } from '../types'

const EMPTY = { name: '', category: 'IN_PROGRESS' as TaskStatus, order: 0 }

// FR-035: administrators configure custom task statuses.
export default function AdminStatuses() {
  const [statuses, setStatuses] = useState<CustomTaskStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY)

  function load() {
    setLoading(true)
    listCustomStatuses().then(setStatuses).catch((err) => setError(getErrorMessage(err))).finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await createCustomStatus(form)
      setForm(EMPTY)
      setShowForm(false)
      load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function toggleActive(s: CustomTaskStatus) {
    setError(null)
    try {
      await updateCustomStatus(s.id, { is_active: !s.is_active })
      load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleDelete(s: CustomTaskStatus) {
    if (!confirm(`Delete "${s.name}"? This only works if no task is using it.`)) return
    setError(null)
    try {
      await deleteCustomStatus(s.id)
      load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Task statuses</h1>
          <p className="muted">
            Every task moves through the six predefined statuses below. Add a status here to give one of them
            a more specific name (e.g. "QA Testing" as a kind of Under Review) without changing how progress or workflow rules work.
          </p>
        </div>
        <button onClick={() => setShowForm((s) => !s)}>{showForm ? 'Cancel' : 'New status'}</button>
      </div>

      {showForm && (
        <form className="panel" onSubmit={handleCreate}>
          <div className="form-grid">
            <label>Name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required maxLength={50} /></label>
            <label>
              Behaves like
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value as TaskStatus })}>
                {TASK_STATUSES.map((s) => <option key={s} value={s}>{TASK_STATUS_LABELS[s]}</option>)}
              </select>
            </label>
            <label>Order<input type="number" value={form.order} onChange={(e) => setForm({ ...form, order: Number(e.target.value) })} /></label>
          </div>
          <button type="submit">Create status</button>
        </form>
      )}

      {error && <p className="error">{error}</p>}
      {loading ? (
        <p>Loading…</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Name</th><th>Behaves like</th><th>In use</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {statuses.map((s) => (
                <tr key={s.id} className={s.is_active ? '' : 'row-inactive'}>
                  <td><strong>{s.name}</strong></td>
                  <td>{TASK_STATUS_LABELS[s.category]}</td>
                  <td>{s.task_count} task{s.task_count === 1 ? '' : 's'}</td>
                  <td><span className={`badge ${s.is_active ? 'status-active' : 'status-inactive'}`}>{s.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td className="actions">
                    <button className="btn-secondary" onClick={() => toggleActive(s)}>{s.is_active ? 'Deactivate' : 'Activate'}</button>
                    <button className="btn-danger" disabled={s.task_count > 0} onClick={() => handleDelete(s)}>Delete</button>
                  </td>
                </tr>
              ))}
              {statuses.length === 0 && <tr><td colSpan={5} className="muted">No custom statuses yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
