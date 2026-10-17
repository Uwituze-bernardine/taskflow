import { useCallback, useEffect, useState } from 'react'
import { listAllProjects } from '../api/projects'
import { listTasks, myTasks, teamTasks, TaskFilters } from '../api/tasks'
import { listUsers } from '../api/users'
import Pager from '../components/Pager'
import TaskForm from '../components/TaskForm'
import TaskList from '../components/TaskList'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../lib/errors'
import { PRIORITIES, PRIORITY_LABELS, TASK_STATUSES, TASK_STATUS_LABELS, fullName } from '../lib/labels'
import { canCreateTask, isManager } from '../lib/roles'
import type { Priority, Project, Task, TaskStatus, UserSummary } from '../types'

type Tab = 'all' | 'mine' | 'team' | 'archived'

const TAB_LABELS: Record<Tab, string> = {
  all: 'All tasks',
  mine: 'Assigned to me', // FR-029
  team: 'My team', // FR-030
  archived: 'Archived',
}

export default function Tasks() {
  const { user } = useAuth()
  const manager = isManager(user?.role)
  const tabs: Tab[] = manager ? ['all', 'mine', 'team', 'archived'] : ['all', 'mine']

  const [tab, setTab] = useState<Tab>('all')
  const [tasks, setTasks] = useState<Task[]>([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [status, setStatus] = useState<TaskStatus | ''>('')
  const [priority, setPriority] = useState<Priority | ''>('')
  const [projectId, setProjectId] = useState('')
  const [assigneeId, setAssigneeId] = useState('')
  const [ordering, setOrdering] = useState('-created_at')
  const [projects, setProjects] = useState<Project[]>([])
  const [people, setPeople] = useState<UserSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    listAllProjects().then(setProjects).catch(() => {})
    listUsers().then(setPeople).catch(() => {})
  }, [])

  useEffect(() => {
    const t = setTimeout(() => { setDebouncedSearch(search); setPage(1) }, 300)
    return () => clearTimeout(t)
  }, [search])

  const load = useCallback(() => {
    setLoading(true)
    const filters: TaskFilters = {
      search: debouncedSearch || undefined,
      status: status || undefined,
      priority: priority || undefined,
      project: projectId ? Number(projectId) : undefined,
      assigned_to: tab !== 'mine' && assigneeId ? Number(assigneeId) : undefined,
      ordering,
      page,
    }
    const request =
      tab === 'mine' ? myTasks(filters)
      : tab === 'team' ? teamTasks(filters)
      : listTasks({ ...filters, archived: tab === 'archived' || undefined })
    request
      .then((data) => { setTasks(data.results); setCount(data.count); setError(null) })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [tab, debouncedSearch, status, priority, projectId, assigneeId, ordering, page])

  useEffect(load, [load])

  // Any filter change goes back to the first page.
  const onFilter = <T,>(setter: (v: T) => void) => (value: T) => { setter(value); setPage(1) }

  return (
    <div>
      <div className="page-header">
        <div><h1>Tasks</h1><p className="muted">Plan the work, focus on what’s next, and keep things moving.</p></div>
        {canCreateTask(user?.role) && (
          <button onClick={() => setShowForm((s) => !s)}>{showForm ? 'Cancel' : 'New task'}</button>
        )}
      </div>

      {showForm && (
        <TaskForm onSaved={() => { setShowForm(false); load() }} onCancel={() => setShowForm(false)} />
      )}

      <div className="tabs">
        {tabs.map((t) => (
          <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => { setTab(t); setPage(1) }}>
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      <div className="filter-bar wrap">
        <input placeholder="Search by title, description or ID…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select value={status} onChange={(e) => onFilter(setStatus)(e.target.value as TaskStatus | '')}>
          <option value="">All statuses</option>
          {TASK_STATUSES.map((s) => <option key={s} value={s}>{TASK_STATUS_LABELS[s]}</option>)}
        </select>
        <select value={priority} onChange={(e) => onFilter(setPriority)(e.target.value as Priority | '')}>
          <option value="">All priorities</option>
          {PRIORITIES.map((p) => <option key={p} value={p}>{PRIORITY_LABELS[p]}</option>)}
        </select>
        <select value={projectId} onChange={(e) => onFilter(setProjectId)(e.target.value)}>
          <option value="">All projects</option>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        {tab !== 'mine' && (
          <select value={assigneeId} onChange={(e) => onFilter(setAssigneeId)(e.target.value)}>
            <option value="">Anyone</option>
            {people.map((u) => <option key={u.id} value={u.id}>{fullName(u)}</option>)}
          </select>
        )}
        <select value={ordering} onChange={(e) => onFilter(setOrdering)(e.target.value)}>
          <option value="-created_at">Newest first</option>
          <option value="due_date">Due soonest</option>
          <option value="-priority">Highest priority</option>
          <option value="status">Status</option>
        </select>
      </div>

      {error && <p className="error">{error}</p>}
      {loading ? (
        <p>Loading…</p>
      ) : (
        <TaskList
          tasks={tasks}
          emptyText={
            tab === 'team' ? 'No tasks are assigned to the members of your projects.'
            : tab === 'mine' ? 'Nothing is assigned to you.'
            : 'No tasks match these filters.'
          }
        />
      )}
      <Pager page={page} count={count} onChange={setPage} />
    </div>
  )
}
