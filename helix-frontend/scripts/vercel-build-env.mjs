/**
 * Vercel build: bake VITE_API_BASE from HELIX_BACKEND_ORIGIN so auth + judge-demo SSE
 * hit Render directly (avoids edge proxy timeouts). Same-origin /api proxy remains fallback
 * when VITE_API_BASE is unset (local preview without env).
 */
import fs from 'node:fs'
import path from 'node:path'
import { resolveBackendOrigin } from '../vercel-default-backend.mjs'

const explicit = (process.env.VITE_API_BASE || '').trim().replace(/\/$/, '')
const origin = resolveBackendOrigin()
const onVercel = process.env.VERCEL === '1'

let viteApiBase = explicit
if (!viteApiBase && origin && (onVercel || process.env.HELIX_BACKEND_ORIGIN)) {
  viteApiBase = `${origin}/api`
}

const out = path.join(process.cwd(), '.env.production.local')
const lines = []
if (viteApiBase) lines.push(`VITE_API_BASE=${viteApiBase}`)
if (onVercel || process.env.HELIX_BACKEND_ORIGIN) {
  lines.push('VITE_HELIX_DEMO_FAST=true')
}

if (lines.length) {
  fs.writeFileSync(out, `${lines.join('\n')}\n`, 'utf8')
  console.log(`[vercel-build] wrote ${out}:`, lines.join(', '))
} else {
  try {
    fs.unlinkSync(out)
  } catch {
    /* noop */
  }
  console.log('[vercel-build] local build — VITE_API_BASE unset (use Vite /api proxy)')
}
