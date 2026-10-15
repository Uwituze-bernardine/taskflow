import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import AuditLog from '../AuditLog'
import { mockApi, renderAsUser, clearSession } from '../../test/harness'
import { meAdmin, paginated } from '../../test/fixtures'

afterEach(() => { clearSession() })

describe('AuditLog page', () => {
  it('renders entries with changes', async () => {
    const mock = mockApi()
    mock.onGet('/audit/').reply(200, paginated([
      { id: 1, actor: 2, actor_username: 'pam', action: 'task.updated', model_name: 'Task', object_id: '100',
        changes: { priority: { from: 'Medium', to: 'High' } }, timestamp: '2026-01-01T00:00:00Z' },
    ]))
    renderAsUser(<AuditLog />, meAdmin, mock)
    expect(await screen.findByText(/updated Task #100/)).toBeInTheDocument()
    expect(screen.getByText(/Medium/)).toBeInTheDocument()
  })

  it('shows an error instead of silently empty results on failure', async () => {
    const mock = mockApi()
    mock.onGet('/audit/').reply(500, { detail: 'Audit service unavailable.' })
    renderAsUser(<AuditLog />, meAdmin, mock)
    expect(await screen.findByText(/audit service unavailable/i)).toBeInTheDocument()
  })
})
