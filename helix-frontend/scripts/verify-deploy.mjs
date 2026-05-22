/**
 * Smoke-check API before/after deploy. Usage:
 *   node scripts/verify-deploy.mjs
 *   API_BASE=https://helix-demo.onrender.com/api node scripts/verify-deploy.mjs
 */
const base = (process.env.API_BASE || 'https://helix-demo.onrender.com/api').replace(/\/$/, '')

async function req(path, init) {
  const url = `${base}${path}`
  const res = await fetch(url, { ...init, signal: AbortSignal.timeout(120000) })
  const text = await res.text()
  let json = null
  try {
    json = JSON.parse(text)
  } catch {
    /* noop */
  }
  return { url, status: res.status, json, text: text.slice(0, 200) }
}

let failed = 0

const health = await req('/health')
console.log('GET /health', health.status, health.json?.status ?? health.text)
if (health.status !== 200) failed++

const guest = await req('/auth/guest', { method: 'POST', headers: { 'Content-Type': 'application/json' } })
console.log('POST /auth/guest', guest.status, guest.json?.access_token ? 'token ok' : guest.text)
if (guest.status !== 200) failed++

process.exit(failed ? 1 : 0)
