import { render } from '@testing-library/react'
import type { ReactElement, ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import MockAdapter from 'axios-mock-adapter'
import { client, tokenStore } from '../api/client'
import { AuthProvider, useAuth } from '../context/AuthContext'
import type { User } from '../types'

/** Fresh axios-mock-adapter per test; call `.reset()` happens automatically via afterEach in each file. */
export function mockApi(): MockAdapter {
  return new MockAdapter(client, { onNoMatch: 'throwException' })
}

/** Mirrors ProtectedRoute: the real app never mounts a page until the session is restored. */
function SessionGate({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading || !user) return null
  return <>{children}</>
}

/**
 * Renders `ui` as a logged-in user, inside a MemoryRouter. `mock` should already have its
 * `/users/me/` route stubbed (AuthProvider re-validates the session on mount) and anything
 * else the page under test needs. Real page/component code runs unmodified; only the HTTP
 * layer is faked, so this exercises real hooks, conditionals and prop wiring.
 */
export function renderAsUser(ui: ReactElement, user: User, mock: MockAdapter, initialPath = '/') {
  mock.onGet('/users/me/').reply(200, user)
  localStorage.setItem('tf_user', JSON.stringify(user))
  tokenStore.set('fake-access-token', 'fake-refresh-token')
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthProvider><SessionGate>{ui}</SessionGate></AuthProvider>
    </MemoryRouter>
  )
}

export function clearSession() {
  localStorage.clear()
}
