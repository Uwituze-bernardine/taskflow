import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import Projects from '../Projects'
import { mockApi, renderAsUser, clearSession } from '../../test/harness'
import { meMember, mePM, paginated, project1 } from '../../test/fixtures'

afterEach(() => { clearSession() })

describe('Projects page', () => {
  it('lists projects and shows the New project button for a manager', async () => {
    const mock = mockApi()
    mock.onGet('/projects/').reply(200, paginated([project1]))
    renderAsUser(<Routes><Route path="/" element={<Projects />} /></Routes>, mePM, mock)

    expect(await screen.findByText('Apollo')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /new project/i })).toBeInTheDocument()
  })

  it('hides the New project button for a team member', async () => {
    const mock = mockApi()
    mock.onGet('/projects/').reply(200, paginated([project1]))
    renderAsUser(<Routes><Route path="/" element={<Projects />} /></Routes>, meMember, mock)

    await screen.findByText('Apollo')
    expect(screen.queryByRole('button', { name: /new project/i })).not.toBeInTheDocument()
  })

  it('shows an empty state with no projects', async () => {
    const mock = mockApi()
    mock.onGet('/projects/').reply(200, paginated([]))
    renderAsUser(<Routes><Route path="/" element={<Projects />} /></Routes>, meMember, mock)
    expect(await screen.findByText(/not part of any project/i)).toBeInTheDocument()
  })

  it('shows a server error if the list fails to load', async () => {
    const mock = mockApi()
    mock.onGet('/projects/').reply(500, { detail: 'Server error.' })
    renderAsUser(<Routes><Route path="/" element={<Projects />} /></Routes>, mePM, mock)
    expect(await screen.findByText(/server error/i)).toBeInTheDocument()
  })

  it('creates a new project through the inline form', async () => {
    const mock = mockApi()
    mock.onGet('/projects/').reply(200, paginated([]))
    renderAsUser(<Routes><Route path="/" element={<Projects />} /></Routes>, mePM, mock)
    await screen.findByText(/not part of any project/i)

    await userEvent.click(screen.getByRole('button', { name: /new project/i }))
    mock.onPost('/projects/').reply(201, { ...project1, id: 11, name: 'Gemini' })

    await userEvent.type(screen.getByLabelText(/project name/i), 'Gemini')
    await userEvent.click(screen.getByRole('button', { name: /create project/i }))

    await waitFor(() => expect(mock.history.post.some((r) => r.url === '/projects/')).toBe(true))
  })
})
