/**
 * Vercel build: map HELIX_BACKEND_ORIGIN → VITE_API_BASE so auth hits Render directly.
 * Also keep edge middleware.js for same-origin /api when VITE_API_BASE is unset.
 */
import fs from 'node:fs'
import path from 'node:path'
import { resolveBackendOrigin } from '../vercel-default-backend.mjs'

const origin = resolveBackendOrigin()
const explicit = (process.env.VITE_API_BASE || '').trim().replace(/\/$/, '')

let viteApiBase = explicit
if (!viteApiBase && origin) {
  viteApiBase = `${origin}/api`
}

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
