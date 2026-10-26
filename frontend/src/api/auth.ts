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
export async function register(payload: RegisterPayload): Promise<void> {
  await client.post('/auth/register/', payload)
}

// FR-002
export async function login(username: string, password: string): Promise<User> {
  const { data } = await client.post('/auth/login/', { username, password })
  tokenStore.set(data.access, data.refresh)
  return data.user as User
}

export async function verifyEmail(uid: string, token: string): Promise<string> {
  const { data } = await client.post('/auth/verify-email/', { uid, token })
  return data.detail as string
}

export async function resendVerification(email: string): Promise<string> {
  const { data } = await client.post('/auth/resend-verification/', { email })
  return data.detail as string
}

export async function requestPasswordReset(email: string): Promise<string> {
  const { data } = await client.post('/auth/password-reset/', { email })
  return data.detail as string
}

export async function confirmPasswordReset(uid: string, token: string, new_password: string): Promise<string> {
  const { data } = await client.post('/auth/password-reset/confirm/', { uid, token, new_password })
  return data.detail as string
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
