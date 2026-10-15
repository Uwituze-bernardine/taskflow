import { FormEvent, useEffect, useState } from 'react'
import { getAttachmentSettings, updateAttachmentSettings } from '../api/attachments'
import { getNotificationSettings, updateNotificationSettings } from '../api/notifications'
import { getErrorMessage } from '../lib/errors'
import type { AttachmentSettings } from '../types'

// FR-095 notification settings, and FR-052's configuration half (file size/type limits).
export default function AdminSettings() {
  const [dueSoonDays, setDueSoonDays] = useState(2)
  const [notifMsg, setNotifMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const [attachmentSettings, setAttachmentSettings] = useState<AttachmentSettings | null>(null)
  const [maxSize, setMaxSize] = useState(25)
  const [extensions, setExtensions] = useState('')
  const [attachMsg, setAttachMsg] = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => {
    getNotificationSettings().then((s) => setDueSoonDays(s.due_soon_days)).catch(() => {})
    getAttachmentSettings().then((s) => {
      setAttachmentSettings(s)
      setMaxSize(s.max_size_mb)
      setExtensions(s.allowed_extensions)
    }).catch(() => {})
  }, [])

  async function saveNotifications(e: FormEvent) {
    e.preventDefault()
    setNotifMsg(null)
    try {
      const updated = await updateNotificationSettings(dueSoonDays)
      setDueSoonDays(updated.due_soon_days)
      setNotifMsg({ ok: true, text: 'Saved.' })
    } catch (err) {
      setNotifMsg({ ok: false, text: getErrorMessage(err) })
    }
  }

  async function saveAttachments(e: FormEvent) {
    e.preventDefault()
    setAttachMsg(null)
    try {
      const updated = await updateAttachmentSettings({ max_size_mb: maxSize, allowed_extensions: extensions })
      setAttachmentSettings(updated)
      setAttachMsg({ ok: true, text: 'Saved.' })
    } catch (err) {
      setAttachMsg({ ok: false, text: getErrorMessage(err) })
    }
  }

  return (
    <div>
      <h1>System settings</h1>

      <form className="panel" onSubmit={saveNotifications}>
        <h2>Notification reminders</h2>
        <p className="muted">
          How many days before its due date a task becomes "due soon" and triggers a reminder.
          Reminders themselves are sent by a scheduled job (<code>send_deadline_reminders</code>); this
          only configures the threshold it uses.
        </p>
        <label>
          Due soon window (days)
          <input type="number" min={1} value={dueSoonDays} onChange={(e) => setDueSoonDays(Number(e.target.value))} />
        </label>
        {notifMsg && <p className={notifMsg.ok ? 'success' : 'error'}>{notifMsg.text}</p>}
        <button type="submit">Save</button>
      </form>

      <form className="panel" onSubmit={saveAttachments}>
        <h2>Attachment limits</h2>
        <p className="muted">File size and type restrictions enforced on every upload.</p>
        <div className="form-grid">
          <label>
            Max file size (MB)
            <input type="number" min={1} value={maxSize} onChange={(e) => setMaxSize(Number(e.target.value))} />
          </label>
          <label>
            Allowed extensions (comma separated)
            <input value={extensions} onChange={(e) => setExtensions(e.target.value)} placeholder="pdf,png,docx" />
          </label>
        </div>
        {attachmentSettings && (
          <p className="muted small">Currently: {attachmentSettings.extension_list.join(', ')}</p>
        )}
        {attachMsg && <p className={attachMsg.ok ? 'success' : 'error'}>{attachMsg.text}</p>}
        <button type="submit">Save</button>
      </form>
    </div>
  )
}
