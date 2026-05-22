import { motion, AnimatePresence } from 'framer-motion'

/**
 * On-screen “time saved” + traceability hook while the judge pipeline runs (SSE-driven).
 */
export default function JudgeDemoLiveTicker({ headline = '', detail = '', artifact = null }) {
  const minutesSaved = artifact?.minutes_saved ?? artifact?.hours_saved
    ? Math.round((artifact.hours_saved || 0) * 60) || 228
    : null
  const trace =
    artifact?.traceability_preview ||
    (artifact?.clauses?.length
      ? `${artifact.clauses.length} clauses → traceable backlog`
      : null) ||
    (artifact?.stories_count != null && artifact?.tasks_count != null
      ? `${artifact.stories_count} stories · ${artifact.tasks_count} tasks linked to clauses`
      : null)

  if (!headline && !detail && !trace) return null

  return (
    <AnimatePresence mode="wait">
      <motion.aside
        key={headline || 'idle'}
        className="jd-live-ticker panel"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        aria-live="polite"
      >
        {minutesSaved != null && (
          <p className="jd-live-ticker-saved">
            <span className="jd-live-ticker-badge">Time saved</span>
            ~{minutesSaved} min vs manual BA + architect + QA pass
          </p>
        )}
        {headline && <p className="jd-live-ticker-head">{headline}</p>}
        {detail && <p className="jd-live-ticker-detail muted small">{detail}</p>}
        {trace && (
          <p className="jd-live-ticker-trace muted small">
            <strong>Traceability:</strong> {String(trace).slice(0, 220)}
            {String(trace).length > 220 ? '…' : ''}
          </p>
        )}
      </motion.aside>
    </AnimatePresence>
  )
}
