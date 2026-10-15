import { client } from './client'
import type { Report } from '../types'

export interface ReportFilters {
  start?: string
  end?: string
  project?: number
}

// FR-078..082: the report summary, filterable by date range and project.
export async function getReport(filters: ReportFilters = {}): Promise<Report> {
  const { data } = await client.get('/reports/summary/', { params: filters })
  return data
}

/** FR-083: downloads the same report as a CSV file. */
export async function exportReport(filters: ReportFilters = {}): Promise<void> {
  const response = await client.get('/reports/export/', { params: filters, responseType: 'blob' })
  const match = /filename="(.+)"/.exec(response.headers['content-disposition'] ?? '')
  const filename = match?.[1] ?? 'report.csv'
  const url = window.URL.createObjectURL(response.data as Blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
