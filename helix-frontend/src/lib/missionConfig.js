const STORAGE_KEY = 'helix_mission_config'

export const DEFAULT_MISSION_CONFIG = {
  teamSize: 6,
  sprintWeeks: 2,
  priorityMode: 'delivery-first',
  techStack: 'React · FastAPI · PostgreSQL',
}

export const PRIORITY_MODES = [
  { id: 'delivery-first', label: 'Delivery-first' },
  { id: 'balanced', label: 'Balanced' },
  { id: 'quality-first', label: 'Quality-first' },
]

export const TECH_PRESETS = [
  'React · FastAPI · PostgreSQL',
  'Next.js · Node · MongoDB',
  '.NET · Azure · SQL Server',
  'Java · Spring · Kubernetes',
]

export function loadMissionConfig(projectId) {
  try {
    const raw = sessionStorage.getItem(
      projectId ? `${STORAGE_KEY}_${projectId}` : STORAGE_KEY,
    )
    if (!raw) return { ...DEFAULT_MISSION_CONFIG }
    return { ...DEFAULT_MISSION_CONFIG, ...JSON.parse(raw) }
  } catch {
    return { ...DEFAULT_MISSION_CONFIG }
  }
}

export function saveMissionConfig(projectId, config) {
  try {
    const key = projectId ? `${STORAGE_KEY}_${projectId}` : STORAGE_KEY
    sessionStorage.setItem(key, JSON.stringify(config))
  } catch {
    /* noop */
  }
}

/** Prepended to requirements so agents respect team preferences. */
export function buildConfigPreamble(config) {
  const c = { ...DEFAULT_MISSION_CONFIG, ...config }
  return (
    `[Helix team configuration]\n` +
    `Team size: ${c.teamSize} engineers\n` +
    `Sprint length: ${c.sprintWeeks} weeks\n` +
    `Priority mode: ${c.priorityMode}\n` +
    `Tech stack: ${c.techStack}\n` +
    `---\n\n`
  )
}
