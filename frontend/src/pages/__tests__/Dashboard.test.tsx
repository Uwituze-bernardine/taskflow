import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import Dashboard from '../Dashboard'
import { mockApi, renderAsUser, clearSession } from '../../test/harness'
import { dashboardData, meMember, mePM } from '../../test/fixtures'

afterEach(() => { clearSession() })

describe('Dashboard page', () => {
  it('renders personal stats, pending/overdue tasks and projects for a team member', async () => {
    const mock = mockApi()
    mock.onGet('/dashboard/').reply(200, { ...dashboardData, team_stats: null })
    renderAsUser(<Dashboard />, meMember, mock)

    expect(await screen.findByText('My Dashboard')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument() // total
    expect(screen.getByText('Pending one')).toBeInTheDocument()
    expect(screen.getByText('Overdue one')).toBeInTheDocument()
    expect(screen.getByText('Apollo')).toBeInTheDocument()
    expect(screen.queryByText('Team statistics')).not.toBeInTheDocument()
  })

  it('renders team statistics for a manager', async () => {
    const mock = mockApi()
    mock.onGet('/dashboard/').reply(200, dashboardData)
    renderAsUser(<Dashboard />, mePM, mock)

    expect(await screen.findByText('Team statistics')).toBeInTheDocument()
    // "Mo Member" legitimately appears twice: once as the overdue task's assignee, once in the team table.
    expect(screen.getAllByText('Mo Member').length).toBeGreaterThanOrEqual(2)
  })

  it('shows an error if the dashboard fails to load', async () => {
    const mock = mockApi()
    mock.onGet('/dashboard/').reply(500, { detail: 'Server error.' })
    renderAsUser(<Dashboard />, meMember, mock)
    expect(await screen.findByText(/could not load the dashboard/i)).toBeInTheDocument()
  })

  it('renders with no projects and no pending tasks without crashing', async () => {
    const mock = mockApi()
    mock.onGet('/dashboard/').reply(200, {
      my_tasks: { total: 0, TODO: 0, IN_PROGRESS: 0, BLOCKED: 0, UNDER_REVIEW: 0, COMPLETED: 0, CANCELLED: 0, overdue: 0 },
      pending_tasks: [], overdue_tasks: [], projects: [], team_stats: null,
    })
    renderAsUser(<Dashboard />, meMember, mock)
    expect(await screen.findByText(/all caught up/i)).toBeInTheDocument()
  })
})
