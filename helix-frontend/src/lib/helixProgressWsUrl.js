/**
 * WebSocket URL for long-running task progress (matches FastAPI `/api/ws/progress/{task_id}`).
 */
export function helixProgressWsUrl(taskId) {
  const raw = import.meta.env.VITE_API_BASE?.replace(/\/$/, '')
  if (raw && /^https?:\/\//i.test(raw)) {
    const u = new URL(raw)
    u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:'
    let basePath = u.pathname.replace(/\/$/, '')
    if (!basePath || basePath === '/') basePath = '/api'
    u.pathname = `${basePath}/ws/progress/${encodeURIComponent(taskId)}`
    u.search = ''
    u.hash = ''
    return u.toString()
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/api/ws/progress/${encodeURIComponent(taskId)}`
}
