import { FormEvent, useEffect, useState } from 'react'
import {
  createCustomPriority, deleteCustomPriority, listCustomPriorities, updateCustomPriority,
} from '../api/customPriorities'
import { getErrorMessage } from '../lib/errors'
import { PRIORITIES, PRIORITY_LABELS } from '../lib/labels'
import type { CustomPriority, Priority } from '../types'

const EMPTY = { name: '', category: 'MEDIUM' as Priority, order: 0 }

// FR-093: administrators configure custom priorities.
export default function AdminPriorities() {
  const [priorities, setPriorities] = useState<CustomPriority[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY)

  function load() {
    setLoading(true)
    listCustomPriorities().then(setPriorities).catch((err) => setError(getErrorMessage(err))).finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await createCustomPriority(form)
      setForm(EMPTY)
      setShowForm(false)
      load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function toggleActive(p: CustomPriority) {
    setError(null)
    try {
      await updateCustomPriority(p.id, { is_active: !p.is_active })
      load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleDelete(p: CustomPriority) {
    if (!confirm(`Delete "${p.name}"? This only works if no task uses it.`)) return
    setError(null)
    try {
      await deleteCustomPriority(p.id)
      load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Priorities</h1>
          <p className="muted">
            Every task has one of the four base priorities below. Add one here to give a priority a more
            specific name (e.g. "Showstopper" as a kind of Critical) without changing how sorting works.
          </p>
        </div>
        <button onClick={() => setShowForm((s) => !s)}>{showForm ? 'Cancel' : 'New priority'}</button>
      </div>

      {showForm && (
        <form className="panel" onSubmit={handleCreate}>
          <div className="form-grid">
            <label>Name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required maxLength={50} /></label>
            <label>
              Behaves like
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value as Priority })}>
                {PRIORITIES.map((p) => <option key={p} value={p}>{PRIORITY_LABELS[p]}</option>)}
              </select>
            </label>
            <label>Order<input type="number" value={form.order} onChange={(e) => setForm({ ...form, order: Number(e.target.value) })} /></label>
          </div>
          <button type="submit">Create priority</button>
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
              {priorities.map((p) => (
                <tr key={p.id} className={p.is_active ? '' : 'row-inactive'}>
                  <td><strong>{p.name}</strong></td>
                  <td>{PRIORITY_LABELS[p.category]}</td>
                  <td>{p.task_count} task{p.task_count === 1 ? '' : 's'}</td>
                  <td><span className={`badge ${p.is_active ? 'status-active' : 'status-inactive'}`}>{p.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td className="actions">
                    <button className="btn-secondary" onClick={() => toggleActive(p)}>{p.is_active ? 'Deactivate' : 'Activate'}</button>
                    <button className="btn-danger" disabled={p.task_count > 0} onClick={() => handleDelete(p)}>Delete</button>
                  </td>
                </tr>
              ))}
              {priorities.length === 0 && <tr><td colSpan={5} className="muted">No custom priorities yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
