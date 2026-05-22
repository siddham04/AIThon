/** Human-managed settings (local until backend vault). */

const KEY = 'helix_human_settings'

export const DEFAULT_HUMAN_SETTINGS = {
  teamSize: 6,
  velocity: 20,
  sprintWeeks: 2,
  priorityMode: 'delivery-first',
  techStack: 'React · FastAPI · PostgreSQL',
  jiraBaseUrl: '',
  jiraEmail: '',
  jiraToken: '',
  jiraProjectKey: '',
  githubToken: '',
  githubRepo: '',
  azureEndpoint: '',
  azureKey: '',
  azureDeployment: '',
}

export function loadHumanSettings() {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return { ...DEFAULT_HUMAN_SETTINGS }
    return { ...DEFAULT_HUMAN_SETTINGS, ...JSON.parse(raw) }
  } catch {
    return { ...DEFAULT_HUMAN_SETTINGS }
  }
}

export function saveHumanSettings(patch) {
  const next = { ...loadHumanSettings(), ...patch }
  localStorage.setItem(KEY, JSON.stringify(next))
  return next
}

export function settingsToMissionConfig(human) {
  return {
    teamSize: human.teamSize,
    sprintWeeks: human.sprintWeeks,
    priorityMode: human.priorityMode,
    techStack: human.techStack,
  }
}
