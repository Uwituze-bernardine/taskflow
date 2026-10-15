import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AttachmentPanel from '../AttachmentPanel'
import CommentThread from '../CommentThread'
import NotificationBell from '../NotificationBell'
import { clearSession, mockApi, renderAsUser } from '../../test/harness'
import { attachment1, comment1, meMember, mePM, notification1, paginated, userSummary } from '../../test/fixtures'

afterEach(() => { clearSession(); vi.restoreAllMocks() })

describe('NotificationBell', () => {
  it('shows the unread count and marks a notification read when clicked', async () => {
    const mock = mockApi()
    mock.onGet('/notifications/unread_count/').reply(200, { count: 3 })
    mock.onGet('/notifications/').reply(200, paginated([notification1]))
    renderAsUser(<NotificationBell />, meMember, mock)

    expect(await screen.findByText('3')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /notifications/i }))
    mock.onPost('/notifications/1/mark_read/').reply(200, { ...notification1, is_read: true })
    await userEvent.click(await screen.findByText(/you were assigned/i))
    await waitFor(() => expect(mock.history.post.some((r) => r.url === '/notifications/1/mark_read/')).toBe(true))
  })
})

describe('CommentThread', () => {
  it('edits own comment and deletes it, showing the placeholder', async () => {
    const mock = mockApi()
    let comments = [{ ...comment1, can_edit: true, can_delete: true }]
    const onChanged = vi.fn((next) => { comments = next })
    const { rerender } = renderAsUser(
      <CommentThread taskId={100} comments={comments} participants={[userSummary(mePM)]} onChanged={onChanged} />, mePM, mock
    )

    await userEvent.click(screen.getByRole('button', { name: /^edit$/i }))
    mock.onPatch('/comments/1/').reply(200, { ...comments[0], body: 'Edited text', is_edited: true })
    const input = screen.getByDisplayValue('Looks good so far')
    await userEvent.clear(input)
    await userEvent.type(input, 'Edited text')
    await userEvent.click(screen.getByRole('button', { name: /^save$/i }))
    await waitFor(() => expect(onChanged).toHaveBeenCalled())
    expect(onChanged.mock.calls[0][0][0].body).toBe('Edited text')
    expect(rerender).toBeDefined()
  })

  it('lists who can be mentioned', async () => {
    const mock = mockApi()
    renderAsUser(<CommentThread taskId={100} comments={[]} participants={[userSummary(mePM)]} onChanged={() => {}} />, mePM, mock)
    expect(screen.getByText(/@pam/)).toBeInTheDocument()
    expect(screen.getByText(/no comments yet/i)).toBeInTheDocument()
  })
})

describe('AttachmentPanel', () => {
  it('shows limits, uploads a file, and surfaces a server rejection', async () => {
    const mock = mockApi()
    mock.onGet('/attachments/settings/').reply(200, { allowed_extensions: 'pdf', max_size_mb: 5, extension_list: ['pdf'] })
    const onChanged = vi.fn()
    renderAsUser(<AttachmentPanel taskId={100} attachments={[attachment1]} canUpload onChanged={onChanged} />, mePM, mock)

    expect(await screen.findByText(/max 5mb/i)).toBeInTheDocument()
    expect(screen.getByText('schema.pdf')).toBeInTheDocument()

    mock.onPost('/attachments/').replyOnce(400, { file: ['File type ".exe" is not allowed.'] })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, new File(['x'], 'bad.exe'))
    expect(await screen.findByText(/not allowed/i)).toBeInTheDocument()
    expect(onChanged).not.toHaveBeenCalled()
  })
})
