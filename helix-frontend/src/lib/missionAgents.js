/**
 * Maps backend demo SSE → autonomous AI team (PM / Architect / QA / Scrum).
 * Aligns with AUTONOMOUS_PIPELINE narrative.
 */

import { pipelineIdForDemoStep } from './autonomousPipeline'

export const MISSION_AGENTS = [
  { id: 'pm', label: 'PM Agent', short: 'PM', glyph: '◆' },
  { id: 'architect', label: 'Architect Agent', short: 'Architect', glyph: '◇' },
  { id: 'qa', label: 'QA Agent', short: 'QA', glyph: '◎' },
  { id: 'scrum', label: 'Scrum Agent', short: 'Scrum', glyph: '▦' },
]

export const AGENT_ORDER = MISSION_AGENTS.map((a) => a.id)

/** Backend step → owning agent */
const STEP_AGENT = {
  ingest: 'pm',
  quality: 'pm',
  review: 'pm',
  ambiguity: 'pm',
  stories: 'pm',
  architecture: 'architect',
  apis: 'architect',
  tests: 'qa',
  effort_sprint: 'scrum',
  jira: 'scrum',
  readiness: 'scrum',
  complete: 'scrum',
}

export const AGENT_STEPS = {
  pm: ['ingest', 'quality', 'review', 'ambiguity', 'stories'],
  architect: ['architecture', 'apis'],
  qa: ['tests'],
  scrum: ['effort_sprint', 'jira', 'readiness'],
}

export const STEP_TO_AGENT = { ...STEP_AGENT }

export const STEP_LOG = {
  ingest: 'Requirement uploaded — team mobilizing…',
  quality: 'PM Agent: analyzing requirement quality…',
  review: 'PM Agent: multi-agent requirement review…',
  ambiguity: 'PM Agent: detecting ambiguities…',
  stories: 'PM Agent: writing user stories & tasks…',
  architecture: 'Architect Agent: generating system architecture…',
  apis: 'Architect Agent: defining API contracts…',
  tests: 'QA Agent: generating test cases…',
  effort_sprint: 'Scrum Agent: building sprint plan…',
  jira: 'Scrum Agent: Jira backlog structure & export…',
  readiness: 'Assembling delivery package…',
  complete: 'Delivery package ready — review & export.',
}

const BOOT_LOG = 'Launch AI team — autonomous SDLC run started.'

export function createInitialExecution() {
  return {
    completedSteps: [],
    failedSteps: [],
    currentStep: null,
    globalPercent: 0,
    agents: Object.fromEntries(
      MISSION_AGENTS.map((a) => [
        a.id,
        { percent: 0, status: 'waiting', activity: '' },
      ]),
    ),
    logs: [],
  }
}

function appendLog(logs, message, agentId) {
  const entry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    at: Date.now(),
    message,
    agentId,
  }
  return [...logs.slice(-40), entry]
}

function computeAgentPercent(agentId, completedSteps, runningStep) {
  const steps = AGENT_STEPS[agentId]
  const done = steps.filter((s) => completedSteps.includes(s)).length
  if (done >= steps.length) return 100

  if (runningStep && steps.includes(runningStep)) {
    const idx = steps.indexOf(runningStep)
    const base = (idx / steps.length) * 100
    const span = 100 / steps.length
    return Math.min(99, Math.round(base + span * 0.72))
  }

  return Math.round((done / steps.length) * 100)
}

export function applyDemoEvent(state, evt) {
  const step = evt?.step
  if (!step || step === 'boot' || step === 'persist') {
    if (Number.isFinite(+evt?.percent)) {
      return { ...state, globalPercent: +evt.percent }
    }
    if (step === 'boot') {
      return {
        ...state,
        logs: appendLog(state.logs, BOOT_LOG, 'pm'),
      }
    }
    return state
  }

  let next = {
    ...state,
    globalPercent: Number.isFinite(+evt?.percent) ? +evt.percent : state.globalPercent,
  }

  if (step === 'complete' && evt.status === 'done') {
    const agents = Object.fromEntries(
      MISSION_AGENTS.map((a) => [
        a.id,
        { percent: 100, status: 'done', activity: 'Complete' },
      ]),
    )
    return {
      ...next,
      currentStep: null,
      globalPercent: 100,
      agents,
      completedSteps: [...next.completedSteps, 'complete'],
      logs: appendLog(next.logs, STEP_LOG.complete, 'scrum'),
    }
  }

  const agentId = STEP_TO_AGENT[step]
  if (!agentId) return next

  const logMsg =
    (evt.headline ? String(evt.headline) : '') ||
    STEP_LOG[step] ||
    (evt.detail ? String(evt.detail) : '') ||
    `Autonomous step: ${step}…`

  if (evt.status === 'running') {
    next.currentStep = step
    next.logs = appendLog(next.logs, logMsg, agentId)
    for (const id of AGENT_ORDER) {
      if (id === agentId) {
        next.agents[id] = {
          percent: Math.max(
            next.agents[id].percent,
            computeAgentPercent(id, next.completedSteps, step),
          ),
          status: 'running',
          activity: logMsg,
        }
      } else if (AGENT_ORDER.indexOf(id) < AGENT_ORDER.indexOf(agentId)) {
        next.agents[id] = { percent: 100, status: 'done', activity: 'Complete' }
      } else {
        next.agents[id] = { ...next.agents[id], status: 'waiting' }
      }
    }
    return next
  }

  if (evt.status === 'error') {
    const errMsg =
      (evt.detail && String(evt.detail)) ||
      (evt.headline && String(evt.headline)) ||
      `Step failed: ${step}`
    next.failedSteps = next.failedSteps?.includes(step)
      ? next.failedSteps
      : [...(next.failedSteps || []), step]
    next.logs = appendLog(next.logs, `✗ ${errMsg}`, agentId)
    next.agents = { ...next.agents }
    for (const id of AGENT_ORDER) {
      if (id === agentId) {
        next.agents[id] = {
          percent: next.agents[id].percent,
          status: 'error',
          activity: errMsg,
        }
      } else if (AGENT_ORDER.indexOf(id) < AGENT_ORDER.indexOf(agentId)) {
        next.agents[id] = { percent: 100, status: 'done', activity: 'Complete' }
      }
    }
    return next
  }

  if (evt.status === 'done') {
    next.completedSteps = next.completedSteps.includes(step)
      ? next.completedSteps
      : [...next.completedSteps, step]
    next.logs = appendLog(next.logs, `✓ ${logMsg.replace(/…$/, '')}`, agentId)
    const steps = AGENT_STEPS[agentId]
    const allDone = steps.every((s) => next.completedSteps.includes(s))
    const pct = allDone ? 100 : computeAgentPercent(agentId, next.completedSteps, null)
    next.agents = { ...next.agents }
    for (const id of AGENT_ORDER) {
      if (AGENT_ORDER.indexOf(id) < AGENT_ORDER.indexOf(agentId)) {
        next.agents[id] = { percent: 100, status: 'done', activity: 'Complete' }
      }
    }
    next.agents[agentId] = {
      percent: pct,
      status: allDone ? 'done' : 'running',
      activity: allDone ? 'Complete' : next.agents[agentId].activity,
    }
    return next
  }

  return next
}

export function formatBlockBar(percent) {
  const filled = Math.max(0, Math.min(10, Math.round(percent / 10)))
  return `${'█'.repeat(filled)}${'░'.repeat(10 - filled)}`
}

export function seedLaunchLogs() {
  return [
    {
      id: 'boot-0',
      at: Date.now(),
      message: BOOT_LOG,
      agentId: 'pm',
    },
  ]
}

/** Map SSE step to pipeline UI id for progress strip */
export function pipelineUiStep(step) {
  return pipelineIdForDemoStep(step)
}
