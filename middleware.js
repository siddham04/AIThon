/**
 * Vercel Edge Middleware — proxies same-origin /api/* to your FastAPI host.
 *
 * In Vercel → Settings → Environment Variables (Production + Preview):
 *   HELIX_BACKEND_ORIGIN = https://your-service.onrender.com
 *   (no trailing slash; no /api suffix)
 *
 * Leave VITE_API_BASE unset to use this proxy. Set VITE_API_BASE to call the API
 * directly from the browser (recommended for long SSE streams — see docs/VERCEL.md).
 *
 * Edge runtime caveats:
 *   - Streaming bodies are forwarded (Response is returned without buffering).
 *   - Hop-by-hop headers (host, connection, content-length, transfer-encoding) are stripped.
 *   - Cold starts on free Render may take 30–60s; client should retry with timeout.
 */

// Default origin: helix-frontend/vercel-default-backend.mjs (keep URL in sync)
const DEFAULT_BACKEND_ORIGIN = 'https://helix-demo.onrender.com'

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
  const backendOrig =
    (process.env.HELIX_BACKEND_ORIGIN || '').trim().replace(/\/$/, '') ||
    DEFAULT_BACKEND_ORIGIN

  const u = new URL(request.url)
  const dest = `${backendOrig}${u.pathname}${u.search}`

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
    // Edge runtime requires duplex: 'half' when forwarding a streaming body.
    init.duplex = 'half'
  }

  try {
    const upstream = await fetch(dest, init)
    // Pass the body through unbuffered so SSE/long-poll responses stream.
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
