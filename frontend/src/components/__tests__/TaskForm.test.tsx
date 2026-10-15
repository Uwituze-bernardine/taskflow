import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import TaskForm from '../TaskForm'
import { mockApi, renderAsUser, clearSession } from '../../test/harness'
import { customPriority1, makeTask, mePM, meMember, paginated, project1, userSummary } from '../../test/fixtures'

afterEach(() => { clearSession() })

function stubCommonLookups(mock: ReturnType<typeof mockApi>) {
  mock.onGet('/projects/').reply(200, paginated([project1]))
  mock.onGet('/users/').reply(200, paginated([userSummary(mePM), userSummary(meMember)]))
  mock.onGet('/tasks/priorities/').reply(200, [customPriority1])
}

describe('TaskForm', () => {
  it('create mode: submits a new task with the typed fields', async () => {
    const mock = mockApi()
    stubCommonLookups(mock)
    const onSaved = vi.fn()
    renderAsUser(<TaskForm onSaved={onSaved} onCancel={() => {}} />, mePM, mock)

    await screen.findByText('Apollo') // project options loaded
    mock.onPost('/tasks/').reply(201, makeTask({ title: 'New task' }))

    await userEvent.type(screen.getByLabelText(/^title/i), 'New task')
    await userEvent.click(screen.getByRole('button', { name: /create task/i }))

    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    const body = JSON.parse(mock.history.post[0].data)
    expect(body.title).toBe('New task')
  })

  it('edit mode: pre-fills from the task and submits changes', async () => {
    const mock = mockApi()
    stubCommonLookups(mock)
    const task = makeTask()
    const onSaved = vi.fn()
    renderAsUser(<TaskForm task={task} onSaved={onSaved} onCancel={() => {}} />, mePM, mock)

    expect(await screen.findByDisplayValue('Design database')).toBeInTheDocument()
    mock.onPatch('/tasks/100/').reply(200, { ...task, title: 'Renamed' })

    const titleInput = screen.getByDisplayValue('Design database')
    await userEvent.clear(titleInput)
    await userEvent.type(titleInput, 'Renamed')
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => expect(onSaved).toHaveBeenCalled())
  })

  it('subtask mode: locks the project field and posts to the subtasks endpoint', async () => {
    const mock = mockApi()
    stubCommonLookups(mock)
    const parent = makeTask()
    const onSaved = vi.fn()
    renderAsUser(<TaskForm parentTask={parent} onSaved={onSaved} onCancel={() => {}} />, mePM, mock)

    await screen.findByDisplayValue('Apollo') // the locked, disabled project field
    mock.onPost('/tasks/100/subtasks/').reply(201, makeTask({ id: 200, parent_task: 100 }))
    await userEvent.type(screen.getByLabelText(/^title/i), 'A subtask')
    await userEvent.click(screen.getByRole('button', { name: /add subtask/i }))

    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    expect(mock.history.post.some((r) => r.url === '/tasks/100/subtasks/')).toBe(true)
  })

  it('selecting a custom priority sends its base category', async () => {
    const mock = mockApi()
    stubCommonLookups(mock)
    const onSaved = vi.fn()
    renderAsUser(<TaskForm onSaved={onSaved} onCancel={() => {}} />, mePM, mock)

    await screen.findByText('Apollo')
    mock.onPost('/tasks/').reply(201, makeTask())
    await userEvent.type(screen.getByLabelText(/^title/i), 'X')

    const prioritySelect = await screen.findByDisplayValue('Medium')
    await userEvent.selectOptions(prioritySelect, 'custom:1')
    await userEvent.click(screen.getByRole('button', { name: /create task/i }))

    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    const body = JSON.parse(mock.history.post[0].data)
    expect(body).toMatchObject({ priority: 'CRITICAL', custom_priority: 1 })
  })

  it('shows a server validation error inline', async () => {
    const mock = mockApi()
    stubCommonLookups(mock)
    renderAsUser(<TaskForm onSaved={() => {}} onCancel={() => {}} />, mePM, mock)
    await screen.findByText('Apollo')

    mock.onPost('/tasks/').reply(400, { title: ['This field may not be blank.'] })
    await userEvent.type(screen.getByLabelText(/^title/i), 'x')
    await userEvent.click(screen.getByRole('button', { name: /create task/i }))

    expect(await screen.findByText(/may not be blank/i)).toBeInTheDocument()
  })

  it('toggling recurrence shows the interval/end-date fields', async () => {
    const mock = mockApi()
    stubCommonLookups(mock)
    renderAsUser(<TaskForm onSaved={() => {}} onCancel={() => {}} />, mePM, mock)
    await screen.findByText('Apollo')

    expect(screen.queryByLabelText(/stop repeating/i)).not.toBeInTheDocument()
    await userEvent.selectOptions(screen.getByDisplayValue('Does not repeat'), 'WEEKLY')
    expect(screen.getByLabelText(/stop repeating/i)).toBeInTheDocument()
  })
})
