/**
 * Vercel Edge Middleware — same logic as repo-root `middleware.js`.
 * Present here so deployments with Vercel **Root Directory = helix-frontend** still proxy /api.
 * Keep in sync with `../middleware.js` when editing.
 */

import { resolveBackendOrigin } from './vercel-default-backend.mjs'

const HOP_BY_HOP = new Set([
  'host',
  'connection',
  'content-length',
  'transfer-encoding',
  'keep-alive',
  'upgrade',
  'proxy-connection',
  'te',
  'trailer',
])

export const config = {
  matcher: '/api/:path*',
}

export default async function middleware(request) {
  const backendOrig = resolveBackendOrigin()

  const u = new URL(request.url)
  const dest = `${backendOrig.replace(/\/$/, '')}${u.pathname}${u.search}`

  const headers = new Headers()
  for (const [k, v] of request.headers.entries()) {
    if (!HOP_BY_HOP.has(k.toLowerCase())) headers.set(k, v)
  }
  headers.set('x-forwarded-host', u.host)
  headers.set('x-forwarded-proto', 'https')

  const init = {
    method: request.method,
    headers,
    redirect: 'manual',
  }
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = request.body
    init.duplex = 'half'
  }

  try {
    const upstream = await fetch(dest, init)
    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: upstream.headers,
    })
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    return Response.json(
      {
        detail:
          `API proxy error: ${msg}. ` +
          'Backend may be cold-starting (free Render takes 30–60s) or HELIX_BACKEND_ORIGIN is wrong.',
        backend: backendOrig,
      },
      { status: 502 },
    )
  }
}
