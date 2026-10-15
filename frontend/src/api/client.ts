import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

export const client = axios.create({ baseURL: BASE_URL })

// --- token storage -----------------------------------------------------
// Kept in memory + localStorage so a page refresh doesn't force a re-login.
// Swap for httpOnly cookies server-side if stricter XSS protection is needed.

export const tokenStore = {
  getAccess: () => localStorage.getItem('tf_access'),
  getRefresh: () => localStorage.getItem('tf_refresh'),
  set: (access: string, refresh: string) => {
    localStorage.setItem('tf_access', access)
    localStorage.setItem('tf_refresh', refresh)
  },
  clear: () => {
    localStorage.removeItem('tf_access')
    localStorage.removeItem('tf_refresh')
  },
}

client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStore.getAccess()
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshing: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStore.getRefresh()
  if (!refresh) return null
  try {
    const { data } = await axios.post(`${BASE_URL}/auth/refresh/`, { refresh })
    // The backend rotates refresh tokens: always keep the newest one.
    tokenStore.set(data.access, data.refresh ?? refresh)
    return data.access as string
  } catch {
    tokenStore.clear()
    return null
  }
}

client.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    // A 401 from the login/register endpoints means "wrong credentials", not "session expired".
    const isAuthCall = /\/auth\/(login|register)\//.test(original?.url ?? '')
    if (error.response?.status === 401 && original && !original._retry && !isAuthCall) {
      original._retry = true
      refreshing = refreshing ?? refreshAccessToken()
      const newAccess = await refreshing
      refreshing = null
      if (newAccess) {
        original.headers = original.headers ?? {}
        original.headers.Authorization = `Bearer ${newAccess}`
        return client(original)
      }
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
