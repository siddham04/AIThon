import { motion } from 'framer-motion'

export default function ReadinessScoreRing({ score = 0, statusLabel = 'PROJECT READY' }) {
  const pct = Math.max(0, Math.min(100, score))
  const ready = statusLabel === 'PROJECT READY'
  const r = 88
  const c = 2 * Math.PI * r
  const offset = c - (pct / 100) * c

  return (
    <div className={`drc-hero${ready ? ' drc-hero--ready' : ''}`}>
      <svg className="drc-ring-svg" viewBox="0 0 200 200" aria-hidden>
        <circle
          className="drc-ring-track"
          cx="100"
          cy="100"
          r={r}
          fill="none"
          strokeWidth="14"
        />
        <motion.circle
          className="drc-ring-fill"
          cx="100"
          cy="100"
          r={r}
          fill="none"
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
          transform="rotate(-90 100 100)"
        />
      </svg>
      <div className="drc-hero-text">
        <motion.span
          className="drc-status-label"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          {statusLabel}
        </motion.span>
        <motion.span
          className="drc-score-value"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.35, duration: 0.5 }}
        >
          {pct}%
        </motion.span>
      </div>
    </div>
  )
}
