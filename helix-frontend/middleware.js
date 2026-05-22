/**
 * Vercel Edge Middleware — same logic as repo-root `middleware.js`.
 * Present here so deployments with Vercel **Root Directory = helix-frontend** still proxy /api.
 * Keep in sync with `../middleware.js` when editing.
 */

import { resolveBackendOrigin } from './vercel-default-backend.mjs'

export const config = {
  matcher: '/api/:path*',
}

export default async function middleware(request) {
  const backendOrig = resolveBackendOrigin()

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
