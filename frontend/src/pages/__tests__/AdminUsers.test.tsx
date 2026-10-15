import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import AdminUsers from '../AdminUsers'
import { mockApi, renderAsUser, clearSession } from '../../test/harness'
import { meAdmin, mePM, paginated } from '../../test/fixtures'

afterEach(() => { clearSession() })

describe('AdminUsers page', () => {
  it('lists users and resets a password via the modal', async () => {
    const mock = mockApi()
    mock.onGet('/users/').reply(200, paginated([meAdmin, mePM]))
    renderAsUser(<AdminUsers />, meAdmin, mock)

    expect(await screen.findByText('@pam')).toBeInTheDocument()
    const resetButtons = screen.getAllByRole('button', { name: /reset password/i })
    await userEvent.click(resetButtons[1]) // pam's row (admin's own row disables deactivate, not reset)

    const heading = await screen.findByText(/reset password for/i)
    const modal = within(heading.closest('form') as HTMLElement) // row buttons share the same label
    mock.onPost('/users/2/reset-password/').reply(200, { temporary_password: 'abc123' })
    await userEvent.click(modal.getByRole('button', { name: /^reset password$/i }))

    expect(await screen.findByText(/temporary password for pam: abc123/i)).toBeInTheDocument()
  })

  it('deactivates a user', async () => {
    const mock = mockApi()
    mock.onGet('/users/').reply(200, paginated([meAdmin, mePM]))
    renderAsUser(<AdminUsers />, meAdmin, mock)
    await screen.findByText('@pam')

    mock.onPost('/users/2/deactivate/').reply(200, { ...mePM, is_active_member: false })
    const confirmSpy = window.confirm
    window.confirm = () => true
    // Index 0 is the admin's own row, whose Deactivate is correctly disabled; pam is index 1.
    const buttons = screen.getAllByRole('button', { name: /^deactivate$/i })
    expect(buttons[0]).toBeDisabled()
    await userEvent.click(buttons[1])
    window.confirm = confirmSpy

    await waitFor(() => expect(mock.history.post.some((r) => r.url === '/users/2/deactivate/')).toBe(true))
  })
})
