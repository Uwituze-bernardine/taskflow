import { FormEvent, useEffect, useMemo, useState } from 'react'
import { listAllProjects } from '../api/projects'
import { addSubtask, createTask, updateTask, TaskInput } from '../api/tasks'
import { listUsers } from '../api/users'
import { getErrorMessage } from '../lib/errors'
import PriorityControl from './PriorityControl'
import { RECURRENCE_LABELS, fullName } from '../lib/labels'
import type { Priority, Project, Recurrence, Task, UserSummary } from '../types'

interface Props {
  task?: Task // present = edit mode (FR-022)
  defaultProjectId?: number
  lockProject?: boolean
  /** FR-038: creating a subtask under `parentTask` - hides the project picker and dependencies. */
  parentTask?: Task
  onSaved: (task: Task) => void
  onCancel: () => void
}

// FR-015..FR-021: title, description, project, assignee, priority, dates (and tags).
export default function TaskForm({ task, defaultProjectId, lockProject, parentTask, onSaved, onCancel }: Props) {
  const isSubtask = !!parentTask
  const [projects, setProjects] = useState<Project[]>([])
  const [directory, setDirectory] = useState<UserSummary[]>([])
  const [title, setTitle] = useState(task?.title ?? '')
  const [description, setDescription] = useState(task?.description ?? '')
  const [projectId, setProjectId] = useState<string>(
    String(task?.project ?? parentTask?.project ?? defaultProjectId ?? '')
  )
  const [assigneeId, setAssigneeId] = useState<string>(task?.assigned_to ? String(task.assigned_to) : '')
  const [priority, setPriority] = useState<Priority>(task?.priority ?? 'MEDIUM')
  const [customPriorityId, setCustomPriorityId] = useState<number | null>(task?.custom_priority ?? null)
  const [startDate, setStartDate] = useState(task?.start_date ?? '')
  const [dueDate, setDueDate] = useState(task?.due_date ?? '')
  const [tags, setTags] = useState((task?.tags ?? []).join(', '))
  const [enforceDeps, setEnforceDeps] = useState(task?.enforce_dependencies ?? false)
  const [recurrence, setRecurrence] = useState<Recurrence>(task?.recurrence ?? 'NONE')
  const [recurrenceInterval, setRecurrenceInterval] = useState(task?.recurrence_interval ?? 1)
  const [recurrenceEnd, setRecurrenceEnd] = useState(task?.recurrence_end_date ?? '')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    // Only projects where this user may put tasks are offered.
    listAllProjects().then((all) => setProjects(all.filter((p) => p.permissions.create_tasks))).catch(() => {})
    listUsers().then(setDirectory).catch(() => {})
  }, [])

  const project = projects.find((p) => String(p.id) === projectId)

  // A project task can only go to that project's team; a standalone task to anyone.
  // (For a subtask, the backend enforces the same rule; the full directory is offered
  // here because the parent's project record - and so its member list - may not be
  // loaded for someone who can add subtasks without being a full project participant.)
  const assignees = useMemo<UserSummary[]>(() => {
    if (isSubtask || !projectId) return directory
    if (!project) return directory.filter((u) => String(u.id) === assigneeId)
    return [project.manager_detail, ...(project.members_detail ?? [])].filter((u): u is UserSummary => !!u)
  }, [isSubtask, projectId, project, directory, assigneeId])

  // Keep the assignee consistent when the project changes.
  useEffect(() => {
    if (isSubtask) return
    if (assigneeId && projects.length && !assignees.some((u) => String(u.id) === assigneeId)) setAssigneeId('')
  }, [isSubtask, assignees, assigneeId, projects.length])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    const payload: Partial<TaskInput> = {
      title,
      description,
      priority,
      custom_priority: customPriorityId,
      start_date: startDate || null,
      due_date: dueDate || null,
      tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
    }
    const newAssignee = assigneeId ? Number(assigneeId) : null
    // On edit, only send what changed so an unrelated edit is never blocked by,
    // say, an assignee who has since been deactivated.
    if (!task || newAssignee !== task.assigned_to) payload.assigned_to = newAssignee
    if (isSubtask) {
      // The project is forced from the parent server-side; no need to send it.
      payload.parent_task = parentTask!.id
    } else {
      const newProject = projectId ? Number(projectId) : null
      if (!task || newProject !== task.project) payload.project = newProject
      payload.enforce_dependencies = enforceDeps
      payload.recurrence = recurrence
      payload.recurrence_interval = recurrenceInterval
      payload.recurrence_end_date = recurrence === 'NONE' ? null : recurrenceEnd || null
    }
    try {
      onSaved(task ? await updateTask(task.id, payload) : isSubtask ? await addSubtask(parentTask!.id, payload) : await createTask(payload))
    } catch (err) {
      setError(getErrorMessage(err, task ? 'Could not save the task.' : 'Could not create the task.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="create-task-form" onSubmit={handleSubmit}>
      <label>
        Title
        <input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={250} />
      </label>
      <label>
        Description
        <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>

      <div className="form-row">
        {isSubtask ? (
          <label>
            Project
            <input value={parentTask!.project_name ?? 'No project'} disabled title="A subtask always belongs to its parent's project." />
          </label>
        ) : (
          <label>
            Project
            <select value={projectId} disabled={lockProject} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">No project</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
              {task?.project && !projects.some((p) => p.id === task.project) && (
                <option value={task.project}>{task.project_name}</option>
              )}
            </select>
          </label>
        )}
        <label>
          Assignee
          <select value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)}>
            <option value="">Unassigned</option>
            {assignees.map((u) => (
              <option key={u.id} value={u.id}>{fullName(u)}</option>
            ))}
          </select>
        </label>
        <label>
          Priority
          <PriorityControl
            priority={priority}
            customPriorityId={customPriorityId}
            onChange={(p, customId) => { setPriority(p); setCustomPriorityId(customId) }}
          />
        </label>
      </div>

      <div className="form-row">
        <label>
          Start date
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </label>
        <label>
          Due date
          <input type="date" value={dueDate} min={startDate || undefined} onChange={(e) => setDueDate(e.target.value)} />
        </label>
        <label>
          Tags (comma separated)
          <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="backend, urgent" />
        </label>
      </div>

      {!isSubtask && (
        <>
          <label className="checkbox-row">
            <input type="checkbox" checked={enforceDeps} onChange={(e) => setEnforceDeps(e.target.checked)} />
            Enforce dependencies: block this task from starting until its predecessors are completed
          </label>

          <div className="form-row">
            <label>
              Repeats
              <select value={recurrence} onChange={(e) => setRecurrence(e.target.value as Recurrence)}>
                {(Object.keys(RECURRENCE_LABELS) as Recurrence[]).map((r) => (
                  <option key={r} value={r}>{RECURRENCE_LABELS[r]}</option>
                ))}
              </select>
            </label>
            {recurrence !== 'NONE' && (
              <>
                <label>
                  Every
                  <input
                    type="number" min={1} value={recurrenceInterval}
                    onChange={(e) => setRecurrenceInterval(Math.max(1, Number(e.target.value)))}
                  />
                </label>
                <label>
                  Stop repeating after
                  <input type="date" value={recurrenceEnd} min={dueDate || undefined} onChange={(e) => setRecurrenceEnd(e.target.value)} />
                </label>
              </>
            )}
          </div>
          {recurrence !== 'NONE' && !dueDate && (
            <p className="muted small">Set a due date above - a recurring task needs one to know when the next one is due.</p>
          )}
        </>
      )}

      {error && <p className="error">{error}</p>}
      <div className="form-actions">
        <button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : task ? 'Save changes' : isSubtask ? 'Add subtask' : 'Create task'}
        </button>
        <button type="button" className="secondary" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}
