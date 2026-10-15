import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import Reports from '../Reports'
import { mockApi, renderAsUser, clearSession } from '../../test/harness'
import { mePM, paginated, project1, reportData } from '../../test/fixtures'

afterEach(() => { clearSession() })

describe('Reports page', () => {
  it('renders metrics, charts and the export button for a manager', async () => {
    const mock = mockApi()
    mock.onGet('/projects/').reply(200, paginated([project1]))
    mock.onGet('/reports/summary/').reply(200, reportData)
    renderAsUser(<Reports />, mePM, mock)

    expect(await screen.findByText('8')).toBeInTheDocument() // tasks_created
    expect(screen.getByText('Workload by employee', { exact: false })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /export csv/i })).toBeInTheDocument()
  })

  it('shows an access-denied error for a non-manager', async () => {
    const mock = mockApi()
    mock.onGet('/projects/').reply(200, paginated([]))
    mock.onGet('/reports/summary/').reply(403, { detail: 'Only managers can view reports.' })
    renderAsUser(<Reports />, mePM, mock)
    expect(await screen.findByText(/only managers can view reports/i)).toBeInTheDocument()
  })
})
