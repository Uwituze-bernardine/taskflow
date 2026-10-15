import { FormEvent, useState } from 'react'
import { addComment, deleteComment, editComment } from '../api/tasks'
import { getErrorMessage } from '../lib/errors'
import { formatDateTime, fullName } from '../lib/labels'
import type { Comment, UserSummary } from '../types'

interface Props {
  taskId: number
  comments: Comment[]
  participants: UserSummary[] // who could be @mentioned, for the hint text
  onChanged: (comments: Comment[]) => void
}

// FR-043 create, FR-044 chronological order (server-ordered, rendered as given),
// FR-045 mentions, FR-047 preserved history (deleted comments show a placeholder), FR-048 edit/delete own.
export default function CommentThread({ taskId, comments, participants, onChanged }: Props) {
  const [body, setBody] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editBody, setEditBody] = useState('')

  async function handlePost(e: FormEvent) {
    e.preventDefault()
    if (!body.trim()) return
    setError(null)
    try {
      const comment = await addComment(taskId, body)
      onChanged([...comments, comment])
      setBody('')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  function startEdit(c: Comment) {
    setEditingId(c.id)
    setEditBody(c.body)
  }

  async function saveEdit(id: number) {
    setError(null)
    try {
      const updated = await editComment(id, editBody)
      onChanged(comments.map((c) => (c.id === id ? updated : c)))
      setEditingId(null)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Delete this comment?')) return
    setError(null)
    try {
      await deleteComment(id)
      onChanged(comments.map((c) => (c.id === id ? { ...c, is_deleted: true, body: 'This comment was deleted.', can_edit: false, can_delete: false } : c)))
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <>
      <ul className="comment-list">
        {comments.map((c) => (
          <li key={c.id} className={c.is_deleted ? 'comment-deleted' : ''}>
            <strong>{fullName(c.author_detail)}</strong>
            <span className="muted"> · {formatDateTime(c.created_at)}{c.is_edited && !c.is_deleted && ' (edited)'}</span>
            {editingId === c.id ? (
              <div className="inline-form">
                <input value={editBody} onChange={(e) => setEditBody(e.target.value)} />
                <button onClick={() => saveEdit(c.id)}>Save</button>
                <button className="btn-secondary" onClick={() => setEditingId(null)}>Cancel</button>
              </div>
            ) : (
              <p className={c.is_deleted ? 'muted' : ''}>{c.body}</p>
            )}
            {(c.can_edit || c.can_delete) && editingId !== c.id && (
              <div className="comment-actions">
                {c.can_edit && <button className="link-btn" onClick={() => startEdit(c)}>Edit</button>}
                {c.can_delete && <button className="link-btn" onClick={() => handleDelete(c.id)}>Delete</button>}
              </div>
            )}
          </li>
        ))}
        {comments.length === 0 && <p className="muted">No comments yet.</p>}
      </ul>
      {error && <p className="error">{error}</p>}
      <form className="inline-form" onSubmit={handlePost}>
        <input placeholder="Add a comment… use @name to mention someone" value={body} onChange={(e) => setBody(e.target.value)} />
        <button type="submit">Post</button>
      </form>
      {participants.length > 0 && (
        <p className="muted small">
          You can mention: {participants.map((u) => `@${u.username}`).join(', ')}
        </p>
      )}
    </>
  )
}
