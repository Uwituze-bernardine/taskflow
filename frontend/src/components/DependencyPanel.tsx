import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { addDependency, getDependencyCandidates, removeDependency } from '../api/tasks'
import { getErrorMessage } from '../lib/errors'
import type { Task, TaskRef } from '../types'
import { StatusBadge } from './Badges'

interface Props {
  task: Task
  canEdit: boolean
  onChanged: (task: Task) => void
}

// FR-041: predecessors this task waits on. FR-042's enforcement itself is shown on the task page
// via `is_blocked_by_dependencies` / `blocked_by` / `completion_blockers`.
export default function DependencyPanel({ task, canEdit, onChanged }: Props) {
  const [candidates, setCandidates] = useState<TaskRef[]>([])
  const [choice, setChoice] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (canEdit) getDependencyCandidates(task.id).then(setCandidates).catch(() => {})
  }, [canEdit, task.id, task.depends_on.length])

  async function handleAdd() {
    if (!choice) return
    setError(null)
    try {
      onChanged(await addDependency(task.id, Number(choice)))
      setChoice('')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleRemove(predecessorId: number) {
    setError(null)
    try {
      onChanged(await removeDependency(task.id, predecessorId))
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  if (!canEdit && task.depends_on_detail.length === 0 && task.blocks_detail.length === 0) return null

  return (
    <div className="panel wide-panel">
      <h2>Dependencies</h2>
      {task.depends_on_detail.length > 0 && (
        <>
          <strong className="small-label">Waiting on</strong>
          <ul className="dependency-list">
            {task.depends_on_detail.map((d) => (
              <li key={d.id}>
                <Link to={`/tasks/${d.id}`}>{d.title}</Link>
                <StatusBadge status={d.status} />
                {canEdit && <button className="btn-secondary" onClick={() => handleRemove(d.id)}>Remove</button>}
              </li>
            ))}
          </ul>
        </>
      )}
      {task.blocks_detail.length > 0 && (
        <>
          <strong className="small-label">Blocks</strong>
          <ul className="dependency-list">
            {task.blocks_detail.map((d) => (
              <li key={d.id}>
                <Link to={`/tasks/${d.id}`}>{d.title}</Link>
                <StatusBadge status={d.status} />
              </li>
            ))}
          </ul>
        </>
      )}
      {canEdit && (
        <div className="inline-form">
          <select value={choice} onChange={(e) => setChoice(e.target.value)}>
            <option value="">Add a predecessor…</option>
            {candidates.map((c) => (
              <option key={c.id} value={c.id}>{c.title} ({c.status_label})</option>
            ))}
          </select>
          <button disabled={!choice} onClick={handleAdd}>Add</button>
        </div>
      )}
      {error && <p className="error">{error}</p>}
      <p className="muted small">
        {task.enforce_dependencies
          ? 'Enforced: this task cannot start until every predecessor is completed.'
          : 'Not enforced: predecessors are informational only. Turn on enforcement while editing the task.'}
      </p>
    </div>
  )
}
