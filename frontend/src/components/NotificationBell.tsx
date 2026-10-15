import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { getUnreadCount, listNotifications, markNotificationRead } from '../api/notifications'
import { formatDateTime } from '../lib/labels'
import type { Notification } from '../types'

// FR-060: a quick glance at recent notifications, from anywhere in the app.
export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [count, setCount] = useState(0)
  const [recent, setRecent] = useState<Notification[]>([])
  const ref = useRef<HTMLDivElement>(null)

  function refreshCount() {
    getUnreadCount().then(setCount).catch(() => {})
  }

  useEffect(() => {
    refreshCount()
    const interval = setInterval(refreshCount, 60_000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  function toggle() {
    if (!open) listNotifications({ page: 1 }).then((d) => setRecent(d.results.slice(0, 8))).catch(() => {})
    setOpen((o) => !o)
  }

  async function handleClick(n: Notification) {
    if (!n.is_read) {
      await markNotificationRead(n.id)
      setRecent((rs) => rs.map((r) => (r.id === n.id ? { ...r, is_read: true } : r)))
      refreshCount()
    }
  }

  return (
    <div className="notification-bell" ref={ref}>
      <button className="bell-button" onClick={toggle}>
        Notifications{count > 0 && <span className="bell-badge">{count > 9 ? '9+' : count}</span>}
      </button>
      {open && (
        <div className="bell-dropdown">
          {recent.length === 0 ? (
            <p className="muted">No notifications yet.</p>
          ) : (
            <ul className="bell-list">
              {recent.map((n) => (
                <li key={n.id} className={n.is_read ? '' : 'unread'}>
                  {n.task ? (
                    <Link to={`/tasks/${n.task}`} onClick={() => handleClick(n)}>{n.message}</Link>
                  ) : (
                    <span onClick={() => handleClick(n)}>{n.message}</span>
                  )}
                  <span className="muted small">{formatDateTime(n.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
          <Link to="/notifications" className="bell-footer" onClick={() => setOpen(false)}>See all notifications</Link>
        </div>
      )}
    </div>
  )
}
