import axios from 'axios'

import { API_BASE_URL, logApiConfig } from '@/config'
import { clearAuth, getToken } from '@/stores/auth'

export const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

logApiConfig()

function resolveRequestUrl(config: { baseURL?: string; url?: string }) {
  const base = config.baseURL ?? ''
  const path = config.url ?? ''
  if (/^https?:\/\//i.test(path)) {
    return path
  }
  const normalizedBase = base.replace(/\/+$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  if (!normalizedBase) {
    return typeof window !== 'undefined'
      ? new URL(normalizedPath, window.location.origin).href
      : normalizedPath
  }
  return `${normalizedBase}${normalizedPath}`
}

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  const method = (config.method ?? 'get').toUpperCase()
  const requestUrl = resolveRequestUrl(config)
  console.info(`[api-request] ${method} ${requestUrl}`, {
    baseURL: config.baseURL ?? '(none)',
    url: config.url,
    pageOrigin: typeof window !== 'undefined' ? window.location.origin : '(unknown)',
  })

  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAuth()
      const path = window.location.pathname
      if (path !== '/login' && path !== '/register') {
        window.location.href = `/login?redirect=${encodeURIComponent(path)}`
      }
    }
    return Promise.reject(error)
  },
)
