const KEY = 'helix_pinned_project_ids'

export function readPinnedProjectIds() {
  try {
    const raw = localStorage.getItem(KEY)
    const arr = JSON.parse(raw || '[]')
    return Array.isArray(arr) ? arr.filter((x) => typeof x === 'string') : []
  } catch {
    return []
  }
}

export function writePinnedProjectIds(ids) {
  try {
    localStorage.setItem(KEY, JSON.stringify(ids))
  } catch {
    /* noop */
  }
}

export function togglePinnedProjectId(id) {
  const cur = readPinnedProjectIds()
  const next = cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]
  writePinnedProjectIds(next)
  return next
}

export function sortProjectsWithPins(projects, pinnedIds) {
  const pinSet = new Set(pinnedIds)
  const pinned = []
  const rest = []
  for (const p of projects || []) {
    if (pinSet.has(p.id)) pinned.push(p)
    else rest.push(p)
  }
  const order = new Map(pinnedIds.map((id, i) => [id, i]))
  pinned.sort((a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0))
  return [...pinned, ...rest]
}
