import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { listAttachments } from '../api/attachments'
import { getProject } from '../api/projects'
import {
  archiveTask, assignTask, changeTaskStatus, deleteTaskPermanently, getSubtasks,
  getTask, getTaskHistory, listComments, restoreTask, statusChoiceFromKey,
} from '../api/tasks'
import { RECURRENCE_LABELS } from '../lib/labels'
import { listUsers } from '../api/users'
import AttachmentPanel from '../components/AttachmentPanel'
import { PriorityBadge, StatusBadge } from '../components/Badges'
import CommentThread from '../components/CommentThread'
import DependencyPanel from '../components/DependencyPanel'
import StatusControl from '../components/StatusControl'
import TaskForm from '../components/TaskForm'
import { getErrorMessage } from '../lib/errors'
import { formatDate, formatDateTime, fullName } from '../lib/labels'
import type { Attachment, Comment, HistoryEntry, Task, UserSummary } from '../types'

// FR-022 edit, FR-023 archive/delete, FR-024 details, FR-025 history,
// FR-026/028 assign & reassign, FR-032..FR-042 status, subtasks, dependencies.
export default function TaskDetail() {
  const { id } = useParams()
  const taskId = Number(id)
  const navigate = useNavigate()
  const [task, setTask] = useState<Task | null>(null)
  const [subtasks, setSubtasks] = useState<Task[]>([])
  const [comments, setComments] = useState<Comment[]>([])
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [participants, setParticipants] = useState<UserSummary[]>([])
  const [assigneeChoice, setAssigneeChoice] = useState('')
  const [editing, setEditing] = useState(false)
  const [showSubtaskForm, setShowSubtaskForm] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loadFailed, setLoadFailed] = useState(false)
  const [nextOccurrenceNotice, setNextOccurrenceNotice] = useState<Task | null>(null)

  const loadHistory = useCallback(() => {
    getTaskHistory(taskId).then(setHistory).catch(() => {})
  }, [taskId])

  const loadSubtasks = useCallback(() => {
    getSubtasks(taskId).then(setSubtasks).catch(() => {})
  }, [taskId])

  const load = useCallback(() => {
    getTask(taskId)
      .then((t) => { setTask(t); setAssigneeChoice(t.assigned_to ? String(t.assigned_to) : '') })
      .catch((err) => { setError(getErrorMessage(err, 'Could not load this task.')); setLoadFailed(true) })
    loadSubtasks()
    listComments(taskId).then((d) => setComments(Array.isArray(d) ? d : d.results)).catch(() => {})
    listAttachments(taskId).then(setAttachments).catch(() => {})
    loadHistory()
  }, [taskId, loadHistory, loadSubtasks])

  useEffect(load, [load])

  // Who is on this task's team? Used both for the assignee dropdown and the
  // "you can mention" hint in the comment box (FR-018/026 and FR-045).
  const projectId = task?.project
  useEffect(() => {
    const team = projectId
      ? getProject(projectId).then((p) => [p.manager_detail, ...(p.members_detail ?? [])].filter((u): u is UserSummary => !!u))
      : listUsers()
    team.then(setParticipants).catch(() => {})
  }, [projectId])

  async function run(action: () => Promise<Task | void>, reload = true) {
    setError(null)
    try {
      const result = await action()
      if (result) setTask(result)
      if (reload) loadHistory()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleAssign() {
    await run(() => assignTask(taskId, assigneeChoice ? Number(assigneeChoice) : null))
  }

  async function handleStatusChange(key: string) {
    setError(null)
    try {
      const result = await changeTaskStatus(taskId, statusChoiceFromKey(key))
      setTask(result)
      loadHistory()
      setNextOccurrenceNotice(result.next_occurrence ?? null)  // FR-064
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleArchive() {
    if (!confirm('Archive this task? It is hidden from lists but can be restored.')) return
    await run(() => archiveTask(taskId))
  }

  async function handleDeleteForever() {
    if (!confirm('Permanently delete this task, with its comments and files? This cannot be undone.')) return
    try {
      await deleteTaskPermanently(taskId)
      navigate('/tasks')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  if (loadFailed) return <p className="error">{error}</p>
  if (!task) return <p>Loading…</p>

  const perms = task.permissions
  const assigneeChanged = assigneeChoice !== (task.assigned_to ? String(task.assigned_to) : '')
  const finished = task.status === 'COMPLETED' || task.status === 'CANCELLED'

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{task.title}</h1>
          <div className="row">
            <span className="muted">#{task.id}</span>
            <PriorityBadge priority={task.priority} label={task.priority_label} />
            <StatusBadge status={task.status} />
            {task.custom_status && <span className="badge">{task.status_label}</span>}
            {task.project && <Link to={`/projects/${task.project}`}>{task.project_name}</Link>}
            {task.parent_task && (
              <span className="muted">Subtask of <Link to={`/tasks/${task.parent_task}`}>{task.parent_title}</Link></span>
            )}
          </div>
        </div>
        <div className="actions">
          {perms.edit && !task.is_archived && (
            <button className="btn-secondary" onClick={() => setEditing((e) => !e)}>{editing ? 'Cancel edit' : 'Edit'}</button>
          )}
          {perms.archive && !task.is_archived && <button className="btn-secondary" onClick={handleArchive}>Archive</button>}
          {perms.archive && task.is_archived && <button onClick={() => run(() => restoreTask(taskId))}>Restore</button>}
          {perms.delete_permanently && task.is_archived && <button className="btn-danger" onClick={handleDeleteForever}>Delete permanently</button>}
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      {nextOccurrenceNotice && (
        <p className="notice">
          This task repeats {RECURRENCE_LABELS[nextOccurrenceNotice.recurrence].toLowerCase()}: the next
          occurrence, <Link to={`/tasks/${nextOccurrenceNotice.id}`}>due {formatDate(nextOccurrenceNotice.due_date)}</Link>, was created.
        </p>
      )}
      {task.is_archived && <p className="banner">This task is archived.</p>}
      {task.is_blocked_by_dependencies && (
        <p className="warning">
          Blocked: waiting on {task.blocked_by.map((b) => `"${b.title}" (${b.status_label})`).join(', ')}.
        </p>
      )}
      {!finished && !task.is_blocked_by_dependencies && task.completion_blockers.length > 0 && (
        <p className="banner">Not ready to complete: {task.completion_blockers.join(' ')}</p>
      )}

      {editing ? (
        <TaskForm
          task={task}
          onSaved={(t) => { setTask(t); setEditing(false); loadHistory() }}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <p className="description">{task.description || <span className="muted">No description.</span>}</p>
      )}

      <div className="meta-row">
        <div>
          <strong>Status</strong>
          {perms.change_status ? (
            <StatusControl status={task.status} customStatusId={task.custom_status} onChange={handleStatusChange} />
          ) : (
            <p>{task.status_label}</p>
          )}
        </div>
        <div><strong>Assigned to</strong><p>{fullName(task.assigned_to_detail)}</p></div>
        <div><strong>Created by</strong><p>{fullName(task.created_by_detail)}</p></div>
        <div><strong>Start date</strong><p>{formatDate(task.start_date)}</p></div>
        <div>
          <strong>Due date</strong>
          <p className={task.is_overdue ? 'overdue' : ''}>{formatDate(task.due_date)}{task.is_overdue && ' (overdue)'}</p>
        </div>
        <div><strong>Progress</strong><p>{task.progress}%{task.subtask_count > 0 && ` (${task.subtasks_done}/${task.subtask_count} subtasks)`}</p></div>
        {task.is_recurring && (
          <div>
            <strong>Repeats</strong>
            <p>
              {RECURRENCE_LABELS[task.recurrence]}
              {task.next_occurrence_due_date && !task.parent_task && `, next due ${formatDate(task.next_occurrence_due_date)}`}
            </p>
          </div>
        )}
      </div>
      {task.tags.length > 0 && (
        <div className="chips">{task.tags.map((t) => <span key={t} className="chip">{t}</span>)}</div>
      )}

      {perms.assign && (
        <div className="panel wide-panel">
          <h2>Assignment</h2>
          <div className="inline-form">
            <select value={assigneeChoice} onChange={(e) => setAssigneeChoice(e.target.value)}>
              <option value="">Unassigned</option>
              {participants.map((u) => <option key={u.id} value={u.id}>{fullName(u)}</option>)}
            </select>
            <button disabled={!assigneeChanged} onClick={handleAssign}>
              {task.assigned_to ? 'Reassign' : 'Assign'}
            </button>
          </div>
          <p className="muted small">The new assignee is notified.{task.project ? ' Only members of the project can be assigned.' : ''}</p>
        </div>
      )}

      {!task.parent_task && <DependencyPanel task={task} canEdit={!!perms.edit} onChanged={(t) => { setTask(t); loadHistory() }} />}

      {!task.parent_task && (
        <>
          <div className="page-header">
            <h2>Subtasks</h2>
            {perms.add_subtask && (
              <button className="btn-secondary" onClick={() => setShowSubtaskForm((s) => !s)}>
                {showSubtaskForm ? 'Cancel' : 'Add subtask'}
              </button>
            )}
          </div>
          {showSubtaskForm && (
            <TaskForm
              parentTask={task}
              onSaved={() => { setShowSubtaskForm(false); loadSubtasks(); load() }}
              onCancel={() => setShowSubtaskForm(false)}
            />
          )}
          {subtasks.length > 0 ? (
            <ul className="task-list">
              {subtasks.map((s) => (
                <li key={s.id}>
                  <div className="task-main"><Link to={`/tasks/${s.id}`}>{s.title}</Link></div>
                  <span className="muted">{fullName(s.assigned_to_detail)}</span>
                  <StatusBadge status={s.status} />
                </li>
              ))}
            </ul>
          ) : (
            !showSubtaskForm && <p className="muted">No subtasks.</p>
          )}
        </>
      )}

      <AttachmentPanel
        taskId={task.id}
        attachments={attachments}
        canUpload={!task.is_archived}
        onChanged={setAttachments}
      />

      <h2>Comments</h2>
      <CommentThread taskId={task.id} comments={comments} participants={participants} onChanged={setComments} />

      <h2>History</h2>
      <ul className="history">
        {history.map((h) => (
          <li key={h.id}>
            <div>
              <strong>{h.actor?.name ?? 'System'}</strong>{' '}
              {h.action === 'task.created' ? 'created this task' : 'changed this task'}
              <span className="muted"> · {formatDateTime(h.timestamp)}</span>
            </div>
            {h.changes.map((c) => (
              <div key={c.field} className="change">
                {c.label}: <span className="from">{c.from ?? '—'}</span> → <span className="to">{c.to ?? '—'}</span>
              </div>
            ))}
          </li>
        ))}
        {history.length === 0 && <p className="muted">No recorded changes.</p>}
      </ul>
    </div>
  )
}
