/**
 * Helix — 5-page product (AI-first, hackathon-polished).
 */

export const PRODUCT_PAGES = [
  {
    id: 'judge-demo',
    segment: '/judge-demo',
    label: 'Judge Demo',
    short: 'Demo',
    icon: '▶',
    tagline: '5-min autonomous SDLC',
    requiresProject: false,
    global: false,
    judge: true,
  },
  {
    id: 'mission-control',
    segment: '/mission-control',
    label: 'Mission Control',
    short: 'Upload',
    icon: '⎈',
    tagline: 'Your own requirement',
    requiresProject: false,
    global: false,
  },
  {
    id: 'ai-workspace',
    segment: '/ai-workspace',
    label: 'AI Workspace',
    short: 'Output',
    icon: '✦',
    tagline: 'Checklist · Approve',
    requiresProject: true,
    global: false,
  },
  {
    id: 'delivery-command',
    segment: '/delivery-command',
    label: 'Delivery Center',
    short: 'Plan',
    icon: '▦',
    tagline: 'Sprint · Graph',
    requiresProject: true,
    global: false,
  },
  {
    id: 'copilot',
    segment: '/copilot',
    label: 'Copilot',
    short: 'Chat',
    icon: '💬',
    tagline: 'SDLC · Trained',
    requiresProject: true,
    global: false,
    highlight: true,
  },
  {
    id: 'settings',
    segment: '/settings',
    label: 'Settings',
    short: 'Prefs',
    icon: '⚙',
    tagline: 'Team & keys',
    requiresProject: false,
    global: true,
  },
]

/** @deprecated alias for TeamFlowBar */
export const TEAM_FLOW = PRODUCT_PAGES.filter((p) => p.id !== 'settings')

export const SETTINGS_FLOW = PRODUCT_PAGES.find((p) => p.id === 'settings')

export const PRIMARY_NAV = PRODUCT_PAGES

export function navPath(projectId, segment, global) {
  if (global) return segment
  if (!projectId) return segment
  return `/project/${projectId}${segment}`
}

export function activeFlowId(pathname) {
  if (pathname.includes('/ai-workspace')) return 'ai-workspace'
  if (pathname.includes('/delivery-command') || pathname.includes('/delivery-package')) {
    return 'delivery-command'
  }
  if (pathname.includes('/copilot') || pathname.includes('/workspace')) return 'copilot'
  if (pathname.includes('/judge-demo')) return 'judge-demo'
  if (
    pathname.includes('/mission-control') ||
    pathname.includes('/new') ||
    pathname === '/executive'
  ) {
    return 'mission-control'
  }
  if (pathname.includes('/settings')) return 'settings'
  return null
}

export const LEGACY_PROJECT_REDIRECTS = {
  dashboard: 'mission-control',
  executive: 'mission-control',
  new: 'mission-control',
  hub: 'copilot',
  preview: 'ai-workspace',
  analytics: 'ai-workspace',
  insights: 'ai-workspace',
  'command-center': 'delivery-command',
  'control-tower': 'delivery-command',
  'review-board': 'ai-workspace',
  quality: 'ai-workspace',
  impact: 'ai-workspace',
  backlog: 'ai-workspace',
  'sprint-plan': 'delivery-command',
  studio: 'ai-workspace',
  'dev-studio': 'ai-workspace',
  forecast: 'mission-control',
  meeting: 'mission-control',
  diff: 'ai-workspace',
  traceability: 'delivery-command',
  prd: 'ai-workspace',
  twin: 'delivery-command',
  pm: 'delivery-command',
  demo: 'mission-control',
  'judge-demo': 'judge-demo',
  'winning-demo': 'judge-demo',
  'requirement-studio': 'mission-control',
  'agent-workflow': 'ai-workspace',
  'quality-center': 'ai-workspace',
  architecture: 'ai-workspace',
  'sprint-planner': 'delivery-command',
  'traceability-graph': 'delivery-command',
  'risk-center': 'ai-workspace',
  'chat-assistant': 'copilot',
  assistant: 'copilot',
  workspace: 'copilot',
  'delivery-package': 'ai-workspace',
  'delivery-readiness': 'ai-workspace',
}

export const LEGACY_GLOBAL_REDIRECTS = {
  dashboard: '/mission-control',
  executive: '/mission-control',
  new: '/mission-control',
  demo: '/mission-control',
  'judge-demo': '/judge-demo',
  'winning-demo': '/judge-demo',
  studio: '/ai-workspace',
  'dev-studio': '/ai-workspace',
  forecast: '/mission-control',
  meeting: '/mission-control',
  diff: '/ai-workspace',
  prd: '/ai-workspace',
  'requirement-studio': '/mission-control',
  'agent-workflow': '/ai-workspace',
  'quality-center': '/ai-workspace',
  architecture: '/ai-workspace',
  'sprint-planner': '/delivery-command',
  'traceability-graph': '/delivery-command',
  'risk-center': '/ai-workspace',
  'chat-assistant': '/copilot',
  assistant: '/copilot',
  workspace: '/copilot',
  'delivery-package': '/ai-workspace',
  'delivery-readiness': '/ai-workspace',
}

export function isNativeShellPath(pathname) {
  const segments = [
    'mission-control',
    'judge-demo',
    'ai-workspace',
    'delivery-command',
    'copilot',
    'settings',
  ]
  if (segments.some((s) => pathname === `/${s}` || pathname.endsWith(`/${s}`))) return true
  if (
    pathname.match(
      /^\/project\/[^/]+\/(mission-control|judge-demo|ai-workspace|delivery-command|copilot)$/,
    )
  ) {
    return true
  }
  if (pathname === '/settings' || pathname.endsWith('/settings')) return true
  return false
}
