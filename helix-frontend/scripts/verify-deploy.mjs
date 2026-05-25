/**
 * Smoke-check the live Helix deployment.
 *
 * Usage:
 *   node scripts/verify-deploy.mjs
 *   API_BASE=https://helix-demo.onrender.com/api node scripts/verify-deploy.mjs
 *   VERCEL_URL=https://your-app.vercel.app node scripts/verify-deploy.mjs
 *
 * When VERCEL_URL is provided we also verify same-origin /api proxying.
 */
const apiBase = (process.env.API_BASE || 'https://helix-demo.onrender.com/api').replace(/\/$/, '')
const vercelUrl = (process.env.VERCEL_URL || '').replace(/\/$/, '')

async function req(base, path, init) {
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
function check(label, ok, hint = '') {
  console.log(`${ok ? '✓' : '✗'} ${label}${hint ? ` — ${hint}` : ''}`)
  if (!ok) failed++
}

console.log(`Checking API at: ${apiBase}`)

const health = await req(apiBase, '/health')
check(`GET /health (${health.status})`, health.status === 200 && health.json?.status === 'ok')
check(
  '/health exposes demo metadata',
  Boolean(health.json && 'demo_fast' in health.json && 'showcase_project_id' in health.json),
  'used by the frontend before login',
)

const guest = await req(apiBase, '/auth/guest', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
})
check(
  `POST /auth/guest (${guest.status})`,
  guest.status === 200 && typeof guest.json?.access_token === 'string',
  guest.json?.detail || '',
)

if (guest.json?.access_token) {
  const tok = guest.json.access_token
  const me = await req(apiBase, '/projects', { headers: { Authorization: `Bearer ${tok}` } })
  check(
    `GET /projects with guest token (${me.status})`,
    me.status === 200 && Array.isArray(me.json),
  )
}

const login = await req(apiBase, '/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'demo@demo.com', password: 'demo123' }),
})
check(
  `POST /auth/login demo@demo.com (${login.status})`,
  login.status === 200 && typeof login.json?.access_token === 'string',
  login.json?.detail || '',
)

if (vercelUrl) {
  console.log(`\nChecking same-origin proxy on: ${vercelUrl}`)
  const proxy = await req(vercelUrl, '/api/health')
  check(
    `GET ${vercelUrl}/api/health (${proxy.status})`,
    proxy.status === 200 && proxy.json?.status === 'ok',
    proxy.text,
  )
}

process.exit(failed ? 1 : 0)
