import { client, tokenStore } from './client'
import type { User } from '../types'

export interface RegisterPayload {
  username: string
  email: string
  first_name: string
  last_name: string
  password: string
}

// FR-001
export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await client.post('/auth/register/', payload)
  return data as User
}

// FR-002
export async function login(username: string, password: string): Promise<User> {
  const { data } = await client.post('/auth/login/', { username, password })
  tokenStore.set(data.access, data.refresh)
  return data.user as User
}

export async function logout(): Promise<void> {
  const refresh = tokenStore.getRefresh()
  try {
    await client.post('/auth/logout/', { refresh })
  } catch {
    // Even if the server can't be reached, the user must end up logged out locally.
  } finally {
    tokenStore.clear()
  }
}
