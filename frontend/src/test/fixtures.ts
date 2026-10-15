// Realistic fake API data, shaped exactly like the backend serializers in this project.
// Keeping it in one place means every test sees internally-consistent IDs/relations.
import type {
  Attachment, Comment, CustomPriority, CustomTaskStatus, DashboardData, HistoryEntry, Notification,
  Paginated, Project, Report, StatusHistoryEntry, Task, TaskTag, User, UserSummary, WorkflowOption,
} from '../types'

export const meAdmin: User = {
  id: 1, username: 'boss', email: 'boss@example.com', first_name: 'Bo', last_name: 'Ss',
  role: 'ADMIN', is_active_member: true,
}
export const mePM: User = {
  id: 2, username: 'pam', email: 'pam@example.com', first_name: 'Pam', last_name: 'Manager',
  role: 'PROJECT_MANAGER', is_active_member: true,
}
export const meMember: User = {
  id: 3, username: 'mo', email: 'mo@example.com', first_name: 'Mo', last_name: 'Member',
  role: 'TEAM_MEMBER', is_active_member: true,
}

export const userSummary = (u: User): UserSummary => ({
  id: u.id, username: u.username, first_name: u.first_name, last_name: u.last_name, role: u.role,
})

export const project1: Project = {
  id: 10, name: 'Apollo', description: 'Moon mission', manager: 2, manager_detail: userSummary(mePM),
  members: [3], members_detail: [userSummary(meMember)], status: 'ACTIVE',
  start_date: '2026-01-01', end_date: '2026-12-31', progress: 40, task_count: 5,
  permissions: { edit: true, manage_members: true, archive: true, close: true, reopen: false, create_tasks: true },
  created_by: 2, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
}

export function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 100, title: 'Design database', description: 'Schema for the new service', project: 10,
    project_name: 'Apollo', parent_task: null, parent_title: null,
    assigned_to: 3, assigned_to_detail: userSummary(meMember), created_by: 2, created_by_detail: userSummary(mePM),
    priority: 'HIGH', custom_priority: null, priority_label: 'High',
    status: 'IN_PROGRESS', custom_status: null, status_label: 'In Progress',
    recurrence: 'NONE', recurrence_interval: 1, recurrence_end_date: null, recurrence_of: null,
    is_recurring: false, next_occurrence_due_date: null,
    start_date: '2026-01-01', due_date: '2026-01-15', tags: ['backend', 'db'],
    depends_on: [], depends_on_detail: [], blocks_detail: [], enforce_dependencies: false,
    is_blocked_by_dependencies: false, blocked_by: [], completion_blockers: [],
    progress: 0, is_overdue: false, subtask_count: 0, subtasks_done: 0, is_archived: false,
    permissions: { edit: true, assign: true, archive: true, change_status: true, add_subtask: true, delete_permanently: false },
    created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-02T00:00:00Z',
    ...overrides,
  }
}

export function paginated<T>(results: T[]): Paginated<T> {
  return { count: results.length, next: null, previous: null, results }
}

export const comment1: Comment = {
  id: 1, task: 100, author: 2, author_detail: userSummary(mePM), body: 'Looks good so far',
  mentioned_users_detail: [], is_edited: false, is_deleted: false, can_edit: false, can_delete: true,
  created_at: '2026-01-02T10:00:00Z', edited_at: null,
}

export const attachment1: Attachment = {
  id: 1, task: 100, filename: 'schema.pdf', content_type: 'application/pdf',
  uploaded_by: 2, uploaded_by_detail: userSummary(mePM), uploaded_at: '2026-01-02T09:00:00Z',
  size_bytes: 102400, can_delete: true,
}

export const workflowOptions: WorkflowOption[] = [
  { key: 'TODO', label: 'To Do', category: 'TODO', custom_status: null, builtin: true },
  { key: 'IN_PROGRESS', label: 'In Progress', category: 'IN_PROGRESS', custom_status: null, builtin: true },
  { key: 'BLOCKED', label: 'Blocked', category: 'BLOCKED', custom_status: null, builtin: true },
  { key: 'UNDER_REVIEW', label: 'Under Review', category: 'UNDER_REVIEW', custom_status: null, builtin: true },
  { key: 'COMPLETED', label: 'Completed', category: 'COMPLETED', custom_status: null, builtin: true },
  { key: 'CANCELLED', label: 'Cancelled', category: 'CANCELLED', custom_status: null, builtin: true },
]

export const historyEntries: HistoryEntry[] = [
  {
    id: 1, timestamp: '2026-01-02T08:00:00Z', action: 'task.updated',
    actor: { id: 2, name: 'Pam Manager' },
    changes: [{ field: 'priority', label: 'Priority', from: 'Medium', to: 'High' }],
  },
  { id: 2, timestamp: '2026-01-01T00:00:00Z', action: 'task.created', actor: { id: 2, name: 'Pam Manager' }, changes: [] },
]

export const statusHistory: StatusHistoryEntry[] = [
  {
    id: 1, from_status: 'TODO', to_status: 'IN_PROGRESS', from_label: 'To Do', to_label: 'In Progress',
    changed_by: 3, changed_by_detail: userSummary(meMember), changed_at: '2026-01-02T08:00:00Z',
  },
]

export const notification1: Notification = {
  id: 1, recipient: 3, category: 'assigned', category_label: 'Task assigned',
  message: 'You were assigned to task "Design database".', task: 100, is_read: false,
  created_at: '2026-01-01T00:00:00Z',
}

export const customStatus1: CustomTaskStatus = {
  id: 1, name: 'QA Testing', category: 'UNDER_REVIEW', order: 1, is_active: true, task_count: 2,
}
export const customPriority1: CustomPriority = {
  id: 1, name: 'Showstopper', category: 'CRITICAL', order: 1, is_active: true, task_count: 1,
}
export const taskTag1: TaskTag = { id: 1, name: 'backend' }

export const dashboardData: DashboardData = {
  my_tasks: { total: 4, TODO: 1, IN_PROGRESS: 1, BLOCKED: 0, UNDER_REVIEW: 0, COMPLETED: 1, CANCELLED: 0, overdue: 1 },
  pending_tasks: [makeTask({ id: 101, title: 'Pending one' })],
  overdue_tasks: [makeTask({ id: 102, title: 'Overdue one', is_overdue: true, due_date: '2025-01-01' })],
  projects: [{ id: 10, name: 'Apollo', status: 'ACTIVE', progress: 40, task_count: 5 }],
  team_stats: {
    total: 6, overdue: 2, by_status: { TODO: 2, IN_PROGRESS: 2, BLOCKED: 0, UNDER_REVIEW: 0, COMPLETED: 2, CANCELLED: 0 },
    by_employee: [{ user: userSummary(meMember), total: 6, completed: 2, overdue: 2 }],
  },
}

export const reportData: Report = {
  start: '2026-01-01', end: '2026-01-31',
  tasks_created: 8, tasks_completed: 5, tasks_overdue: 2,
  overdue_tasks: [{ id: 102, title: 'Overdue one', project: 'Apollo', assignee: userSummary(meMember), due_date: '2025-01-01' }],
  avg_completion_days: 3.2,
  tasks_by_priority: { LOW: 1, MEDIUM: 3, HIGH: 3, CRITICAL: 1 },
  tasks_by_status: { TODO: 2, IN_PROGRESS: 2, BLOCKED: 0, UNDER_REVIEW: 1, COMPLETED: 5, CANCELLED: 0 },
  tasks_by_employee: [{ user: userSummary(meMember), total: 6, completed: 2, overdue: 2 }],
  projects: [{ id: 10, name: 'Apollo', status: 'ACTIVE', progress: 40, task_count: 5 }],
}
