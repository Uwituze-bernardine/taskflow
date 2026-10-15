import { client } from './client'
import type { CustomTaskStatus, TaskStatus } from '../types'

export interface CustomStatusInput {
  name: string
  category: TaskStatus
  order?: number
  is_active?: boolean
}

// FR-035: everyone can read the configured statuses; only administrators can write.
export async function listCustomStatuses(): Promise<CustomTaskStatus[]> {
  const { data } = await client.get('/tasks/statuses/')
  return data
}

export async function createCustomStatus(payload: CustomStatusInput): Promise<CustomTaskStatus> {
  const { data } = await client.post('/tasks/statuses/', payload)
  return data
}

export async function updateCustomStatus(id: number, payload: Partial<CustomStatusInput>): Promise<CustomTaskStatus> {
  const { data } = await client.patch(`/tasks/statuses/${id}/`, payload)
  return data
}

export async function deleteCustomStatus(id: number): Promise<void> {
  await client.delete(`/tasks/statuses/${id}/`)
}
