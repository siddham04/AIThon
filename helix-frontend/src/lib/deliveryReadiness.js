/** Screen 10 — Delivery Readiness Center (fallback when API unavailable). */

export const DEMO_READINESS_CENTER = {
  checklist: [
    { key: 'requirements', label: 'Requirements', complete: true, detail: 'Complete' },
    { key: 'stories', label: 'Stories', complete: true, detail: 'Complete' },
    { key: 'tasks', label: 'Tasks', complete: true, detail: 'Complete' },
    { key: 'tests', label: 'Test Cases', complete: true, detail: 'Complete' },
    { key: 'risks', label: 'Risks Reviewed', complete: true, detail: 'Complete' },
    { key: 'architecture', label: 'Architecture Generated', complete: true, detail: 'Complete' },
  ],
  readiness: 100,
  status_label: 'PROJECT READY',
  headline: 'All six SDLC gates passed — safe to demo handoff to engineering.',
  blocking_items: [],
}

export function allGatesComplete(center) {
  return (center?.checklist || []).every((c) => c.complete)
}
