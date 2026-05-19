/** Live progress for long-running backend jobs (WebSocket). */
export default function TaskProgressStrip({ label, percent = 0, message = '', status = '' }) {
  if (!status && !message && !percent) return null
  const pct = Math.max(0, Math.min(100, Number(percent) || 0))
  const err = status === 'error'
  return (
    <div className={`task-progress-strip${err ? ' task-progress-strip--error' : ''}`} role="status">
      <div className="task-progress-strip-head">
        <span className="task-progress-strip-label">{label}</span>
        <span className="muted small">{message}</span>
        <span className="muted small">{pct}%</span>
      </div>
      <div className="task-progress-bar" aria-hidden>
        <div className="task-progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
