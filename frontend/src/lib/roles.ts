import type { Role } from '../types'

export const ROLE_LABELS: Record<Role, string> = {
  ADMIN: 'System Administrator',
  PROJECT_MANAGER: 'Project Manager',
  TEAM_LEADER: 'Team Leader',
  TEAM_MEMBER: 'Team Member',
}

export const ROLE_OPTIONS = (Object.keys(ROLE_LABELS) as Role[]).map((value) => ({
  value,
  label: ROLE_LABELS[value],
}))

// FR-006: one place that decides what each role may see/do in the UI.
// The backend enforces the same rules; this only hides controls that would be refused.
export const isAdmin = (role?: Role) => role === 'ADMIN'
export const isManager = (role?: Role) =>
  role === 'ADMIN' || role === 'PROJECT_MANAGER' || role === 'TEAM_LEADER'

// FR-008 / FR-015: who sees the "New project" / "New task" buttons (the API enforces the same).
export const canCreateProject = (role?: Role) => role === 'ADMIN' || role === 'PROJECT_MANAGER'
export const canCreateTask = (role?: Role) => isManager(role)
