import { client } from './client'
import type { Attachment, AttachmentSettings, Paginated } from '../types'

// FR-049..FR-053: files attached to a task.

export async function listAttachments(taskId: number): Promise<Attachment[]> {
  const { data } = await client.get<Paginated<Attachment> | Attachment[]>('/attachments/', { params: { task: taskId } })
  return Array.isArray(data) ? data : data.results
}

export async function uploadAttachment(taskId: number, file: File): Promise<Attachment> {
  const form = new FormData()
  form.append('task', String(taskId))
  form.append('file', file)
  const { data } = await client.post('/attachments/', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  return data
}

export async function deleteAttachment(id: number): Promise<void> {
  await client.delete(`/attachments/${id}/`)
}

/** Streams the file through an authenticated request and triggers a browser save-as. */
export async function downloadAttachment(id: number, filename: string): Promise<void> {
  const response = await client.get(`/attachments/${id}/download/`, { responseType: 'blob' })
  const url = window.URL.createObjectURL(response.data as Blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function getAttachmentSettings(): Promise<AttachmentSettings> {
  const { data } = await client.get('/attachments/settings/')
  return data
}

/** FR-052: administrators configure the allowed file types and max size. */
export async function updateAttachmentSettings(
  patch: Partial<Pick<AttachmentSettings, 'allowed_extensions' | 'max_size_mb'>>
): Promise<AttachmentSettings> {
  const { data } = await client.patch('/attachments/settings/', patch)
  return data
}
