import { client } from './client'
import type { CustomPriority, Priority } from '../types'

export interface CustomPriorityInput {
  name: string
  category: Priority
  order?: number
  is_active?: boolean
}

// FR-093: everyone can read the configured priorities; only administrators can write.
export async function listCustomPriorities(): Promise<CustomPriority[]> {
  const { data } = await client.get('/tasks/priorities/')
  return data
}

export async function createCustomPriority(payload: CustomPriorityInput): Promise<CustomPriority> {
  const { data } = await client.post('/tasks/priorities/', payload)
  return data
}

export async function updateCustomPriority(id: number, payload: Partial<CustomPriorityInput>): Promise<CustomPriority> {
  const { data } = await client.patch(`/tasks/priorities/${id}/`, payload)
  return data
}

export async function deleteCustomPriority(id: number): Promise<void> {
  await client.delete(`/tasks/priorities/${id}/`)
}
