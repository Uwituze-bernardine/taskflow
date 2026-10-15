import { FormEvent, useEffect, useState } from 'react'
import { createTaskTag, deleteTaskTag, listTaskTags } from '../api/taskTags'
import { getErrorMessage } from '../lib/errors'
import type { TaskTag } from '../types'

// FR-094: administrators curate the known tag registry (tasks can still use any free-text tag).
export default function AdminTags() {
  const [tags, setTags] = useState<TaskTag[]>([])
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  function load() {
    setLoading(true)
    listTaskTags().then(setTags).catch((err) => setError(getErrorMessage(err))).finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await createTaskTag(name)
      setName('')
      load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleDelete(tag: TaskTag) {
    if (!confirm(`Remove "${tag.name}" from the suggested tag list?`)) return
    setError(null)
    try {
      await deleteTaskTag(tag.id)
      load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <div>
      <h1>Task tags</h1>
      <p className="muted">
        A curated list of tags people can pick from when tagging a task, for consistency. This doesn't
        stop anyone from typing a tag that isn't on this list.
      </p>

      <form className="inline-form" onSubmit={handleCreate}>
        <input placeholder="New tag name" value={name} onChange={(e) => setName(e.target.value)} required />
        <button type="submit">Add tag</button>
      </form>

      {error && <p className="error">{error}</p>}
      {loading ? (
        <p>Loading…</p>
      ) : (
        <div className="chips">
          {tags.map((t) => (
            <span key={t.id} className="chip removable">
              {t.name}
              <button className="chip-remove" onClick={() => handleDelete(t)} aria-label={`Remove ${t.name}`}>×</button>
            </span>
          ))}
          {tags.length === 0 && <p className="muted">No tags yet.</p>}
        </div>
      )}
    </div>
  )
}
