import axios from 'axios'
import { clearAuthStorage, readAuthToken } from '../lib/authTokenStorage'

const baseURL =
  import.meta.env.VITE_API_BASE?.replace(/\/$/, '') ||
  `${window.location.origin}/api`

export const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000,
})

api.interceptors.request.use((config) => {
  const token = readAuthToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status
    if (status === 401) {
      clearAuthStorage()
      if (!window.location.pathname.startsWith('/login')) {
        window.location.assign('/login')
      }
    }
    return Promise.reject(err)
  },
)
