import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import { AuthProvider } from '../../context/AuthContext'
import Profile from '../Profile'
import Register from '../Register'
import { clearSession, mockApi, renderAsUser } from '../../test/harness'
import { mePM } from '../../test/fixtures'

afterEach(() => { clearSession() })

const allOn = { assigned: true, status_changed: true, mentioned: true, due_soon: true, overdue: true }

describe('Profile page', () => {
  it('saves profile changes', async () => {
    const mock = mockApi()
    mock.onGet('/notifications/preferences/').reply(200, allOn)
    renderAsUser(<Profile />, mePM, mock)

    const first = await screen.findByDisplayValue('Pam')
    mock.onPatch('/users/me/').reply(200, { ...mePM, first_name: 'Pamela' })
    await userEvent.clear(first)
    await userEvent.type(first, 'Pamela')
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))
    expect(await screen.findByText('Profile updated.')).toBeInTheDocument()
  })

  it('informs the user to verify a changed email address', async () => {
    const mock = mockApi()
    mock.onGet('/notifications/preferences/').reply(200, allOn)
    renderAsUser(<Profile />, mePM, mock)
    await screen.findByDisplayValue('Pam')

    mock.onPatch('/users/me/').reply(200, {
      ...mePM, email: 'new@example.com', email_verified: false,
    })
    const email = screen.getByLabelText(/^email/i)
    await userEvent.clear(email)
    await userEvent.type(email, 'new@example.com')
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    expect(await screen.findByText(/verify your new email address/i)).toBeInTheDocument()
  })

  it('toggles a notification preference and sends only that key', async () => {
    const mock = mockApi()
    mock.onGet('/notifications/preferences/').reply(200, allOn)
    renderAsUser(<Profile />, mePM, mock)

    const box = await screen.findByLabelText(/mentioned in a comment/i)
    expect(box).toBeChecked()
    mock.onPatch('/notifications/preferences/').reply(200, { ...allOn, mentioned: false })
    await userEvent.click(box)

    await waitFor(() => expect(box).not.toBeChecked())
    expect(JSON.parse(mock.history.patch[0].data)).toEqual({ mentioned: false })
  })

  it('reverts the toggle and shows an error if saving the preference fails', async () => {
    const mock = mockApi()
    mock.onGet('/notifications/preferences/').reply(200, allOn)
    renderAsUser(<Profile />, mePM, mock)

    const box = await screen.findByLabelText(/due soon/i)
    mock.onPatch('/notifications/preferences/').reply(500, { detail: 'Could not save.' })
    await userEvent.click(box)

    expect(await screen.findByText(/could not save/i)).toBeInTheDocument()
    expect(box).toBeChecked() // optimistic update rolled back
  })

  it('rejects mismatched new passwords without calling the API', async () => {
    const mock = mockApi()
    mock.onGet('/notifications/preferences/').reply(200, allOn)
    renderAsUser(<Profile />, mePM, mock)
    await screen.findByDisplayValue('Pam')

    await userEvent.type(screen.getByLabelText(/current password/i), 'old-pass')
    await userEvent.type(screen.getByLabelText(/^new password/i), 'aaaa1111')
    await userEvent.type(screen.getByLabelText(/confirm new password/i), 'bbbb2222')
    await userEvent.click(screen.getByRole('button', { name: /change password/i }))

    expect(await screen.findByText(/do not match/i)).toBeInTheDocument()
    expect(mock.history.post.some((r) => r.url?.includes('change-password'))).toBe(false)
  })
})

describe('Register page', () => {
  function renderRegister() {
    return render(<MemoryRouter><AuthProvider><Register /></AuthProvider></MemoryRouter>)
  }

  it('rejects mismatched passwords client-side', async () => {
    mockApi()
    renderRegister()
    expect(document.querySelectorAll('.auth-story .auth-slide')).toHaveLength(2)
    await userEvent.type(screen.getByLabelText(/first name/i), 'A')
    await userEvent.type(screen.getByLabelText(/last name/i), 'B')
    await userEvent.type(screen.getByLabelText(/^username/i), 'ab')
    await userEvent.type(screen.getByLabelText(/^email/i), 'ab@example.com')
    await userEvent.type(screen.getByLabelText(/^password/i), 'Sup3r-secret-pw')
    await userEvent.type(screen.getByLabelText(/confirm password/i), 'different')
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument()
  })

  it('shows server-side validation errors', async () => {
    const mock = mockApi()
    mock.onPost('/auth/register/').reply(400, { email: ['A user with this email already exists.'] })
    renderRegister()
    await userEvent.type(screen.getByLabelText(/first name/i), 'A')
    await userEvent.type(screen.getByLabelText(/last name/i), 'B')
    await userEvent.type(screen.getByLabelText(/^username/i), 'ab')
    await userEvent.type(screen.getByLabelText(/^email/i), 'ab@example.com')
    await userEvent.type(screen.getByLabelText(/^password/i), 'Sup3r-secret-pw')
    await userEvent.type(screen.getByLabelText(/confirm password/i), 'Sup3r-secret-pw')
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByText(/already exists/i)).toBeInTheDocument()
  })

  it('asks the new user to verify email instead of signing in immediately', async () => {
    const mock = mockApi()
    mock.onPost('/auth/register/').reply(201, {
      detail: 'Account created. Check your email for a verification link before signing in.',
    })
    renderRegister()
    await userEvent.type(screen.getByLabelText(/first name/i), 'A')
    await userEvent.type(screen.getByLabelText(/last name/i), 'B')
    await userEvent.type(screen.getByLabelText(/^username/i), 'ab')
    await userEvent.type(screen.getByLabelText(/^email/i), 'ab@example.com')
    await userEvent.type(screen.getByLabelText(/^password/i), 'Sup3r-secret-pw')
    await userEvent.type(screen.getByLabelText(/confirm password/i), 'Sup3r-secret-pw')
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByText(/check your inbox for a verification link/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /resend verification email/i })).toHaveAttribute(
      'href',
      '/resend-verification?email=ab%40example.com',
    )
    expect(mock.history.post.map((request) => request.url)).toEqual(['/auth/register/'])
  })
})
