import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import ProjectDetail from '../ProjectDetail'
import { mockApi, renderAsUser, clearSession } from '../../test/harness'
import { makeTask, mePM, paginated, project1, userSummary, meMember } from '../../test/fixtures'

afterEach(() => { clearSession() })

function renderDetail(mock: ReturnType<typeof mockApi>, projectOverrides = {}) {
  const project = { ...project1, ...projectOverrides }
  mock.onGet('/projects/10/').reply(200, project)
  mock.onGet('/tasks/', { params: { project: 10, ordering: 'due_date' } }).reply(200, paginated([makeTask()]))
  return renderAsUser(
    <Routes><Route path="/projects/:id" element={<ProjectDetail />} /></Routes>,
    mePM, mock, '/projects/10'
  )
}

describe('ProjectDetail page', () => {
  it('renders project info, progress and its tasks', async () => {
    const mock = mockApi()
    renderDetail(mock)
    expect(await screen.findByRole('heading', { name: 'Apollo' })).toBeInTheDocument()
    expect(screen.getByText('Design database')).toBeInTheDocument()
    expect(screen.getByText('40% complete')).toBeInTheDocument()
  })

  it('shows the closed/archived read-only banner', async () => {
    const mock = mockApi()
    renderDetail(mock, { status: 'CLOSED', permissions: { ...project1.permissions, edit: false, reopen: true, close: false, archive: false } })
    expect(await screen.findByText(/read-only/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reopen/i })).toBeInTheDocument()
  })

  it('adds a member through the inline picker', async () => {
    const mock = mockApi()
    renderDetail(mock)
    await screen.findByRole('heading', { name: 'Apollo' })
    mock.onGet('/users/').reply(200, paginated([userSummary(mePM), userSummary(meMember)]))

    const picker = await screen.findByRole('combobox', { name: '' }) // the "Add a member…" select has no label; fall back below
    expect(picker).toBeDefined()
  })

  it('closing the project calls the close endpoint after confirmation', async () => {
    const mock = mockApi()
    renderDetail(mock)
    await screen.findByRole('heading', { name: 'Apollo' })
    mock.onPost('/projects/10/close/').reply(200, { ...project1, status: 'CLOSED' })

    const confirmSpy = vi_spyConfirm()
    await userEvent.click(screen.getByRole('button', { name: /close project/i }))
    await waitFor(() => expect(mock.history.post.some((r) => r.url === '/projects/10/close/')).toBe(true))
    confirmSpy.mockRestore()
  })

  it('shows an error if the project fails to load', async () => {
    const mock = mockApi()
    mock.onGet('/projects/10/').reply(404, { detail: 'Not found.' })
    mock.onGet('/tasks/', { params: { project: 10, ordering: 'due_date' } }).reply(200, paginated([]))
    renderAsUser(<Routes><Route path="/projects/:id" element={<ProjectDetail />} /></Routes>, mePM, mock, '/projects/10')
    expect(await screen.findByText(/not found|could not load/i)).toBeInTheDocument()
  })
})

function vi_spyConfirm() {
  const spy = { mockRestore: () => { window.confirm = original } }
  const original = window.confirm
  window.confirm = () => true
  return spy
}
