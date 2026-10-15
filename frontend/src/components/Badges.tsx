import { PRIORITY_LABELS, PROJECT_STATUS_LABELS, TASK_STATUS_LABELS } from '../lib/labels'
import type { Priority, ProjectStatus, TaskStatus } from '../types'

export function PriorityBadge({ priority, label }: { priority: Priority; label?: string }) {
  return <span className={`badge priority-${priority.toLowerCase()}`}>{label ?? PRIORITY_LABELS[priority]}</span>
}

export function StatusBadge({ status }: { status: TaskStatus }) {
  return <span className={`badge status status-${status.toLowerCase()}`}>{TASK_STATUS_LABELS[status]}</span>
}

export function ProjectStatusBadge({ status }: { status: ProjectStatus }) {
  return <span className={`badge project-${status.toLowerCase()}`}>{PROJECT_STATUS_LABELS[status]}</span>
}
