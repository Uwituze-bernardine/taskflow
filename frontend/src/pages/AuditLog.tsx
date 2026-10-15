import { useCallback, useEffect, useState } from 'react'
import { listAuditLog } from '../api/audit'
import Pager from '../components/Pager'
import { getErrorMessage } from '../lib/errors'
import { formatDateTime } from '../lib/labels'
import type { AuditLogEntry } from '../types'

const ACTION_LABELS: Record<string, string> = {
  'task.created': 'created',
  'task.updated': 'updated',
}

// FR-085..089: who changed what, when - read-only, administrators only.
export default function AuditLog() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [modelName, setModelName] = useState('')
  const [objectId, setObjectId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    listAuditLog({ model_name: modelName || undefined, object_id: objectId || undefined, page })
      .then((d) => { setEntries(d.results); setCount(d.count) })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [modelName, objectId, page])

  useEffect(load, [load])

  return (
    <div>
      <h1>Audit log</h1>
      <p className="muted">Every recorded change to a task: who made it, what changed, and when.</p>

      <div className="filter-bar">
        <select value={modelName} onChange={(e) => { setModelName(e.target.value); setPage(1) }}>
          <option value="">All record types</option>
          <option value="Task">Task</option>
        </select>
        <input
          placeholder="Filter by record ID…"
          value={objectId}
          onChange={(e) => { setObjectId(e.target.value); setPage(1) }}
        />
      </div>

      {error && <p className="error">{error}</p>}
      {loading ? (
        <p>Loading…</p>
      ) : (
        <ul className="history">
          {entries.map((entry) => (
            <li key={entry.id}>
              <div>
                <strong>{entry.actor_username ?? 'System'}</strong>{' '}
                {ACTION_LABELS[entry.action] ?? entry.action} {entry.model_name} #{entry.object_id}
                <span className="muted"> · {formatDateTime(entry.timestamp)}</span>
              </div>
              {Object.entries(entry.changes).map(([field, change]) => (
                <div key={field} className="change">
                  {field}: <span className="from">{change.from ?? '—'}</span> → <span className="to">{change.to ?? '—'}</span>
                </div>
              ))}
            </li>
          ))}
          {entries.length === 0 && <p className="muted">No audit entries match these filters.</p>}
        </ul>
      )}
      <Pager page={page} count={count} onChange={setPage} />
    </div>
  )
}
