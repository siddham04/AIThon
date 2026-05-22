/**
 * Vercel Edge Middleware — proxies same-origin /api/* to your FastAPI host.
 *
 * In Vercel → Settings → Environment Variables (Production + Preview):
 *   HELIX_BACKEND_ORIGIN = https://your-service.onrender.com
 *   (no trailing slash; no /api suffix)
 *
 * Leave VITE_API_BASE unset so the SPA uses /api on this deployment (see helix-frontend/src/api/client.js).
 *
 * Limits: long-lived WebSocket/SSE through this proxy may be unreliable; for full pipeline demos
 * prefer Render all-in-one (DEMO_HOSTING.md) or set VITE_API_BASE to the API origin for wss://.
 */

export const config = {
  matcher: '/api/:path*',
}

// Default origin: helix-frontend/vercel-default-backend.mjs (keep URL in sync)
const DEFAULT_BACKEND_ORIGIN = 'https://helix-demo.onrender.com'

export default async function middleware(request) {
  const backendOrig =
    (process.env.HELIX_BACKEND_ORIGIN || '').trim() || DEFAULT_BACKEND_ORIGIN

  const u = new URL(request.url)
  const dest = `${backendOrig.replace(/\/$/, '')}${u.pathname}${u.search}`

  const headers = new Headers()
  for (const [k, v] of request.headers.entries()) {
    const lk = k.toLowerCase()
    if (lk === 'host' || lk === 'connection' || lk === 'content-length') continue
    headers.set(k, v)
  }

  const init = {
    method: request.method,
    headers,
    redirect: 'manual',
  }
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = request.body
  }

  try {
    return await fetch(dest, init)
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    return Response.json({ detail: `API proxy error: ${msg}` }, { status: 502 })
  }
}
