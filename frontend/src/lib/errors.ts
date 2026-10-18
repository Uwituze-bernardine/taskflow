import axios from 'axios'

/**
 * Turns a Django REST Framework error response into one readable string.
 * DRF returns shapes like { field: ["msg"] }, { detail: "msg" } or { non_field_errors: ["msg"] }.
 */
export function getErrorMessage(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (err instanceof Error && !axios.isAxiosError(err)) return err.message || fallback
  if (!axios.isAxiosError(err) || !err.response) {
    return axios.isAxiosError(err) ? 'Cannot reach the server. Is the backend running?' : fallback
  }
  const data = err.response.data
  if (typeof data === 'string') return fallback
  if (data && typeof data === 'object') {
    const parts: string[] = []
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      const text = Array.isArray(value) ? value.join(' ') : String(value)
      parts.push(key === 'detail' || key === 'non_field_errors' ? text : `${key.replace('_', ' ')}: ${text}`)
    }
    if (parts.length) return parts.join(' ')
  }
  return fallback
}
