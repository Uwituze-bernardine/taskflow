import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  listNotifications, markAllNotificationsRead, markNotificationRead,
} from '../api/notifications'
import Pager from '../components/Pager'
import { getErrorMessage } from '../lib/errors'
import { formatDateTime } from '../lib/labels'
import type { Notification, NotificationCategory } from '../types'

const CATEGORY_LABELS: Record<NotificationCategory, string> = {
  assigned: 'Assigned to you',
  status_changed: 'Status changed',
  mentioned: 'Mentioned',
  due_soon: 'Due soon',
  overdue: 'Overdue',
  other: 'Other',
}

// FR-060: notification history.
export default function Notifications() {
  const [items, setItems] = useState<Notification[]>([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [category, setCategory] = useState<NotificationCategory | ''>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    listNotifications({ is_read: unreadOnly ? false : undefined, category: category || undefined, page })
      .then((d) => { setItems(d.results); setCount(d.count) })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [unreadOnly, category, page])

  useEffect(load, [load])

  async function handleClick(n: Notification) {
    if (n.is_read) return
    try {
      await markNotificationRead(n.id)
      setItems((rs) => rs.map((r) => (r.id === n.id ? { ...r, is_read: true } : r)))
    } catch {
      // Not read-marking the item isn't disruptive enough to interrupt the user; they can retry.
    }
  }

  async function handleMarkAll() {
    setError(null)
    try {
      await markAllNotificationsRead()
      load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Notifications</h1>
        <button className="btn-secondary" onClick={handleMarkAll}>Mark all as read</button>
      </div>

      <div className="filter-bar">
        <label className="checkbox-row">
          <input type="checkbox" checked={unreadOnly} onChange={(e) => { setUnreadOnly(e.target.checked); setPage(1) }} />
          Unread only
        </label>
        <select value={category} onChange={(e) => { setCategory(e.target.value as NotificationCategory | ''); setPage(1) }}>
          <option value="">All categories</option>
          {Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>

      {error && <p className="error">{error}</p>}
      {loading ? (
        <p>Loading…</p>
      ) : (
        <ul className="notification-list">
          {items.map((n) => (
            <li key={n.id} className={n.is_read ? '' : 'unread'} onClick={() => handleClick(n)}>
              <span className="badge">{CATEGORY_LABELS[n.category]}</span>
              {n.task ? <Link to={`/tasks/${n.task}`}>{n.message}</Link> : <span>{n.message}</span>}
              <span className="muted small">{formatDateTime(n.created_at)}</span>
            </li>
          ))}
          {items.length === 0 && <p className="muted">No notifications.</p>}
        </ul>
      )}
      <Pager page={page} count={count} onChange={setPage} />
    </div>
  )
}
