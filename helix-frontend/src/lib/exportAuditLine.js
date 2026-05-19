function readSessionUser() {
  try {
    return JSON.parse(localStorage.getItem('helix_user') || 'null')
  } catch {
    return null
  }
}

/** Audit footer for Markdown handoff (env-driven labels for demo / prod). */
export function buildExportAuditFooter() {
  const generated = new Date().toISOString()
  const model =
    (import.meta.env.VITE_HELIX_EXPORT_MODEL && String(import.meta.env.VITE_HELIX_EXPORT_MODEL).trim()) ||
    'Helix bundle (demo)'
  const u = readSessionUser()
  const user =
    (u && (u.email || u.username || u.name))?.trim?.() ||
    (import.meta.env.VITE_HELIX_EXPORT_USER && String(import.meta.env.VITE_HELIX_EXPORT_USER).trim()) ||
    'signed-in user'
  return `\n\n---\n\n_Generated at ${generated} · model ${model} · user ${user}_\n`
}
