import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  addProjectMember, archiveProject, closeProject, getProject, removeProjectMember, reopenProject,
} from '../api/projects'
import { listTasks } from '../api/tasks'
import { listUsers } from '../api/users'
import { ProjectStatusBadge } from '../components/Badges'
import ProjectForm from '../components/ProjectForm'
import TaskForm from '../components/TaskForm'
import TaskList from '../components/TaskList'
import { getErrorMessage } from '../lib/errors'
import { TASK_STATUS_LABELS, formatDate, fullName } from '../lib/labels'
import type { Project, Task, TaskStatus, UserSummary } from '../types'

// FR-009 edit, FR-010 archive/close, FR-011 members, FR-013 progress, FR-014 dates.
export default function ProjectDetail() {
  const { id } = useParams()
  const projectId = Number(id)
  const [project, setProject] = useState<Project | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [taskCount, setTaskCount] = useState(0)
  const [directory, setDirectory] = useState<UserSummary[]>([])
  const [editing, setEditing] = useState(false)
  const [showTaskForm, setShowTaskForm] = useState(false)
  const [newMember, setNewMember] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loadFailed, setLoadFailed] = useState(false)

  const load = useCallback(() => {
    Promise.all([getProject(projectId), listTasks({ project: projectId, ordering: 'due_date' })])
      .then(([p, t]) => { setProject(p); setTasks(t.results); setTaskCount(t.count) })
      .catch((err) => { setError(getErrorMessage(err, 'Could not load this project.')); setLoadFailed(true) })
  }, [projectId])

  useEffect(load, [load])

  const canManageMembers = project?.permissions.manage_members
  useEffect(() => {
    if (canManageMembers) listUsers().then(setDirectory).catch(() => {})
  }, [canManageMembers])

  const candidates = useMemo(() => {
    if (!project) return []
    const inTeam = new Set([project.manager, ...project.members])
    return directory.filter((u) => !inTeam.has(u.id))
  }, [project, directory])

  async function run(action: () => Promise<Project>) {
    setError(null)
    try {
      setProject(await action())
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  if (loadFailed) return <p className="error">{error}</p>
  if (!project) return <p>Loading…</p>

  const perms = project.permissions
  const counts = project.status_counts
  const openTasks = counts ? Object.entries(counts).filter(([s]) => s !== 'COMPLETED' && s !== 'CANCELLED').reduce((n, [, c]) => n + c, 0) : 0

  async function handleClose() {
    const warning = openTasks ? `\n\n${openTasks} task(s) are not finished yet.` : ''
    if (!confirm(`Close "${project!.name}"? Its tasks become read-only until the project is reopened.${warning}`)) return
    await run(() => closeProject(projectId))
    load()
  }

  async function handleArchive() {
    if (!confirm(`Archive "${project!.name}"? It will be hidden from the project list.`)) return
    await run(() => archiveProject(projectId))
    load()
  }

  async function handleAdd() {
    if (!newMember) return
    await run(() => addProjectMember(projectId, Number(newMember)))
    setNewMember('')
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{project.name}</h1>
          <div className="row"><ProjectStatusBadge status={project.status} /></div>
        </div>
        <div className="actions">
          {perms.edit && <button className="btn-secondary" onClick={() => setEditing((e) => !e)}>{editing ? 'Cancel edit' : 'Edit'}</button>}
          {perms.close && <button className="btn-secondary" onClick={handleClose}>Close project</button>}
          {perms.archive && <button className="btn-secondary" onClick={handleArchive}>Archive</button>}
          {perms.reopen && <button onClick={() => run(() => reopenProject(projectId)).then(load)}>Reopen</button>}
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      {(project.status === 'CLOSED' || project.status === 'ARCHIVED') && (
        <p className="banner">This project is {project.status.toLowerCase()}: its details, members and tasks are read-only until it is reopened.</p>
      )}

      {editing ? (
        <ProjectForm
          project={project}
          onSaved={(p) => { setProject((prev) => (prev ? { ...prev, ...p } : p)); setEditing(false) }}
          onCancel={() => setEditing(false)}
        />
      ) : (
        project.description && <p>{project.description}</p>
      )}

      <div className="panel wide-panel">
        <div className="progress-head">
          <strong>{project.progress}% complete</strong>
          <span className="muted">{project.task_count} counted task{project.task_count === 1 ? '' : 's'}</span>
        </div>
        <div className="progress-bar large">
          <div className="progress-fill" style={{ width: `${project.progress}%` }} />
        </div>
        {counts && (
          <div className="chips">
            {(Object.keys(TASK_STATUS_LABELS) as TaskStatus[]).filter((s) => counts[s] > 0).map((s) => (
              <span key={s} className="chip">{TASK_STATUS_LABELS[s]}: {counts[s]}</span>
            ))}
            {!!project.overdue_count && <span className="chip chip-warning">Overdue: {project.overdue_count}</span>}
          </div>
        )}
      </div>

      <div className="meta-row">
        <div><strong>Manager</strong><p>{fullName(project.manager_detail)}</p></div>
        <div><strong>Start date</strong><p>{formatDate(project.start_date)}</p></div>
        <div><strong>Expected completion</strong><p>{formatDate(project.end_date)}</p></div>
      </div>

      <h2>Team</h2>
      <ul className="team-list">
        <li>
          <span>{fullName(project.manager_detail)}</span>
          <span className="badge">Manager</span>
        </li>
        {project.members_detail?.map((m) => (
          <li key={m.id}>
            <span>{fullName(m)}</span>
            <span className="muted">{m.role.replace('_', ' ').toLowerCase()}</span>
            {perms.manage_members && (
              <button className="btn-secondary" onClick={() => run(() => removeProjectMember(projectId, m.id))}>Remove</button>
            )}
          </li>
        ))}
      </ul>
      {perms.manage_members && (
        <div className="inline-form">
          <select value={newMember} onChange={(e) => setNewMember(e.target.value)}>
            <option value="">Add a member…</option>
            {candidates.map((u) => (
              <option key={u.id} value={u.id}>{fullName(u)}</option>
            ))}
          </select>
          <button disabled={!newMember} onClick={handleAdd}>Add</button>
        </div>
      )}

      <div className="page-header">
        <h2>Tasks</h2>
        {perms.create_tasks && (
          <button onClick={() => setShowTaskForm((s) => !s)}>{showTaskForm ? 'Cancel' : 'New task'}</button>
        )}
      </div>
      {showTaskForm && (
        <TaskForm
          defaultProjectId={projectId}
          lockProject
          onSaved={() => { setShowTaskForm(false); load() }}
          onCancel={() => setShowTaskForm(false)}
        />
      )}
      <TaskList tasks={tasks} showProject={false} emptyText="No tasks in this project yet." />
      {taskCount > tasks.length && <p className="muted">Showing {tasks.length} of {taskCount} tasks. Use the Tasks page to filter the rest.</p>}
    </div>
  )
}
