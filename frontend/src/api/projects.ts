import { client } from './client'
import type { Paginated, Project, ProjectStatus } from '../types'

export interface ProjectFilters {
  status?: ProjectStatus
  include_archived?: boolean
  page?: number
}

export interface ProjectInput {
  name: string
  description?: string
  manager?: number
  status?: ProjectStatus
  start_date?: string | null
  end_date?: string | null
}

export async function listProjects(filters: ProjectFilters = {}): Promise<Paginated<Project>> {
  const { data } = await client.get('/projects/', { params: filters })
  return data
}

/** Every project the current user can see (follows pagination), for pickers. */
export async function listAllProjects(): Promise<Project[]> {
  const all: Project[] = []
  for (let page = 1; page <= 50; page++) {
    const data = await listProjects({ page })
    all.push(...data.results)
    if (!data.next) break
  }
  return all
}

export async function getProject(id: number): Promise<Project> {
  const { data } = await client.get(`/projects/${id}/`)
  return data
}

export async function createProject(payload: ProjectInput): Promise<Project> {
  const { data } = await client.post('/projects/', payload)
  return data
}

export async function updateProject(id: number, payload: Partial<ProjectInput>): Promise<Project> {
  const { data } = await client.patch(`/projects/${id}/`, payload)
  return data
}

export async function archiveProject(id: number): Promise<Project> {
  const { data } = await client.post(`/projects/${id}/archive/`)
  return data
}

export async function closeProject(id: number): Promise<Project> {
  const { data } = await client.post(`/projects/${id}/close/`)
  return data
}

export async function reopenProject(id: number): Promise<Project> {
  const { data } = await client.post(`/projects/${id}/reopen/`)
  return data
}

export async function addProjectMember(id: number, userId: number): Promise<Project> {
  const { data } = await client.post(`/projects/${id}/members/`, { user_id: userId })
  return data
}

export async function removeProjectMember(id: number, userId: number): Promise<Project> {
  const { data } = await client.delete(`/projects/${id}/members/${userId}/`)
  return data
}
