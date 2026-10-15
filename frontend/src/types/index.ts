export type Role = 'ADMIN' | 'PROJECT_MANAGER' | 'TEAM_LEADER' | 'TEAM_MEMBER'

export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  role: Role
  job_title?: string
  phone?: string
  is_active_member: boolean
}

/** What the API shows about *other* people: no email, phone or account status. */
export type UserSummary = Pick<User, 'id' | 'username' | 'first_name' | 'last_name' | 'role'>

export type ProjectStatus = 'PLANNED' | 'ACTIVE' | 'ON_HOLD' | 'ARCHIVED' | 'CLOSED'

export type Priority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export type TaskStatus =
  | 'TODO'
  | 'IN_PROGRESS'
  | 'BLOCKED'
  | 'UNDER_REVIEW'
  | 'COMPLETED'
  | 'CANCELLED'

/** Computed by the server for the current user, so the UI never has to guess. */
export interface ProjectPermissions {
  edit: boolean
  manage_members: boolean
  archive: boolean
  close: boolean
  reopen: boolean
  create_tasks: boolean
}

export interface Project {
  id: number
  name: string
  description: string
  manager: number
  manager_detail?: UserSummary
  members: number[]
  members_detail?: UserSummary[]
  status: ProjectStatus
  start_date: string | null
  end_date: string | null
  progress: number
  task_count: number
  permissions: ProjectPermissions
  /** Only on the single-project response. */
  status_counts?: Record<TaskStatus, number>
  overdue_count?: number
  created_by: number
  created_at: string
  updated_at: string
}

export interface TaskPermissions {
  edit: boolean
  assign: boolean
  archive: boolean
  change_status: boolean
  add_subtask: boolean
  delete_permanently: boolean
}

export interface TaskRef {
  id: number
  title: string
  status: TaskStatus
  status_label: string
}

/** One entry in the FR-033/FR-035 workflow: a predefined status or an admin-defined one. */
export interface WorkflowOption {
  key: string // 'TODO' or 'custom:<id>' - pass straight to changeTaskStatus
  label: string
  category: TaskStatus
  custom_status: number | null
  builtin: boolean
}

export interface CustomTaskStatus {
  id: number
  name: string
  category: TaskStatus
  order: number
  is_active: boolean
  task_count: number
}

export interface CustomPriority {
  id: number
  name: string
  category: Priority
  order: number
  is_active: boolean
  task_count: number
}

export interface TaskTag {
  id: number
  name: string
}

export interface Task {
  id: number
  title: string
  description: string
  project: number | null
  project_name: string | null
  parent_task: number | null
  assigned_to: number | null
  assigned_to_detail?: UserSummary | null
  created_by: number
  created_by_detail?: UserSummary
  priority: Priority
  custom_priority: number | null
  priority_label: string
  status: TaskStatus
  start_date: string | null
  due_date: string | null
  custom_status: number | null
  status_label: string
  recurrence: Recurrence
  recurrence_interval: number
  recurrence_end_date: string | null
  recurrence_of: number | null
  is_recurring: boolean
  next_occurrence_due_date: string | null
  tags: string[]
  depends_on: number[]
  depends_on_detail: TaskRef[]
  blocks_detail: TaskRef[]
  enforce_dependencies: boolean
  is_blocked_by_dependencies: boolean
  blocked_by: TaskRef[]
  completion_blockers: string[] // FR-036: why this task can't be completed right now
  progress: number
  is_overdue: boolean
  subtask_count: number
  subtasks_done: number
  parent_title: string | null
  is_archived: boolean
  permissions: TaskPermissions
  created_at: string
  updated_at: string
}

export type Recurrence = 'NONE' | 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'YEARLY'

export interface HistoryChange {
  field: string
  label: string
  from: string | null
  to: string | null
}

export interface HistoryEntry {
  id: number
  timestamp: string
  action: string
  actor: { id: number; name: string } | null
  changes: HistoryChange[]
}

export interface StatusHistoryEntry {
  id: number
  from_status: TaskStatus
  to_status: TaskStatus
  from_label: string
  to_label: string
  changed_by: number | null
  changed_by_detail?: UserSummary
  changed_at: string
}

export interface Comment {
  id: number
  task: number
  author: number
  author_detail?: UserSummary
  body: string
  mentioned_users_detail: UserSummary[]
  is_edited: boolean
  is_deleted: boolean
  can_edit: boolean
  can_delete: boolean
  created_at: string
  edited_at: string | null
}

export interface Attachment {
  id: number
  task: number
  filename: string
  content_type: string
  uploaded_by: number | null
  uploaded_by_detail?: UserSummary
  uploaded_at: string
  size_bytes: number
  can_delete: boolean
}

export interface AttachmentSettings {
  allowed_extensions: string
  max_size_mb: number
  extension_list: string[]
}

export type NotificationCategory = 'assigned' | 'status_changed' | 'mentioned' | 'due_soon' | 'overdue' | 'other'

export interface Notification {
  id: number
  recipient: number
  category: NotificationCategory
  category_label: string
  message: string
  task: number | null
  is_read: boolean
  created_at: string
}

/** FR-059: one boolean per category, keyed the same as NotificationCategory (minus 'other'). */
export type NotificationPreferences = Record<Exclude<NotificationCategory, 'other'>, boolean>

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ---- dashboard (FR-071..077) ----------------------------------------------

export interface MyTaskCounts extends Record<TaskStatus, number> {
  total: number
  overdue: number
}

export interface EmployeeWorkload {
  user: UserSummary
  total: number
  completed: number
  overdue: number
}

export interface TeamStats {
  total: number
  by_status: Record<TaskStatus, number>
  overdue: number
  by_employee: EmployeeWorkload[]
}

export interface ProjectProgressEntry {
  id: number
  name: string
  status: ProjectStatus
  progress: number
  task_count: number
}

export interface DashboardData {
  my_tasks: MyTaskCounts
  pending_tasks: Task[]
  overdue_tasks: Task[]
  projects: ProjectProgressEntry[]
  team_stats: TeamStats | null
}

// ---- reports (FR-078..084) -------------------------------------------------

export interface OverdueReportEntry {
  id: number
  title: string
  project: string | null
  assignee: UserSummary | null
  due_date: string
}

export interface Report {
  start: string
  end: string
  tasks_created: number
  tasks_completed: number
  tasks_overdue: number
  overdue_tasks: OverdueReportEntry[]
  avg_completion_days: number | null
  tasks_by_priority: Record<Priority, number>
  tasks_by_status: Record<TaskStatus, number>
  tasks_by_employee: EmployeeWorkload[]
  projects: ProjectProgressEntry[]
}

// ---- audit trail (FR-096) --------------------------------------------------

export interface AuditLogChange {
  field?: string
  from?: string | null
  to?: string | null
}

export interface AuditLogEntry {
  id: number
  actor: number | null
  actor_username: string | null
  action: string
  model_name: string
  object_id: string
  changes: Record<string, { from: string | null; to: string | null }>
  timestamp: string
}
