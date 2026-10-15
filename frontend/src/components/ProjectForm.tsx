import { FormEvent, useEffect, useState } from 'react'
import { createProject, updateProject, ProjectInput } from '../api/projects'
import { listUsers } from '../api/users'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../lib/errors'
import { PROJECT_STATUS_LABELS, fullName } from '../lib/labels'
import { isAdmin } from '../lib/roles'
import type { Project, ProjectStatus, UserSummary } from '../types'

// Closing and archiving have their own buttons, so they are not offered here.
const EDITABLE_STATUSES: ProjectStatus[] = ['PLANNED', 'ACTIVE', 'ON_HOLD']

interface Props {
  project?: Project // present = edit mode
  onSaved: (project: Project) => void
  onCancel: () => void
}

// FR-008 (create), FR-009 (edit), FR-014 (start date + expected completion date).
export default function ProjectForm({ project, onSaved, onCancel }: Props) {
  const { user } = useAuth()
  const [name, setName] = useState(project?.name ?? '')
  const [description, setDescription] = useState(project?.description ?? '')
  const [startDate, setStartDate] = useState(project?.start_date ?? '')
  const [endDate, setEndDate] = useState(project?.end_date ?? '')
  const [status, setStatus] = useState<ProjectStatus>(project?.status ?? 'PLANNED')
  const [managerId, setManagerId] = useState<string>(project ? String(project.manager) : '')
  const [managers, setManagers] = useState<UserSummary[]>([])
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Only administrators can choose a manager other than themselves.
  useEffect(() => {
    if (!isAdmin(user?.role)) return
    listUsers().then((all) => setManagers(all.filter((u) => u.role === 'ADMIN' || u.role === 'PROJECT_MANAGER'))).catch(() => {})
  }, [user?.role])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    const payload: ProjectInput = {
      name,
      description,
      status,
      start_date: startDate || null,
      end_date: endDate || null,
    }
    if (isAdmin(user?.role) && managerId) payload.manager = Number(managerId)
    try {
      onSaved(project ? await updateProject(project.id, payload) : await createProject(payload))
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="create-task-form" onSubmit={handleSubmit}>
      <label>
        Project name
        <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={200} />
      </label>
      <label>
        Description
        <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <div className="form-row">
        <label>
          Start date
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </label>
        <label>
          Expected completion date
          <input type="date" value={endDate} min={startDate || undefined} onChange={(e) => setEndDate(e.target.value)} />
        </label>
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value as ProjectStatus)}>
            {EDITABLE_STATUSES.map((s) => (
              <option key={s} value={s}>{PROJECT_STATUS_LABELS[s]}</option>
            ))}
          </select>
        </label>
        {isAdmin(user?.role) && (
          <label>
            Project manager
            <select value={managerId} onChange={(e) => setManagerId(e.target.value)}>
              {!project && <option value="">Me</option>}
              {managers.map((m) => (
                <option key={m.id} value={m.id}>{fullName(m)}</option>
              ))}
            </select>
          </label>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      <div className="form-actions">
        <button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : project ? 'Save changes' : 'Create project'}
        </button>
        <button type="button" className="secondary" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}
