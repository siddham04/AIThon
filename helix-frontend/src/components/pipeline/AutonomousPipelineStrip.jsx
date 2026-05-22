import { AUTONOMOUS_PIPELINE } from '../../lib/autonomousPipeline'

function statusFor(stepId, activeId, completedIds) {
  if (completedIds.has(stepId)) return 'is-done'
  if (activeId === stepId) return 'is-active'
  const order = AUTONOMOUS_PIPELINE.map((s) => s.id)
  const ai = activeId ? order.indexOf(activeId) : -1
  const si = order.indexOf(stepId)
  if (ai >= 0 && si < ai) return 'is-done'
  return ''
}

/**
 * Compact autonomous workflow strip — shows what the AI team is doing.
 * @param {string|null} activeStepId — pipeline step id from autonomousPipeline
 * @param {Set<string>} completedStepIds
 * @param {boolean} compact — smaller variant for Mission Control during run
 */
export default function AutonomousPipelineStrip({
  activeStepId = null,
  completedStepIds = new Set(),
  compact = false,
  showExport = true,
}) {
  const steps = showExport
    ? AUTONOMOUS_PIPELINE
    : AUTONOMOUS_PIPELINE.filter((s) => s.id !== 'export')

  return (
    <nav
      className={`hx-pipeline${compact ? ' hx-pipeline--compact' : ''}`}
      aria-label="Autonomous SDLC workflow"
    >
      <p className="hx-pipeline-eyebrow muted small">
        Autonomous by default — AI runs every step · you approve before export
      </p>
      <ol className="hx-pipeline-list">
        {steps.map((step, i) => {
          const status = statusFor(step.id, activeStepId, completedStepIds)
          const showArrow = i < steps.length - 1

          return (
            <li key={step.id} className="hx-pipeline-item">
              <div className={`hx-pipeline-step ${status}${step.autonomous ? '' : ' is-human'}`}>
                <span className="hx-pipeline-icon" aria-hidden>
                  {step.icon}
                </span>
                <span className="hx-pipeline-text">
                  <span className="hx-pipeline-label">{step.label}</span>
                  {!compact && (
                    <span className="hx-pipeline-actor muted small">{step.actor}</span>
                  )}
                </span>
                <span className="hx-pipeline-badge" aria-hidden>
                  {status === 'is-done' ? '✓' : status === 'is-active' ? '●' : '○'}
                </span>
              </div>
              {showArrow && <span className="hx-pipeline-arrow" aria-hidden>↓</span>}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
