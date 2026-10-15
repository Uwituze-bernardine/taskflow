import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import Calendar from '../Calendar'
import { mockApi, renderAsUser, clearSession } from '../../test/harness'
import { makeTask, mePM, paginated, project1, userSummary, meMember } from '../../test/fixtures'

afterEach(() => { clearSession() })

describe('Calendar page', () => {
  it('renders the month grid and due tasks without crashing', async () => {
    const mock = mockApi()
    mock.onGet('/projects/').reply(200, paginated([project1]))
    mock.onGet('/users/').reply(200, paginated([userSummary(mePM), userSummary(meMember)]))
    mock.onGet('/tasks/calendar/').reply(200, [makeTask({ due_date: new Date().toISOString().slice(0, 10) })])

    renderAsUser(<Calendar />, mePM, mock)
    expect(await screen.findByText('Calendar')).toBeInTheDocument()
    expect(await screen.findByText('Design database')).toBeInTheDocument()
  })

  it('shows an error banner (not a silent empty calendar) when the fetch fails', async () => {
    const mock = mockApi()
    mock.onGet('/projects/').reply(200, paginated([project1]))
    mock.onGet('/users/').reply(200, paginated([]))
    mock.onGet('/tasks/calendar/').reply(500, { detail: 'Calendar backend is down.' })

    renderAsUser(<Calendar />, mePM, mock)
    expect(await screen.findByText(/calendar backend is down/i)).toBeInTheDocument()
  })
})
