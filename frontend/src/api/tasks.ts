import { client } from './client'
import type {
  Comment, HistoryEntry, Paginated, Priority, Recurrence, StatusHistoryEntry, Task, TaskRef,
  TaskStatus, WorkflowOption,
} from '../types'

export interface TaskFilters {
  project?: number
  status?: TaskStatus
  priority?: Priority
  assigned_to?: number
  search?: string
  ordering?: string
  archived?: boolean
  page?: number
}

export interface TaskInput {
  title: string
  description: string
  project: number | null
  parent_task?: number
  assigned_to: number | null
  priority: Priority
  custom_priority?: number | null
  start_date: string | null
  due_date: string | null
  tags: string[]
  enforce_dependencies?: boolean
  recurrence?: Recurrence
  recurrence_interval?: number
  recurrence_end_date?: string | null
}

/** One of `status` (a predefined value) or `custom_status` (an id), matching a WorkflowOption's `key`. */
export type StatusChoice = { status: TaskStatus } | { custom_status: number }

export function statusChoiceFromKey(key: string): StatusChoice {
  return key.startsWith('custom:') ? { custom_status: Number(key.slice(7)) } : { status: key as TaskStatus }
}

export async function listTasks(filters: TaskFilters = {}): Promise<Paginated<Task>> {
  const { data } = await client.get('/tasks/', { params: filters })
  return data
}

// FR-061/062/065: tasks with a due date in [start, end], filterable like the task list.
export async function getCalendarTasks(
  start: string, end: string, filters: Omit<TaskFilters, 'page' | 'search' | 'ordering' | 'archived'> = {}
): Promise<Task[]> {
  const { data } = await client.get('/tasks/calendar/', { params: { start, end, ...filters } })
  return data
}

/** FR-029: tasks assigned to me. */
export async function myTasks(filters: TaskFilters = {}): Promise<Paginated<Task>> {
  const { data } = await client.get('/tasks/mine/', { params: filters })
  return data
}

/** FR-030: tasks assigned to the members of my teams (managers only). */
export async function teamTasks(filters: TaskFilters = {}): Promise<Paginated<Task>> {
  const { data } = await client.get('/tasks/team/', { params: filters })
  return data
}

export async function getTask(id: number): Promise<Task> {
  const { data } = await client.get(`/tasks/${id}/`)
  return data
}

export async function createTask(payload: Partial<TaskInput>): Promise<Task> {
  const { data } = await client.post('/tasks/', payload)
  return data
}

export async function updateTask(id: number, payload: Partial<TaskInput>): Promise<Task> {
  const { data } = await client.patch(`/tasks/${id}/`, payload)
  return data
}

export async function archiveTask(id: number): Promise<Task> {
  const { data } = await client.post(`/tasks/${id}/archive/`)
  return data
}

export async function restoreTask(id: number): Promise<Task> {
  const { data } = await client.post(`/tasks/${id}/restore/`)
  return data
}

/** Administrators only. */
export async function deleteTaskPermanently(id: number): Promise<void> {
  await client.delete(`/tasks/${id}/`, { params: { permanent: true } })
}

/** Assign or reassign; pass null to unassign. */
export async function assignTask(id: number, userId: number | null): Promise<Task> {
  const { data } = await client.post(`/tasks/${id}/assign/`, { user_id: userId })
  return data
}

export interface StatusChangeResult extends Task {
  /** FR-064: present when completing this task started the next occurrence of a recurring series. */
  next_occurrence?: Task
}

// FR-032/033/035: move a task to a predefined or an administrator-defined status.
export async function changeTaskStatus(id: number, choice: StatusChoice): Promise<StatusChangeResult> {
  const { data } = await client.post(`/tasks/${id}/status/`, choice)
  return data
}

/** FR-033/FR-035: every status a task can be moved to, in workflow order. */
export async function getWorkflowOptions(): Promise<WorkflowOption[]> {
  const { data } = await client.get('/tasks/workflow/')
  return data
}

/** FR-034: the status-change log for one task (who, when, from -> to). */
export async function getStatusHistory(id: number): Promise<StatusHistoryEntry[]> {
  const { data } = await client.get(`/tasks/${id}/status-history/`)
  return data
}

export async function getTaskHistory(id: number): Promise<HistoryEntry[]> {
  const { data } = await client.get(`/tasks/${id}/history/`)
  return data
}

// FR-038/039/040: subtasks -----------------------------------------------

export async function getSubtasks(id: number): Promise<Task[]> {
  const { data } = await client.get(`/tasks/${id}/subtasks/`)
  return data
}

export async function addSubtask(parentId: number, payload: Partial<TaskInput>): Promise<Task> {
  const { data } = await client.post(`/tasks/${parentId}/subtasks/`, payload)
  return data
}

// FR-041/042: dependencies -------------------------------------------------

export async function getDependencyCandidates(id: number, search = ''): Promise<TaskRef[]> {
  const { data } = await client.get(`/tasks/${id}/dependency-candidates/`, { params: { search } })
  return data
}

export async function addDependency(id: number, predecessorId: number): Promise<Task> {
  const { data } = await client.post(`/tasks/${id}/dependencies/`, { predecessor: predecessorId })
  return data
}

export async function removeDependency(id: number, predecessorId: number): Promise<Task> {
  const { data } = await client.delete(`/tasks/${id}/dependencies/${predecessorId}/`)
  return data
}

// FR-043/044: comments, oldest first (the API already orders them). -------

export async function listComments(taskId: number): Promise<Comment[] | Paginated<Comment>> {
  const { data } = await client.get('/comments/', { params: { task: taskId } })
  return data
}

export async function addComment(taskId: number, body: string): Promise<Comment> {
  const { data } = await client.post('/comments/', { task: taskId, body })
  return data
}

// FR-048: edit or (soft-)delete a comment.
export async function editComment(id: number, body: string): Promise<Comment> {
  const { data } = await client.patch(`/comments/${id}/`, { body })
  return data
}

export async function deleteComment(id: number): Promise<void> {
  await client.delete(`/comments/${id}/`)
}
