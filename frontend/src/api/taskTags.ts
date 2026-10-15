import { client } from './client'
import type { TaskTag } from '../types'

// FR-094: the administrator-curated tag registry (task.tags itself stays freeform).
export async function listTaskTags(): Promise<TaskTag[]> {
  const { data } = await client.get('/tasks/tags/')
  return data
}

export async function createTaskTag(name: string): Promise<TaskTag> {
  const { data } = await client.post('/tasks/tags/', { name })
  return data
}

export async function deleteTaskTag(id: number): Promise<void> {
  await client.delete(`/tasks/tags/${id}/`)
}
