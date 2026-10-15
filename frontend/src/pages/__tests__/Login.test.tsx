import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import { AuthProvider } from '../../context/AuthContext'
import { mockApi, clearSession } from '../../test/harness'
import { mePM } from '../../test/fixtures'
import Login from '../Login'

afterEach(() => { clearSession() })

describe('Login page', () => {
  it('submits credentials and shows a server error on failure', async () => {
    const mock = mockApi()
    mock.onPost('/auth/login/').reply(400, { detail: 'Invalid username or password.' })
    render(
      <MemoryRouter>
        <AuthProvider><Login /></AuthProvider>
      </MemoryRouter>
    )

    await userEvent.type(screen.getByLabelText(/username/i), 'pam')
    await userEvent.type(screen.getByLabelText(/password/i), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText(/invalid username or password/i)).toBeInTheDocument()
  })

  it('logs in successfully and stores the session', async () => {
    const mock = mockApi()
    mock.onPost('/auth/login/').reply(200, { access: 'a', refresh: 'b', user: mePM })
    render(
      <MemoryRouter>
        <AuthProvider><Login /></AuthProvider>
      </MemoryRouter>
    )

    await userEvent.type(screen.getByLabelText(/username/i), 'pam')
    await userEvent.type(screen.getByLabelText(/password/i), 'right')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => expect(localStorage.getItem('tf_access')).toBe('a'))
  })

  it('shows a footer with the current year and still offers the sign-up link', () => {
    mockApi()
    render(
      <MemoryRouter>
        <AuthProvider><Login /></AuthProvider>
      </MemoryRouter>
    )
    const footer = screen.getByRole('contentinfo')
    expect(footer).toHaveTextContent(`© ${new Date().getFullYear()} TaskFlow`)
    expect(screen.getByRole('link', { name: /create one/i })).toHaveAttribute('href', '/register')
  })
})
