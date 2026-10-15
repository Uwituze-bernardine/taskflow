import { client } from './client'
import type { AuditLogEntry, Paginated } from '../types'

export interface AuditLogFilters {
  model_name?: string
  object_id?: string
  actor?: number
  page?: number
}

// FR-096: administrators view the system audit log.
export async function listAuditLog(filters: AuditLogFilters = {}): Promise<Paginated<AuditLogEntry>> {
  const { data } = await client.get('/audit/', { params: filters })
  return data
}
