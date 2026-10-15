import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import Tasks from '../Tasks'
import { mockApi, renderAsUser, clearSession } from '../../test/harness'
import { makeTask, meMember, mePM, paginated, project1, userSummary } from '../../test/fixtures'

afterEach(() => { clearSession() })

function stubLookups(mock: ReturnType<typeof mockApi>) {
  mock.onGet('/projects/').reply(200, paginated([project1]))
  mock.onGet('/users/').reply(200, paginated([userSummary(mePM), userSummary(meMember)]))
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
