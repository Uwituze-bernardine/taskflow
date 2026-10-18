import { useCallback, useEffect, useState } from 'react'
import { listAllProjects } from '../api/projects'
import {
  createSavedTaskFilter, deleteSavedTaskFilter, listSavedTaskFilters, listTasks, myTasks,
  SavedTaskFilter, TaskFilters, teamTasks,
} from '../api/tasks'
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
  const [tag, setTag] = useState('')
  const [createdAfter, setCreatedAfter] = useState('')
  const [createdBefore, setCreatedBefore] = useState('')
  const [dueAfter, setDueAfter] = useState('')
  const [dueBefore, setDueBefore] = useState('')
  const [ordering, setOrdering] = useState('-created_at')
  const [savedFilters, setSavedFilters] = useState<SavedTaskFilter[]>([])
  const [savedFilterId, setSavedFilterId] = useState('')
  const [savedFilterName, setSavedFilterName] = useState('')
  const [projects, setProjects] = useState<Project[]>([])
  const [people, setPeople] = useState<UserSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    listAllProjects().then(setProjects).catch(() => {})
    listUsers().then(setPeople).catch(() => {})
    listSavedTaskFilters().then(setSavedFilters).catch(() => {})
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
      tag: tag.trim() || undefined,
      created_after: createdAfter || undefined,
      created_before: createdBefore || undefined,
      due_after: dueAfter || undefined,
      due_before: dueBefore || undefined,
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
  }, [tab, debouncedSearch, status, priority, projectId, assigneeId, tag, createdAfter, createdBefore, dueAfter, dueBefore, ordering, page])

  useEffect(load, [load])

  // Any filter change goes back to the first page.
  const onFilter = <T,>(setter: (v: T) => void) => (value: T) => { setter(value); setPage(1) }

  function activeFilterValues(): SavedTaskFilter['filters'] {
    return {
      ...(status ? { status } : {}),
      ...(priority ? { priority } : {}),
      ...(projectId ? { project: Number(projectId) } : {}),
      ...(tab !== 'mine' && assigneeId ? { assigned_to: Number(assigneeId) } : {}),
      ...(tag.trim() ? { tag: tag.trim() } : {}),
      ...(createdAfter ? { created_after: createdAfter } : {}),
      ...(createdBefore ? { created_before: createdBefore } : {}),
      ...(dueAfter ? { due_after: dueAfter } : {}),
      ...(dueBefore ? { due_before: dueBefore } : {}),
    }
  }

  function applySavedFilter(filter: SavedTaskFilter | undefined) {
    if (!filter) return
    const values = filter.filters
    setStatus(values.status ?? '')
    setPriority(values.priority ?? '')
    setProjectId(values.project === undefined ? '' : String(values.project))
    setAssigneeId(values.assigned_to === undefined ? '' : String(values.assigned_to))
    setTag(values.tag ?? '')
    setCreatedAfter(values.created_after ?? '')
    setCreatedBefore(values.created_before ?? '')
    setDueAfter(values.due_after ?? '')
    setDueBefore(values.due_before ?? '')
    setPage(1)
  }

  async function saveCurrentFilter() {
    const name = savedFilterName.trim()
    if (!name) return
    try {
      const saved = await createSavedTaskFilter(name, activeFilterValues())
      setSavedFilters((current) => [...current.filter((item) => item.id !== saved.id), saved])
      setSavedFilterId(String(saved.id))
      setSavedFilterName('')
      setError(null)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function removeSavedFilter() {
    const id = Number(savedFilterId)
    if (!id) return
    try {
      await deleteSavedTaskFilter(id)
      setSavedFilters((current) => current.filter((item) => item.id !== id))
      setSavedFilterId('')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

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
        <select
          aria-label="Saved filters"
          value={savedFilterId}
          onChange={(e) => {
            const value = e.target.value
            setSavedFilterId(value)
            applySavedFilter(savedFilters.find((filter) => String(filter.id) === value))
          }}
        >
          <option value="">Saved filters</option>
          {savedFilters.map((filter) => <option key={filter.id} value={filter.id}>{filter.name}</option>)}
        </select>
        <input
          aria-label="Name this filter"
          placeholder="Name this filter"
          value={savedFilterName}
          onChange={(e) => setSavedFilterName(e.target.value)}
        />
        <button type="button" disabled={!savedFilterName.trim()} onClick={saveCurrentFilter}>Save filter</button>
        {savedFilterId && <button type="button" className="btn-secondary" onClick={removeSavedFilter}>Delete saved filter</button>}
        <input placeholder="Search by title, description or ID…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <input aria-label="Filter by tag" placeholder="Tag" value={tag} onChange={(e) => onFilter(setTag)(e.target.value)} />
        <input aria-label="Created on or after" type="date" value={createdAfter} onChange={(e) => onFilter(setCreatedAfter)(e.target.value)} />
        <input aria-label="Created on or before" type="date" value={createdBefore} onChange={(e) => onFilter(setCreatedBefore)(e.target.value)} />
        <input aria-label="Due on or after" type="date" value={dueAfter} onChange={(e) => onFilter(setDueAfter)(e.target.value)} />
        <input aria-label="Due on or before" type="date" value={dueBefore} onChange={(e) => onFilter(setDueBefore)(e.target.value)} />
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
