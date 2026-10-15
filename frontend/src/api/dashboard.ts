import { client } from './client'
import type { DashboardData } from '../types'

// FR-071: a single call for everything the logged-in user's dashboard needs.
export async function getDashboard(): Promise<DashboardData> {
  const { data } = await client.get('/dashboard/')
  return data
}
