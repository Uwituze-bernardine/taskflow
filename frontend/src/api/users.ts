import { client } from './client'
import type { Paginated, Role, User, UserSummary } from '../types'

export interface UserFilters {
  search?: string
  role?: Role | ''
  is_active_member?: boolean | ''
  page?: number
}

export interface NewUserPayload {
  username: string
  email: string
  first_name: string
  last_name: string
  password: string
  role: Role
}

export type ProfilePayload = Pick<User, 'email' | 'first_name' | 'last_name'> &
  Partial<Pick<User, 'job_title' | 'phone'>>

// --- current user (FR-003) ---------------------------------------------

export async function getMe(): Promise<User> {
  const { data } = await client.get('/users/me/')
  return data
}

export async function updateMe(payload: Partial<ProfilePayload>): Promise<User> {
  const { data } = await client.patch('/users/me/', payload)
  return data
}

export async function changePassword(current_password: string, new_password: string): Promise<void> {
  await client.post('/users/me/change-password/', { current_password, new_password })
}

// --- user directory (any signed-in user) --------------------------------

/**
 * Every user the current person may see, as a plain array. Used by pickers such as the
 * task assignee dropdown, so it follows pagination instead of stopping at page 1.
 * Non-admins receive only active users and a minimal set of fields.
 */
export async function listUsers(): Promise<UserSummary[]> {
  const all: UserSummary[] = []
  for (let page = 1; page <= 50; page++) {
    const { data } = await client.get<Paginated<UserSummary> | UserSummary[]>('/users/', { params: { page } })
    if (Array.isArray(data)) return data
    all.push(...data.results)
    if (!data.next) break
  }
  return all
}

// --- administration (FR-004, FR-007) -----------------------------------

/** One filtered page of the full user records (administrators only for the extra fields). */
export async function listUsersPage(filters: UserFilters = {}): Promise<Paginated<User>> {
  const params: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(filters)) {
    if (value !== '' && value !== undefined) params[key] = value
  }
  const { data } = await client.get('/users/', { params })
  return data
}

export async function createUser(payload: NewUserPayload): Promise<User> {
  const { data } = await client.post('/users/', payload)
  return data
}

export async function updateUser(id: number, payload: Partial<User>): Promise<User> {
  const { data } = await client.patch(`/users/${id}/`, payload)
  return data
}

export async function deactivateUser(id: number): Promise<User> {
  const { data } = await client.post(`/users/${id}/deactivate/`)
  return data
}

export async function reactivateUser(id: number): Promise<User> {
  const { data } = await client.post(`/users/${id}/reactivate/`)
  return data
}

/**
 * FR-007. Omit `newPassword` (or pass nothing) to have the server generate a one-time
 * temporary password, returned in `temporary_password`. Pass `newPassword` to set a
 * specific password instead - the response then has no `temporary_password`.
 * Either way the user's existing sessions are ended.
 */
export async function resetUserPassword(id: number, newPassword?: string): Promise<{ temporary_password?: string }> {
  const { data } = await client.post(`/users/${id}/reset-password/`, newPassword ? { new_password: newPassword } : {})
  return data
}
