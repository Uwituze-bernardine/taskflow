import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AdminPriorities from '../AdminPriorities'
import AdminSettings from '../AdminSettings'
import AdminStatuses from '../AdminStatuses'
import AdminTags from '../AdminTags'
import { mockApi, renderAsUser, clearSession } from '../../test/harness'
import { customPriority1, customStatus1, meAdmin, taskTag1 } from '../../test/fixtures'

afterEach(() => { clearSession(); vi.restoreAllMocks() })

describe('Admin configuration pages render without crashing', () => {
  it('AdminStatuses lists custom statuses', async () => {
    const mock = mockApi()
    mock.onGet('/tasks/statuses/').reply(200, [customStatus1])
    renderAsUser(<AdminStatuses />, meAdmin, mock)
    expect(await screen.findByText('QA Testing')).toBeInTheDocument()
  })

  it('AdminPriorities lists custom priorities and deactivates one', async () => {
    const mock = mockApi()
    mock.onGet('/tasks/priorities/').reply(200, [customPriority1])
    renderAsUser(<AdminPriorities />, meAdmin, mock)
    expect(await screen.findByText('Showstopper')).toBeInTheDocument()

    mock.onPatch('/tasks/priorities/1/').reply(200, { ...customPriority1, is_active: false })
    mock.onGet('/tasks/priorities/').reply(200, [{ ...customPriority1, is_active: false }]) // the page reloads after saving
    await userEvent.click(screen.getByRole('button', { name: /deactivate/i }))
    expect(await screen.findByText('Inactive')).toBeInTheDocument()
  })

  it('AdminTags lists and adds a tag', async () => {
    const mock = mockApi()
    mock.onGet('/tasks/tags/').reply(200, [taskTag1])
    renderAsUser(<AdminTags />, meAdmin, mock)
    expect(await screen.findByText('backend')).toBeInTheDocument()

    mock.onPost('/tasks/tags/').reply(201, { id: 2, name: 'urgent' })
    mock.onGet('/tasks/tags/').reply(200, [taskTag1, { id: 2, name: 'urgent' }])
    await userEvent.type(screen.getByPlaceholderText(/new tag name/i), 'urgent')
    await userEvent.click(screen.getByRole('button', { name: /add tag/i }))
    expect(await screen.findByText('urgent')).toBeInTheDocument()
  })

  it('AdminSettings loads and saves both settings forms', async () => {
    const mock = mockApi()
    mock.onGet('/notifications/settings/').reply(200, { due_soon_days: 2 })
    mock.onGet('/attachments/settings/').reply(200, { allowed_extensions: 'pdf,png', max_size_mb: 25, extension_list: ['pdf', 'png'] })
    renderAsUser(<AdminSettings />, meAdmin, mock)

    expect(await screen.findByDisplayValue('2')).toBeInTheDocument()
    expect(await screen.findByDisplayValue('25')).toBeInTheDocument()

    mock.onPatch('/notifications/settings/').reply(200, { due_soon_days: 5 })
    const [dueSoonInput] = screen.getAllByDisplayValue('2')
    await userEvent.clear(dueSoonInput)
    await userEvent.type(dueSoonInput, '5')
    await userEvent.click(screen.getAllByRole('button', { name: /^save$/i })[0])
    expect(await screen.findAllByText('Saved.')).toHaveLength(1)
  })
})
