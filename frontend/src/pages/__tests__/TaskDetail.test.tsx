import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import { mockApi, renderAsUser, clearSession } from '../../test/harness'
import {
  attachment1, comment1, historyEntries, makeTask, mePM, paginated, project1, workflowOptions,
} from '../../test/fixtures'
import TaskDetail from '../TaskDetail'

afterEach(() => { clearSession() })

function renderTaskDetail(mock: ReturnType<typeof mockApi>, taskOverrides = {}) {
  const task = makeTask(taskOverrides)
  mock.onGet('/tasks/100/').reply(200, task)
  mock.onGet('/tasks/100/subtasks/').reply(200, [])
  mock.onGet('/comments/', { params: { task: 100 } }).reply(200, paginated([comment1]))
  mock.onGet('/attachments/', { params: { task: 100 } }).reply(200, paginated([attachment1]))
  mock.onGet('/tasks/100/history/').reply(200, historyEntries)
  mock.onGet('/tasks/workflow/').reply(200, workflowOptions)
  mock.onGet('/projects/10/').reply(200, project1)
  mock.onGet('/attachments/settings/').reply(200, { allowed_extensions: 'pdf,png', max_size_mb: 25, extension_list: ['pdf', 'png'] })
  return renderAsUser(
    <Routes><Route path="/tasks/:id" element={<TaskDetail />} /></Routes>,
    mePM, mock, '/tasks/100'
  )
}

describe('TaskDetail page', () => {
  it('renders task details, comments, attachments and history without crashing', async () => {
    const mock = mockApi()
    renderTaskDetail(mock)

    expect(await screen.findByRole('heading', { name: 'Design database' })).toBeInTheDocument()
    expect(screen.getByText('Looks good so far')).toBeInTheDocument()
    expect(screen.getByText('schema.pdf')).toBeInTheDocument()
    expect(screen.getByText(/changed this task/i)).toBeInTheDocument()
  })

  it('posts a new comment and shows it immediately', async () => {
    const mock = mockApi()
    renderTaskDetail(mock)
    await screen.findByRole('heading', { name: 'Design database' })

    mock.onPost('/comments/').reply(201, {
      id: 2, task: 100, author: 2, author_detail: comment1.author_detail, body: 'New comment here',
      mentioned_users_detail: [], is_edited: false, is_deleted: false, can_edit: true, can_delete: true,
      created_at: '2026-01-03T00:00:00Z', edited_at: null,
    })
    const input = screen.getByPlaceholderText(/add a comment/i)
    await userEvent.type(input, 'New comment here')
    await userEvent.click(screen.getByRole('button', { name: /post/i }))

    expect(await screen.findByText('New comment here')).toBeInTheDocument()
  })

  it('changes status through the StatusControl dropdown', async () => {
    const mock = mockApi()
    renderTaskDetail(mock)
    await screen.findByRole('heading', { name: 'Design database' })
    await screen.findByDisplayValue('In Progress')

    mock.onPost('/tasks/100/status/').reply(200, makeTask({ status: 'COMPLETED', status_label: 'Completed' }))
    const select = screen.getByDisplayValue('In Progress')
    await userEvent.selectOptions(select, 'COMPLETED')

    await waitFor(() => {
      const posts = mock.history.post.filter((r) => r.url === '/tasks/100/status/')
      expect(posts).toHaveLength(1)
      expect(JSON.parse(posts[0].data)).toEqual({ status: 'COMPLETED' })
    })
  })

  it('shows the blocked banner when a task is waiting on a dependency', async () => {
    const mock = mockApi()
    renderTaskDetail(mock, {
      is_blocked_by_dependencies: true,
      blocked_by: [{ id: 99, title: 'Design DB', status: 'TODO', status_label: 'To Do' }],
      enforce_dependencies: true,
    })
    expect(await screen.findByText(/blocked: waiting on/i)).toBeInTheDocument()
    expect(screen.getByText(/Design DB/)).toBeInTheDocument()
  })

  it('shows recurrence info for a recurring task', async () => {
    const mock = mockApi()
    renderTaskDetail(mock, { recurrence: 'WEEKLY', is_recurring: true, next_occurrence_due_date: '2026-02-01' })
    expect(await screen.findByText(/weekly/i)).toBeInTheDocument()
    expect(screen.getByText(/2026-02-01|Feb/i)).toBeInTheDocument()
  })

  it('renders a subtask without crashing (no dependency/subtask panels)', async () => {
    const mock = mockApi()
    renderTaskDetail(mock, { parent_task: 55, parent_title: 'Parent task', id: 100 })
    expect(await screen.findByText(/subtask of/i)).toBeInTheDocument()
  })

  it('shows an error banner if the task fails to load', async () => {
    const mock = mockApi()
    mock.onGet('/tasks/100/').reply(404, { detail: 'Not found.' })
    mock.onGet('/tasks/100/subtasks/').reply(200, [])
    mock.onGet('/comments/', { params: { task: 100 } }).reply(200, paginated([]))
    mock.onGet('/attachments/', { params: { task: 100 } }).reply(200, paginated([]))
    mock.onGet('/tasks/100/history/').reply(200, [])
    renderAsUser(<Routes><Route path="/tasks/:id" element={<TaskDetail />} /></Routes>, mePM, mock, '/tasks/100')
    expect(await screen.findByText(/not found/i)).toBeInTheDocument()
  })
})
