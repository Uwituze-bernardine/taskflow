import { ChangeEvent, useEffect, useRef, useState } from 'react'
import {
  deleteAttachment, downloadAttachment, getAttachmentSettings, uploadAttachment,
} from '../api/attachments'
import { getErrorMessage } from '../lib/errors'
import { formatBytes, formatDateTime, fullName } from '../lib/labels'
import type { Attachment, AttachmentSettings } from '../types'

interface Props {
  taskId: number
  attachments: Attachment[]
  canUpload: boolean
  onChanged: (attachments: Attachment[]) => void
}

// FR-049 upload, FR-050 download, FR-051 metadata, FR-052 restrictions shown up front, FR-053 remove.
export default function AttachmentPanel({ taskId, attachments, canUpload, onChanged }: Props) {
  const [settings, setSettings] = useState<AttachmentSettings | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (canUpload) getAttachmentSettings().then(setSettings).catch(() => {})
  }, [canUpload])

  async function handleFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    setUploading(true)
    try {
      const attachment = await uploadAttachment(taskId, file)
      onChanged([attachment, ...attachments])
    } catch (err) {
      setError(getErrorMessage(err, 'Could not upload this file.'))
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  async function handleDelete(a: Attachment) {
    if (!confirm(`Remove "${a.filename}"?`)) return
    setError(null)
    try {
      await deleteAttachment(a.id)
      onChanged(attachments.filter((x) => x.id !== a.id))
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  if (!canUpload && attachments.length === 0) return null

  return (
    <div className="panel wide-panel">
      <h2>Attachments</h2>
      {attachments.length > 0 ? (
        <ul className="attachment-list">
          {attachments.map((a) => (
            <li key={a.id}>
              <button className="link-btn filename" onClick={() => downloadAttachment(a.id, a.filename)}>{a.filename}</button>
              <span className="muted">{formatBytes(a.size_bytes)}</span>
              <span className="muted">{fullName(a.uploaded_by_detail)} · {formatDateTime(a.uploaded_at)}</span>
              {a.can_delete && <button className="btn-secondary" onClick={() => handleDelete(a)}>Remove</button>}
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No attachments yet.</p>
      )}
      {canUpload && (
        <>
          <input ref={inputRef} type="file" onChange={handleFile} disabled={uploading} />
          {settings && (
            <p className="muted small">
              Max {settings.max_size_mb}MB. Allowed types: {settings.extension_list.join(', ')}.
            </p>
          )}
        </>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  )
}
