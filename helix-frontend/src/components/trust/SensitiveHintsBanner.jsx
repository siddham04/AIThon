import { useCallback, useMemo, useState } from 'react'

function dismissKey(projectId) {
  return `helix_dismiss_sensitive_hints_${projectId}`
}

export default function SensitiveHintsBanner({ projectId, hints = [], className = '' }) {
  const normalized = useMemo(
    () => [...new Set((hints || []).map((h) => String(h).trim()).filter(Boolean))],
    [hints],
  )
  const [dismissed, setDismissed] = useState(() => {
    if (!projectId || typeof sessionStorage === 'undefined') return false
    try {
      return sessionStorage.getItem(dismissKey(projectId)) === '1'
    } catch {
      return false
    }
  })

  const onDismiss = useCallback(() => {
    if (!projectId) return
    try {
      sessionStorage.setItem(dismissKey(projectId), '1')
    } catch {
      /* noop */
    }
    setDismissed(true)
  }, [projectId])

  if (!projectId || !normalized.length || dismissed) return null

  return (
    <div className={`sensitive-hints-banner ${className}`.trim()} role="status">
      <div className="sensitive-hints-banner__body">
        <strong>Redaction hints</strong>
        <span className="muted small">
          Ingest scan flagged possible sensitive content — review before sharing externally.
        </span>
        <ul>
          {normalized.map((h) => (
            <li key={h}>{h}</li>
          ))}
        </ul>
      </div>
      <button type="button" className="btn ghost small-btn" onClick={onDismiss}>
        Dismiss
      </button>
    </div>
  )
}
