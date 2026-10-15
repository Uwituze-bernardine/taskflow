import type { Priority, ProjectStatus, Recurrence, TaskStatus, UserSummary } from '../types'

export const RECURRENCE_LABELS: Record<Recurrence, string> = {
  NONE: 'Does not repeat',
  DAILY: 'Daily',
  WEEKLY: 'Weekly',
  MONTHLY: 'Monthly',
  YEARLY: 'Yearly',
}

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  TODO: 'To Do',
  IN_PROGRESS: 'In Progress',
  BLOCKED: 'Blocked',
  UNDER_REVIEW: 'Under Review',
  COMPLETED: 'Completed',
  CANCELLED: 'Cancelled',
}
export const TASK_STATUSES = Object.keys(TASK_STATUS_LABELS) as TaskStatus[]

export const PRIORITY_LABELS: Record<Priority, string> = {
  LOW: 'Low',
  MEDIUM: 'Medium',
  HIGH: 'High',
  CRITICAL: 'Critical',
}
export const PRIORITIES = Object.keys(PRIORITY_LABELS) as Priority[]

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
  PLANNED: 'Planned',
  ACTIVE: 'Active',
  ON_HOLD: 'On hold',
  CLOSED: 'Closed',
  ARCHIVED: 'Archived',
}

export function fullName(u?: Pick<UserSummary, 'first_name' | 'last_name' | 'username'> | null): string {
  if (!u) return 'Unassigned'
  return `${u.first_name} ${u.last_name}`.trim() || u.username
}

export function formatDate(iso?: string | null): string {
  if (!iso) return '—'
  // Dates arrive as YYYY-MM-DD; build them in local time so they never shift by a day.
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB']
  let value = bytes / 1024
  let i = 0
  while (value >= 1024 && i < units.length - 1) { value /= 1024; i++ }
  return `${value.toFixed(value < 10 ? 1 : 0)} ${units[i]}`
}
