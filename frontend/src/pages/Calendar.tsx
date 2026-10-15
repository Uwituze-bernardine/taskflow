import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listAllProjects } from '../api/projects'
import { getCalendarTasks } from '../api/tasks'
import { listUsers } from '../api/users'
import { PriorityBadge } from '../components/Badges'
import { getErrorMessage } from '../lib/errors'
import { TASK_STATUSES, TASK_STATUS_LABELS, fullName } from '../lib/labels'
import type { Project, Task, TaskStatus, UserSummary } from '../types'

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function toISODate(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// FR-061 calendar view, FR-062 due dates on it, FR-065 filter by project/status/assignee.
// FR-063 (changing a task's date) is done from the task detail page's Edit form.
export default function Calendar() {
  const today = new Date()
  const [cursor, setCursor] = useState(new Date(today.getFullYear(), today.getMonth(), 1))
  const [tasks, setTasks] = useState<Task[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [people, setPeople] = useState<UserSummary[]>([])
  const [projectId, setProjectId] = useState('')
  const [status, setStatus] = useState<TaskStatus | ''>('')
  const [assigneeId, setAssigneeId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedDay, setSelectedDay] = useState<string | null>(null)

  useEffect(() => {
    listAllProjects().then(setProjects).catch(() => {})
    listUsers().then(setPeople).catch(() => {})
  }, [])

  const { start, end, gridStart, gridEnd } = useMemo(() => {
    const monthStart = new Date(cursor.getFullYear(), cursor.getMonth(), 1)
    const monthEnd = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0)
    const gridStart = new Date(monthStart)
    gridStart.setDate(gridStart.getDate() - gridStart.getDay())
    const gridEnd = new Date(monthEnd)
    gridEnd.setDate(gridEnd.getDate() + (6 - gridEnd.getDay()))
    return { start: monthStart, end: monthEnd, gridStart, gridEnd }
  }, [cursor])

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    getCalendarTasks(toISODate(start), toISODate(end), {
      project: projectId ? Number(projectId) : undefined,
      status: status || undefined,
      assigned_to: assigneeId ? Number(assigneeId) : undefined,
    })
      .then(setTasks)
      .catch((err) => setError(getErrorMessage(err, 'Could not load the calendar.')))
      .finally(() => setLoading(false))
  }, [start, end, projectId, status, assigneeId])

  useEffect(load, [load])

  const byDay = useMemo(() => {
    const map = new Map<string, Task[]>()
    for (const t of tasks) {
      if (!t.due_date) continue
      const key = t.due_date.slice(0, 10)
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(t)
    }
    return map
  }, [tasks])

  const days: Date[] = []
  for (let d = new Date(gridStart); d <= gridEnd; d.setDate(d.getDate() + 1)) days.push(new Date(d))

  const todayISO = toISODate(today)

  return (
    <div>
      <div className="page-header">
        <h1>Calendar</h1>
        <div className="actions">
          <button className="btn-secondary" onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}>‹ Prev</button>
          <span className="month-label">{cursor.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</span>
          <button className="btn-secondary" onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}>Next ›</button>
          <button className="btn-secondary" onClick={() => setCursor(new Date(today.getFullYear(), today.getMonth(), 1))}>Today</button>
        </div>
      </div>

      <div className="filter-bar">
        <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
          <option value="">All projects</option>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value as TaskStatus | '')}>
          <option value="">All statuses</option>
          {TASK_STATUSES.map((s) => <option key={s} value={s}>{TASK_STATUS_LABELS[s]}</option>)}
        </select>
        <select value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)}>
          <option value="">Anyone</option>
          {people.map((u) => <option key={u.id} value={u.id}>{fullName(u)}</option>)}
        </select>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Loading…</p>}

      <div className="calendar-grid">
        {WEEKDAYS.map((w) => <div key={w} className="calendar-weekday">{w}</div>)}
        {days.map((d) => {
          const iso = toISODate(d)
          const inMonth = d.getMonth() === cursor.getMonth()
          const dayTasks = byDay.get(iso) ?? []
          return (
            <div
              key={iso}
              className={`calendar-day ${inMonth ? '' : 'outside'} ${iso === todayISO ? 'today' : ''} ${selectedDay === iso ? 'selected' : ''}`}
              onClick={() => setSelectedDay(iso === selectedDay ? null : iso)}
            >
              <div className="calendar-day-number">{d.getDate()}</div>
              <div className="calendar-day-tasks">
                {dayTasks.slice(0, 3).map((t) => (
                  <Link key={t.id} to={`/tasks/${t.id}`} className={`calendar-chip priority-${t.priority.toLowerCase()}`} onClick={(e) => e.stopPropagation()}>
                    {t.title}
                  </Link>
                ))}
                {dayTasks.length > 3 && <span className="muted small">+{dayTasks.length - 3} more</span>}
              </div>
            </div>
          )
        })}
      </div>

      {selectedDay && (
        <div className="panel wide-panel">
          <h2>{new Date(selectedDay + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}</h2>
          {(byDay.get(selectedDay) ?? []).length === 0 ? (
            <p className="muted">Nothing due this day.</p>
          ) : (
            <ul className="task-list">
              {(byDay.get(selectedDay) ?? []).map((t) => (
                <li key={t.id}>
                  <div className="task-main"><Link to={`/tasks/${t.id}`}>{t.title}</Link></div>
                  <PriorityBadge priority={t.priority} label={t.priority_label} />
                  <span className="muted">{fullName(t.assigned_to_detail)}</span>
                  {t.project_name && <span className="muted">{t.project_name}</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
