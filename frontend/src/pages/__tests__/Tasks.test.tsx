import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import Tasks from '../Tasks'
import { mockApi, renderAsUser, clearSession } from '../../test/harness'
import { makeTask, meMember, mePM, paginated, project1, userSummary } from '../../test/fixtures'

afterEach(() => { clearSession() })

function stubLookups(mock: ReturnType<typeof mockApi>) {
  mock.onGet('/projects/').reply(200, paginated([project1]))
  mock.onGet('/users/').reply(200, paginated([userSummary(mePM), userSummary(meMember)]))
  mock.onGet('/tasks/saved-filters/').reply(200, [])
}

describe('Tasks page', () => {
  it('lists tasks and shows manager-only tabs for a manager', async () => {
    const mock = mockApi()
    stubLookups(mock)
    mock.onGet('/tasks/').reply(200, paginated([makeTask()]))
    renderAsUser(<Tasks />, mePM, mock)

    expect(await screen.findByText('Design database')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /my team/i })).toBeInTheDocument()
  })

  it('hides the team tab for a team member', async () => {
    const mock = mockApi()
    stubLookups(mock)
    mock.onGet('/tasks/').reply(200, paginated([makeTask()]))
    renderAsUser(<Tasks />, meMember, mock)
    await screen.findByText('Design database')
    expect(screen.queryByRole('button', { name: /my team/i })).not.toBeInTheDocument()
  })

  it('switches to the "Assigned to me" tab and calls the mine endpoint', async () => {
    const mock = mockApi()
    stubLookups(mock)
    mock.onGet('/tasks/').reply(200, paginated([makeTask()]))
    mock.onGet('/tasks/mine/').reply(200, paginated([makeTask({ id: 101, title: 'Mine only' })]))
    renderAsUser(<Tasks />, meMember, mock)
    await screen.findByText('Design database')

    await userEvent.click(screen.getByRole('button', { name: /assigned to me/i }))
    expect(await screen.findByText('Mine only')).toBeInTheDocument()
  })

  it('filtering by status re-fetches with the right query param', async () => {
    const mock = mockApi()
    stubLookups(mock)
    mock.onGet('/tasks/').reply((config) => {
      if (config.params?.status === 'COMPLETED') {
        return [200, paginated([makeTask({ id: 999, title: 'Done task', status: 'COMPLETED' })])]
      }
      return [200, paginated([makeTask()])]
    })

    it('saves and reapplies a named filter', async () => {
      const mock = mockApi()
      stubLookups(mock)
      mock.onGet('/tasks/').reply(200, paginated([makeTask()]))
      mock.onPost('/tasks/saved-filters/').reply(201, {
        id: 4,
        name: 'Urgent dates',
        filters: { tag: 'urgent', due_after: '2026-11-01' },
        created_at: '2026-10-18T09:00:00Z',
      })
      renderAsUser(<Tasks />, mePM, mock)
      await screen.findByText('Design database')

      await userEvent.type(screen.getByRole('textbox', { name: /name this filter/i }), 'Urgent dates')
      await userEvent.click(screen.getByRole('button', { name: /save filter/i }))
      const select = screen.getByRole('combobox', { name: /saved filters/i })
      await screen.findByRole('option', { name: 'Urgent dates' })
      await userEvent.selectOptions(select, '4')
      await waitFor(() => {
        expect(mock.history.get.some((request) => request.url === '/tasks/' && request.params?.tag === 'urgent' && request.params?.due_after === '2026-11-01')).toBe(true)
      })
    })
    renderAsUser(<Tasks />, mePM, mock)
    await screen.findByText('Design database')

    await userEvent.selectOptions(screen.getByDisplayValue(/all statuses/i), 'COMPLETED')
    expect(await screen.findByText('Done task')).toBeInTheDocument()
  })

  it('shows a server error message', async () => {
    const mock = mockApi()
    stubLookups(mock)
    mock.onGet('/tasks/').reply(500, { detail: 'Boom.' })
    renderAsUser(<Tasks />, mePM, mock)
    expect(await screen.findByText(/boom/i)).toBeInTheDocument()
  })
})
