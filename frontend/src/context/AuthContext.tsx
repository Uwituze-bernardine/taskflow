import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react'
import { login as apiLogin, logout as apiLogout, register as apiRegister, RegisterPayload } from '../api/auth'
import { tokenStore } from '../api/client'
import { getMe } from '../api/users'
import type { User } from '../types'

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  logout: () => Promise<void>
  /** Replace the cached user after their profile changed (FR-003). */
  setCurrentUser: (user: User) => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

const STORED_USER_KEY = 'tf_user'

function readStoredUser(): User | null {
  try {
    const raw = localStorage.getItem(STORED_USER_KEY)
    return raw && tokenStore.getAccess() ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const setCurrentUser = useCallback((next: User) => {
    localStorage.setItem(STORED_USER_KEY, JSON.stringify(next))
    setUser(next)
  }, [])

  useEffect(() => {
    // FR-002: restore the session after a page refresh, then re-check it with the
    // server so a changed role or a deactivated account is picked up immediately.
    const stored = readStoredUser()
    if (!stored) {
      setIsLoading(false)
      return
    }
    setUser(stored)
    setIsLoading(false)
    getMe()
      .then(setCurrentUser)
      .catch(() => {
        // The API client already clears tokens and redirects on a dead session.
      })
  }, [setCurrentUser])

  async function login(username: string, password: string) {
    setCurrentUser(await apiLogin(username, password))
  }

  // FR-001: new accounts must verify their email before they can sign in.
  async function register(payload: RegisterPayload) {
    await apiRegister(payload)
  }

  async function logout() {
    await apiLogout()
    localStorage.removeItem(STORED_USER_KEY)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, setCurrentUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
