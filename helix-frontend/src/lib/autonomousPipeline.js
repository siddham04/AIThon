/**
 * Canonical autonomous SDLC workflow — single source of truth for product UX.
 * Autonomous by default: AI performs every SDLC step. Humans upload, review checklist, Approve & Export.
 */

/** User-visible pipeline (display order) */
export const AUTONOMOUS_PIPELINE = [
  {
    id: 'upload',
    label: 'Upload Requirement',
    short: 'Upload',
    icon: '📄',
    actor: 'You',
    autonomous: false,
    demoSteps: ['ingest'],
    autoMs: 1200,
  },
  {
    id: 'launch',
    label: 'Launch AI Team',
    short: 'Launch',
    icon: '⎈',
    actor: 'Helix',
    autonomous: true,
    demoSteps: ['boot'],
    autoMs: 800,
  },
  {
    id: 'pm',
    label: 'PM Agent Analysis',
    short: 'PM',
    icon: '◆',
    actor: 'PM Agent',
    autonomous: true,
    demoSteps: ['quality', 'review', 'ambiguity'],
    autoMs: 3800,
  },
  {
    id: 'architecture',
    label: 'Architecture Generation',
    short: 'Architecture',
    icon: '◇',
    actor: 'Architect Agent',
    autonomous: true,
    demoSteps: ['architecture', 'apis'],
    autoMs: 3400,
  },
  {
    id: 'stories',
    label: 'User Stories',
    short: 'Stories',
    icon: '✦',
    actor: 'PM Agent',
    autonomous: true,
    demoSteps: ['stories'],
    autoMs: 3200,
  },
  {
    id: 'sprint',
    label: 'Sprint Planning',
    short: 'Sprint',
    icon: '▦',
    actor: 'Scrum Agent',
    autonomous: true,
    demoSteps: ['effort_sprint'],
    autoMs: 3000,
  },
  {
    id: 'tests',
    label: 'Test Case Generation',
    short: 'Tests',
    icon: '✓',
    actor: 'QA Agent',
    autonomous: true,
    demoSteps: ['tests'],
    autoMs: 3000,
  },
  {
    id: 'risk',
    label: 'Risk Analysis',
    short: 'Risk',
    icon: '⚠',
    actor: 'Scrum Agent',
    autonomous: true,
    demoSteps: ['jira'],
    autoMs: 3200,
  },
  {
    id: 'package',
    label: 'Delivery Package',
    short: 'Package',
    icon: '📦',
    actor: 'Helix',
    autonomous: true,
    demoSteps: ['readiness', 'complete'],
    autoMs: 4000,
  },
  {
    id: 'export',
    label: 'Approve & Export',
    short: 'Export',
    icon: '↗',
    actor: 'You approve',
    autonomous: false,
    demoSteps: [],
    autoMs: 0,
  },
]

/** Steps that run during SSE (excludes export) */
export const PIPELINE_AUTONOMOUS_STEPS = AUTONOMOUS_PIPELINE.filter(
  (s) => s.demoSteps.length > 0 || s.id === 'launch',
)

const STEP_TO_PIPELINE = Object.fromEntries(
  AUTONOMOUS_PIPELINE.flatMap((s) => s.demoSteps.map((d) => [d, s.id])),
)

export function pipelineStepForDemoStep(stepId) {
  if (!stepId) return null
  const pid = STEP_TO_PIPELINE[stepId]
  if (!pid) return null
  return AUTONOMOUS_PIPELINE.find((s) => s.id === pid) ?? null
}

export function pipelineIdForDemoStep(stepId) {
  return STEP_TO_PIPELINE[stepId] ?? null
}

/**
 * @deprecated Display-only timer (~30s). Mission Control uses real SSE — do not use for live demo.
 */
export function runPipelineAutoPlay({ onStep, signal }) {
  const timers = []
  let t = 300
  for (const step of AUTONOMOUS_PIPELINE) {
    if (step.id === 'export' || !step.autoMs) continue
    t += step.autoMs
    const id = setTimeout(() => {
      if (signal?.aborted) return
      onStep(step.id)
    }, t)
    timers.push(id)
  }
  return () => timers.forEach(clearTimeout)
}
