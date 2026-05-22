import { motion, AnimatePresence } from 'framer-motion'
import { AUTONOMOUS_PIPELINE } from '../../lib/autonomousPipeline'

const JUDGE_STEPS = AUTONOMOUS_PIPELINE.filter((s) => s.id !== 'export')

function beatIndex(id) {
  return JUDGE_STEPS.findIndex((b) => b.id === id)
}

function statusFor(beatId, activeBeat, completedBeats) {
  if (completedBeats.has(beatId)) return 'is-done'
  if (activeBeat === beatId) return 'is-active'
  const ai = activeBeat ? beatIndex(activeBeat) : -1
  const bi = beatIndex(beatId)
  if (ai >= 0 && bi < ai) return 'is-done'
  return ''
}

export default function JudgeDemoPipeline({
  activeBeat = null,
  completedBeats = new Set(),
  running = false,
  progress = 0,
  liveHeadline = '',
  liveDetail = '',
}) {
  return (
    <section className="jd-pipeline" aria-label="Autonomous SDLC pipeline">
      <p className="jd-pipeline-principle muted small">
        You upload. The AI team runs every SDLC step. You review the delivery package and
        export.
      </p>
      {running && (
        <div className="jd-pipeline-progress" aria-live="polite">
          <div className="jd-pipeline-progress-track">
            <motion.div
              className="jd-pipeline-progress-fill"
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
            />
          </div>
          <span className="jd-pipeline-progress-label">{Math.round(progress)}%</span>
        </div>
      )}

      <ol className="jd-pipeline-list">
        {JUDGE_STEPS.map((beat, i) => {
          const status = statusFor(beat.id, activeBeat, completedBeats)
          const showArrow = i < JUDGE_STEPS.length - 1

          return (
            <li key={beat.id} className="jd-pipeline-item">
              <motion.div
                className={`jd-pipeline-step ${status}`}
                layout
                initial={false}
                animate={
                  status === 'is-active'
                    ? {
                        scale: 1.02,
                        boxShadow: '0 0 32px rgba(99, 102, 241, 0.35)',
                      }
                    : { scale: 1, boxShadow: '0 0 0 transparent' }
                }
                transition={{ duration: 0.35 }}
              >
                <span className="jd-pipeline-icon" aria-hidden>
                  {beat.icon}
                </span>
                <span className="jd-pipeline-label">{beat.label}</span>
                {status === 'is-active' && liveHeadline && (
                  <span className="jd-pipeline-live-head" aria-live="polite">
                    {liveHeadline}
                  </span>
                )}
                {status === 'is-active' && liveDetail && (
                  <span className="jd-pipeline-live-detail muted small">{liveDetail}</span>
                )}
                <span className="jd-pipeline-agent muted small">{beat.actor}</span>
                <span className="jd-pipeline-status" aria-hidden>
                  <AnimatePresence mode="wait">
                    {status === 'is-done' && (
                      <motion.span
                        key="done"
                        className="jd-pipeline-check"
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                      >
                        ✓
                      </motion.span>
                    )}
                    {status === 'is-active' && (
                      <motion.span
                        key="active"
                        className="jd-pipeline-pulse"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                      >
                        <span className="jd-pipeline-dot" />
                        <span className="jd-pipeline-dot" />
                        <span className="jd-pipeline-dot" />
                      </motion.span>
                    )}
                    {!status && (
                      <motion.span key="idle" className="jd-pipeline-idle">
                        ○
                      </motion.span>
                    )}
                  </AnimatePresence>
                </span>
              </motion.div>

              {showArrow && (
                <div className="jd-pipeline-arrow" aria-hidden>
                  <motion.span
                    animate={
                      status === 'is-done' || status === 'is-active'
                        ? { opacity: 1, y: 0 }
                        : { opacity: 0.35, y: 0 }
                    }
                  >
                    ↓
                  </motion.span>
                </div>
              )}
            </li>
          )
        })}
      </ol>
    </section>
  )
}
