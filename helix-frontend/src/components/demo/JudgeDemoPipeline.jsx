import { motion, AnimatePresence } from 'framer-motion'
import { AUTONOMOUS_PIPELINE } from '../../lib/autonomousPipeline'

const JUDGE_STEPS = AUTONOMOUS_PIPELINE.filter((s) => s.id !== 'export')

const AGENT_ROLE = {
  You: 'you',
  Helix: 'helix',
  'PM Agent': 'pm',
  'Architect Agent': 'arch',
  'Scrum Agent': 'scrum',
  'QA Agent': 'qa',
}

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
  const doneCount = JUDGE_STEPS.filter((b) => completedBeats.has(b.id)).length

  return (
    <section className="jd-pipeline" aria-label="Autonomous SDLC pipeline">
      <header className="jd-pipeline-header">
        <p className="jd-pipeline-principle">
          You upload → AI team runs every SDLC step → you review &amp; export
        </p>
        {running && (
          <div className="jd-pipeline-progress" aria-live="polite">
            <div className="jd-pipeline-progress-meta">
              <span className="jd-pipeline-progress-title">Pipeline running</span>
              <span className="jd-pipeline-progress-label">{Math.round(progress)}%</span>
            </div>
            <div className="jd-pipeline-progress-track">
              <motion.div
                className="jd-pipeline-progress-fill"
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
              />
            </div>
            <p className="jd-pipeline-progress-steps muted small">
              {doneCount} of {JUDGE_STEPS.length} steps complete
            </p>
          </div>
        )}
      </header>

      <ol className="jd-pipeline-list">
        {JUDGE_STEPS.map((beat, i) => {
          const status = statusFor(beat.id, activeBeat, completedBeats)
          const role = AGENT_ROLE[beat.actor] || 'helix'
          const isLast = i === JUDGE_STEPS.length - 1

          return (
            <li
              key={beat.id}
              className={`jd-pipeline-item${status ? ` jd-pipeline-item--${status.replace('is-', '')}` : ''}`}
            >
              <div className="jd-pipeline-rail" aria-hidden>
                <span className="jd-pipeline-rail-num">{String(i + 1).padStart(2, '0')}</span>
                {!isLast && <span className="jd-pipeline-rail-line" />}
              </div>

              <motion.article
                className={`jd-pipeline-step ${status}`}
                data-agent={role}
                layout
                initial={false}
                animate={
                  status === 'is-active'
                    ? { scale: 1.01, y: 0 }
                    : { scale: 1, y: 0 }
                }
                transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              >
                {status === 'is-active' && <span className="jd-pipeline-glow" aria-hidden />}

                <span className="jd-pipeline-icon-wrap" aria-hidden>
                  <span className="jd-pipeline-icon">{beat.icon}</span>
                </span>

                <div className="jd-pipeline-body">
                  <div className="jd-pipeline-title-row">
                    <h3 className="jd-pipeline-label">{beat.label}</h3>
                    <span className={`jd-pipeline-agent-pill jd-pipeline-agent-pill--${role}`}>
                      {beat.actor}
                    </span>
                  </div>

                  {status === 'is-active' && liveHeadline && (
                    <p className="jd-pipeline-live-head" aria-live="polite">
                      {liveHeadline}
                    </p>
                  )}
                  {status === 'is-active' && liveDetail && (
                    <p className="jd-pipeline-live-detail">{liveDetail}</p>
                  )}
                </div>

                <span className="jd-pipeline-status" aria-hidden>
                  <AnimatePresence mode="wait">
                    {status === 'is-done' && (
                      <motion.span
                        key="done"
                        className="jd-pipeline-check"
                        initial={{ scale: 0, rotate: -40, opacity: 0 }}
                        animate={{ scale: 1, rotate: 0, opacity: 1 }}
                        transition={{ type: 'spring', stiffness: 420, damping: 22 }}
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
              </motion.article>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
