import { formatApiError } from './formatApiError'

/** Ping API (Render cold start can take 30–60s on free tier). */
export async function checkApiHealth(api, { timeoutMs = 90000 } = {}) {
  try {
    const { data } = await api.get('/health', { timeout: timeoutMs })
    return { ok: true, data }
  } catch (ex) {
    return { ok: false, message: formatApiError(ex) }
  }
}
