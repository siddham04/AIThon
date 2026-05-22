/**
 * Hackathon demo runtime — synced with GET /api/health and HELIX_DEMO_FAST.
 */

const ENV_FAST =
  import.meta.env.VITE_HELIX_DEMO_FAST === 'true' ||
  import.meta.env.VITE_HELIX_DEMO_FAST === '1'

export const DEFAULT_SHOWCASE_PROJECT_ID =
  import.meta.env.VITE_HELIX_SHOWCASE_PROJECT_ID || 'proj_demo_seed01'

let cached = {
  demoFast: ENV_FAST,
  showcaseProjectId: DEFAULT_SHOWCASE_PROJECT_ID,
  loaded: false,
}

/** @returns {Promise<{ demoFast: boolean, showcaseProjectId: string }>} */
export async function loadDemoConfig(api) {
  if (cached.loaded) return cached
  try {
    const { data } = await api.get('/health')
    cached = {
      demoFast: ENV_FAST || Boolean(data.demo_fast),
      showcaseProjectId: data.showcase_project_id || DEFAULT_SHOWCASE_PROJECT_ID,
      loaded: true,
    }
  } catch {
    cached.loaded = true
  }
  return cached
}

export function getDemoConfigSync() {
  return cached
}

export function resolveDemoUseAi(requested = true) {
  const { demoFast } = getDemoConfigSync()
  if (demoFast) return false
  return requested
}

export const HELIX_AUTO_DEMO_KEY = 'helix_auto_demo'
