import { NavLink, useLocation, useParams } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import { TEAM_FLOW, activeFlowId, navPath } from '../../lib/productFlow'

export default function TeamFlowBar() {
  const { id: projectId } = useParams()
  const { pathname } = useLocation()
  const reduceMotion = useReducedMotion()
  const current = activeFlowId(pathname)

  if (!projectId) return null

  return (
    <nav className="team-flow" aria-label="Your autonomous SDLC team">
      <p className="team-flow-label muted small">Your team</p>
      <ol className="team-flow-steps">
        {TEAM_FLOW.map((step, i) => {
          const to = navPath(projectId, step.segment, false)
          const isActive = current === step.id
          const isPast =
            TEAM_FLOW.findIndex((s) => s.id === current) > i && current !== null

          return (
            <li key={step.id} className="team-flow-item">
              {i > 0 && <span className="team-flow-connector" aria-hidden />}
              <NavLink
                to={to}
                className={() =>
                  `team-flow-step${isActive ? ' is-active' : ''}${isPast ? ' is-past' : ''}`.trim()
                }
                title={step.tagline}
              >
                <motion.span
                  className="team-flow-icon"
                  aria-hidden
                  animate={reduceMotion || !isActive ? {} : { scale: [1, 1.08, 1] }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                >
                  {step.icon}
                </motion.span>
                <span className="team-flow-text">
                  <span className="team-flow-short">{step.short}</span>
                  <span className="team-flow-name">{step.label}</span>
                </span>
              </NavLink>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
