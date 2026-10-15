import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import Notifications from '../Notifications'
import { mockApi, renderAsUser, clearSession } from '../../test/harness'
import { meMember, notification1, paginated } from '../../test/fixtures'

afterEach(() => { clearSession() })

describe('Notifications page', () => {
  it('lists notifications and marks all as read', async () => {
    const mock = mockApi()
    mock.onGet('/notifications/').reply(200, paginated([notification1]))
    renderAsUser(<Notifications />, meMember, mock)
    expect(await screen.findByText(/you were assigned/i)).toBeInTheDocument()

    mock.onPost('/notifications/mark-all-read/').reply(204)
    await userEvent.click(screen.getByRole('button', { name: /mark all as read/i }))
  })

  it('shows an error instead of silently empty results on failure', async () => {
    const mock = mockApi()
    mock.onGet('/notifications/').reply(500, { detail: 'Could not load notifications.' })
    renderAsUser(<Notifications />, meMember, mock)
    expect(await screen.findByText(/could not load notifications/i)).toBeInTheDocument()
  })
})
