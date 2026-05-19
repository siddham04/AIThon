import RequirementTextDiff from './RequirementTextDiff'

/** Requirement text before last successful generate vs after reload (client-only baseline). */
export default function RequirementSinceGenerateDiff({ beforeText, afterText, onDismiss }) {
  if (beforeText == null || afterText == null) return null
  if (beforeText === afterText) return null

  return (
    <div className="version-history since-generate-diff">
      <div className="since-generate-diff-head">
        <h4>Requirement delta (last generate)</h4>
        <button type="button" className="btn ghost small-btn" onClick={onDismiss}>
          Dismiss
        </button>
      </div>
      <p className="muted small">
        Synthesized requirement view before this run vs after artifacts refreshed (green = added, red =
        removed).
      </p>
      <RequirementTextDiff oldText={beforeText} newText={afterText} />
    </div>
  )
}
