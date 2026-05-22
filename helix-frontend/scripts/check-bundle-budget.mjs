/**
 * CI bundle budget — fails if dist exceeds HELIX_BUNDLE_BUDGET_KB (default 2800).
 */
import fs from 'node:fs'
import path from 'node:path'

const DIST = path.resolve('dist')
const BUDGET_KB = Number(process.env.HELIX_BUNDLE_BUDGET_KB || 2800)

function dirSizeBytes(dir) {
  let total = 0
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name)
    if (ent.isDirectory()) total += dirSizeBytes(p)
    else total += fs.statSync(p).size
  }
  return total
}

if (!fs.existsSync(DIST)) {
  console.error('dist/ missing — run npm run build first')
  process.exit(1)
}

const bytes = dirSizeBytes(DIST)
const kb = Math.round(bytes / 1024)
console.log(`Bundle size: ${kb} KB (budget ${BUDGET_KB} KB)`)

const assetsDir = path.join(DIST, 'assets')
if (fs.existsSync(assetsDir)) {
  const chunks = fs
    .readdirSync(assetsDir)
    .filter((f) => f.endsWith('.js'))
    .map((f) => ({ name: f, kb: Math.round(fs.statSync(path.join(assetsDir, f)).size / 1024) }))
    .sort((a, b) => b.kb - a.kb)
  console.log('Top JS chunks:', chunks.slice(0, 8))
}

if (kb > BUDGET_KB) {
  console.error(`FAIL: bundle ${kb} KB exceeds budget ${BUDGET_KB} KB`)
  process.exit(1)
}
console.log('PASS: within bundle budget')
