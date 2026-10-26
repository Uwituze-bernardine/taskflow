import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import { mockApi } from '../../test/harness'
import ForgotPassword from '../ForgotPassword'
import ResetPassword from '../ResetPassword'
import VerifyEmail from '../VerifyEmail'

afterEach(() => {
  localStorage.clear()
})

describe('account recovery', () => {
  it('requests a password reset and shows the generic confirmation', async () => {
    const mock = mockApi()
    mock.onPost('/auth/password-reset/').reply(200, {
      detail: 'If an active account uses that email, password reset instructions have been sent.',
    })
    render(<MemoryRouter><ForgotPassword /></MemoryRouter>)

    await userEvent.type(screen.getByLabelText(/email/i), 'person@example.com')
    await userEvent.click(screen.getByRole('button', { name: /send reset link/i }))

    expect(await screen.findByRole('status')).toHaveTextContent(/if an active account uses that email/i)
  })

  it('sets a new password using the token in the reset link', async () => {
    const mock = mockApi()
    mock.onPost('/auth/password-reset/confirm/', {
      uid: 'abc', token: 'valid-token', new_password: 'new-strong-password',
    }).reply(200, { detail: 'Password reset. You can now sign in.' })
    render(
      <MemoryRouter initialEntries={['/reset-password?uid=abc&token=valid-token']}>
        <ResetPassword />
      </MemoryRouter>
    )

    await userEvent.type(screen.getByLabelText(/^new password/i), 'new-strong-password')
    await userEvent.type(screen.getByLabelText(/confirm new password/i), 'new-strong-password')
    await userEvent.click(screen.getByRole('button', { name: /set new password/i }))

    expect(await screen.findByRole('status')).toHaveTextContent(/password reset/i)
  })

  it('verifies an email from the link and provides the sign-in route', async () => {
    const mock = mockApi()
    mock.onPost('/auth/verify-email/', { uid: 'abc', token: 'verification-token' })
      .reply(200, { detail: 'Email verified. You can now sign in.' })
    render(
      <MemoryRouter initialEntries={['/verify-email?uid=abc&token=verification-token']}>
        <Routes><Route path="/verify-email" element={<VerifyEmail />} /></Routes>
      </MemoryRouter>
    )

    expect(await screen.findByText(/email verified/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /continue to sign in/i })).toHaveAttribute('href', '/login')
  })
})
