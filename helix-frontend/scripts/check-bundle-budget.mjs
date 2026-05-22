/**
 * CI bundle budget — measures initial-load assets (excludes lazy route chunks).
 *
 * Lazy (on-demand): vendor-mermaid, vendor-three, katex (diagram + 3D hero).
 * Set HELIX_BUNDLE_BUDGET_KB (default 2800) for initial load.
 * Set HELIX_BUNDLE_TOTAL_KB (optional) to cap entire dist/ size.
 */
import fs from 'node:fs'
import path from 'node:path'

const DIST = path.resolve('dist')
const BUDGET_KB = Number(process.env.HELIX_BUNDLE_BUDGET_KB || 2800)
const TOTAL_CAP_KB = Number(process.env.HELIX_BUNDLE_TOTAL_KB || 0)

/** Chunks loaded only when opening workspace diagrams or 3D ambient. */
const LAZY_JS = /vendor-mermaid|vendor-three|^katex-/i

function fileKb(filePath) {
  return Math.round(fs.statSync(filePath).size / 1024)
}

function sumDistBytes(filterFn) {
  let total = 0
  const walk = (dir) => {
    for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, ent.name)
      if (ent.isDirectory()) walk(p)
      else if (!filterFn || filterFn(p, ent.name)) total += fs.statSync(p).size
    }
  }
  walk(DIST)
  return total
}

if (!fs.existsSync(DIST)) {
  console.error('dist/ missing — run npm run build first')
  process.exit(1)
}

const totalKb = Math.round(sumDistBytes() / 1024)

const initialKb = Math.round(
  sumDistBytes((filePath, name) => {
    if (name.endsWith('.js') && LAZY_JS.test(name)) return false
    return true
  }) / 1024,
)

const assetsDir = path.join(DIST, 'assets')
if (fs.existsSync(assetsDir)) {
  const chunks = fs
    .readdirSync(assetsDir)
    .filter((f) => f.endsWith('.js'))
    .map((f) => ({ name: f, kb: fileKb(path.join(assetsDir, f)), lazy: LAZY_JS.test(f) }))
    .sort((a, b) => b.kb - a.kb)
  console.log('Top JS chunks:', chunks.slice(0, 10).map(({ name, kb, lazy }) => ({ name, kb, lazy })))
}

console.log(`Initial load: ${initialKb} KB (budget ${BUDGET_KB} KB)`)
console.log(`Total dist:   ${totalKb} KB (lazy chunks excluded from budget)`)

if (TOTAL_CAP_KB > 0 && totalKb > TOTAL_CAP_KB) {
  console.error(`FAIL: total dist ${totalKb} KB exceeds cap ${TOTAL_CAP_KB} KB`)
  process.exit(1)
}

if (initialKb > BUDGET_KB) {
  console.error(`FAIL: initial load ${initialKb} KB exceeds budget ${BUDGET_KB} KB`)
  process.exit(1)
}

console.log('PASS: initial load within bundle budget')
