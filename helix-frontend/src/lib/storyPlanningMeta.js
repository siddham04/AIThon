const PRI_ORDER = { P1: 1, P2: 2, P3: 3, P4: 4 }

export function storyPlanningStorageKey(projectId) {
  return `helix_story_plan_${projectId}`
}

export function loadStoryPlanningMap(projectId) {
  if (!projectId) return {}
  try {
    const raw = localStorage.getItem(storyPlanningStorageKey(projectId))
    if (!raw) return {}
    const o = JSON.parse(raw)
    return o && typeof o === 'object' ? o : {}
  } catch {
    return {}
  }
}

export function saveStoryPlanningMap(projectId, map) {
  if (!projectId) return
  try {
    localStorage.setItem(storyPlanningStorageKey(projectId), JSON.stringify(map))
  } catch {
    /* ignore quota */
  }
}

export function defaultStoryMeta() {
  return { reach: 3, impact: 3, confidence: 80, effort: 3, priority: 'P3' }
}

/** RICE-style score: (R × I × confidence%) / E */
export function riceScore(meta) {
  const m = { ...defaultStoryMeta(), ...meta }
  const r = Math.max(1, Math.min(5, Number(m.reach) || 1))
  const i = Math.max(1, Math.min(5, Number(m.impact) || 1))
  const e = Math.max(1, Math.min(5, Number(m.effort) || 1))
  const c = Math.max(10, Math.min(100, Number(m.confidence) || 80)) / 100
  return (r * i * c) / e
}

export function sortStoriesForPlanning(stories, metaById, sortMode) {
  const list = [...(stories || [])]
  if (sortMode === 'rice') {
    list.sort((a, b) => {
      const sa = riceScore(metaById[a.id] || {})
      const sb = riceScore(metaById[b.id] || {})
      return sb - sa
    })
    return list
  }
  if (sortMode === 'priority') {
    list.sort((a, b) => {
      const pa = PRI_ORDER[(metaById[a.id] || {}).priority] ?? 99
      const pb = PRI_ORDER[(metaById[b.id] || {}).priority] ?? 99
      if (pa !== pb) return pa - pb
      return riceScore(metaById[b.id] || {}) - riceScore(metaById[a.id] || {})
    })
    return list
  }
  return list
}
