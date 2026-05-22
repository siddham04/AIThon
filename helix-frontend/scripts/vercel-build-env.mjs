/**
 * Vercel build: only set VITE_API_BASE when explicitly provided (Path B).
 * Default (Path A): leave unset so the SPA calls same-origin /api on your existing
 * *.vercel.app URL; edge middleware.js proxies to HELIX_BACKEND_ORIGIN.
 */
import fs from 'node:fs'
import path from 'node:path'

const viteApiBase = (process.env.VITE_API_BASE || '').trim().replace(/\/$/, '')

const out = path.join(process.cwd(), '.env.production.local')
if (viteApiBase) {
  fs.writeFileSync(out, `VITE_API_BASE=${viteApiBase}\n`, 'utf8')
  console.log(`[vercel-build] VITE_API_BASE=${viteApiBase}`)
} else {
  try {
    fs.unlinkSync(out)
  } catch {
    /* noop */
  }
  console.log(
    '[vercel-build] VITE_API_BASE unset — browser uses /api on Vercel host (set HELIX_BACKEND_ORIGIN for middleware + rebuild)',
  )
}
