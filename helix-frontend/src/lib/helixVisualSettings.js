/**
 * Visual effects toggles — on by default for hackathon polish.
 * Set VITE_HELIX_*=false or localStorage to disable on low-end devices.
 */

function envOff(key) {
  const v = import.meta.env[key]
  return v === 'false' || v === '0'
}

export function isHeroParticlesEnabled() {
  if (envOff('VITE_HELIX_HERO_PARTICLES')) return false
  if (import.meta.env.VITE_HELIX_HERO_PARTICLES === 'true') return true
  if (import.meta.env.VITE_HELIX_HERO_PARTICLES === '1') return true
  try {
    const stored = localStorage.getItem('helix_hero_particles')
    if (stored === '0') return false
    if (stored === '1') return true
  } catch {
    /* noop */
  }
  return true
}

export function isWorkspaceAmbientEnabled() {
  if (envOff('VITE_HELIX_WORKSPACE_AMBIENT')) return false
  if (import.meta.env.VITE_HELIX_WORKSPACE_AMBIENT === 'true') return true
  if (import.meta.env.VITE_HELIX_WORKSPACE_AMBIENT === '1') return true
  try {
    const stored = localStorage.getItem('helix_workspace_ambient')
    if (stored === '0') return false
    if (stored === '1') return true
  } catch {
    /* noop */
  }
  return true
}
