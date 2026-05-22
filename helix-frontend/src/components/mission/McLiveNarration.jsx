import { motion, AnimatePresence } from 'framer-motion'

/** Headline-driven narration during long pipeline runs (SSE). */
export default function McLiveNarration({ headline = '', detail = '', percent = 0 }) {
  if (!headline && !detail) return null

  return (
    <AnimatePresence mode="wait">
      <motion.aside
        key={headline || 'idle'}
        className="mc-live-narration panel"
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        aria-live="polite"
      >
        <p className="mc-live-narration-label muted small">
          Live pipeline · {Math.round(percent)}%
        </p>
        {headline && <p className="mc-live-narration-head">{headline}</p>}
        {detail && <p className="mc-live-narration-detail muted small">{detail}</p>}
      </motion.aside>
    </AnimatePresence>
  )
}
