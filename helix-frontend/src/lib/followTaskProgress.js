import { helixProgressWsUrl } from './helixProgressWsUrl'

/**
 * Subscribe to backend task progress over WebSocket. Calls onDone when status is done or error.
 * Returns a dispose function to close the socket early.
 */
export function followTaskProgress(taskId, { onEvent, onDone } = {}) {
  if (!taskId) return () => {}

  let finished = false
  const ws = new WebSocket(helixProgressWsUrl(taskId))

  const finish = (msg) => {
    if (finished) return
    finished = true
    try {
      ws.close()
    } catch {
      /* ignore */
    }
    onDone?.(msg)
  }

  ws.onmessage = (ev) => {
    let msg
    try {
      msg = JSON.parse(ev.data)
    } catch {
      return
    }
    onEvent?.(msg)
    const st = String(msg?.status || '')
    if (st === 'done' || st === 'error') {
      finish(msg)
    }
  }

  ws.onerror = () => {
    if (finished) return
    finish({ status: 'error', message: 'Progress stream failed', percent: 0 })
  }

  return () => {
    if (finished) return
    finished = true
    try {
      ws.close()
    } catch {
      /* ignore */
    }
  }
}
