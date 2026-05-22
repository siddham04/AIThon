import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  MISSION_AGENTS,
  formatBlockBar,
} from '../../lib/missionAgents'

function AgentBarRow({ agent, state, isActive }) {
  const pct = Math.max(0, Math.min(100, state?.percent ?? 0))
  const status = state?.status || 'waiting'
  const blocks = formatBlockBar(pct)

  return (
    <motion.div
      className={`mc-exec-agent mc-exec-agent--${status}${isActive ? ' mc-exec-agent--live' : ''}`}
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="mc-exec-agent-head">
        <span className="mc-exec-agent-glyph" aria-hidden>
          {agent.glyph}
        </span>
        <span className="mc-exec-agent-name">{agent.label}</span>
        {status === 'running' && (
          <span className="mc-exec-live-dot" aria-label="Working">
            <span className="mc-exec-pulse" />
          </span>
        )}
        {status === 'done' && <span className="mc-exec-done-badge">✓</span>}
        {status === 'error' && <span className="mc-exec-error-badge">!</span>}
      </div>
      <div className="mc-exec-bar-line">
        <code className="mc-exec-blocks" aria-hidden>
          {blocks}
        </code>
        <span className="mc-exec-pct">{pct}%</span>
      </div>
      {status === 'error' && state?.activity && (
        <p className="mc-exec-activity mc-exec-activity--error">{state.activity}</p>
      )}
      {status === 'running' && state?.activity && (
        <motion.p
          className="mc-exec-activity"
          key={state.activity}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {state.activity}
        </motion.p>
      )}
    </motion.div>
  )
}

export default function MissionAgentExecution({
  execution,
  globalPercent = 0,
  running = false,
  onStop,
}) {
  const logRef = useRef(null)
  const activeId = MISSION_AGENTS.find((a) => execution.agents[a.id]?.status === 'running')?.id

  useEffect(() => {
    const el = logRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [execution.logs.length])

  return (
    <section className="mc-exec" aria-live="polite" aria-busy={running}>
      <header className="mc-exec-head">
        <div>
          <span className="mc-exec-eyebrow">Live execution</span>
          <h2>Your AI team is working</h2>
          <p className="muted small">
            Autonomous agents — same feel as Cursor, Devin, or Operator.
          </p>
        </div>
        <div className="mc-exec-head-meta">
          <span className="mc-exec-global">{Math.round(globalPercent)}%</span>
          {onStop && (
            <button type="button" className="btn ghost small" onClick={onStop}>
              Stop
            </button>
          )}
        </div>
      </header>

      <div className="mc-exec-grid">
        <div className="mc-exec-agents panel">
          {MISSION_AGENTS.map((agent) => (
            <AgentBarRow
              key={agent.id}
              agent={agent}
              state={execution.agents[agent.id]}
              isActive={activeId === agent.id}
            />
          ))}
        </div>

        <div className="mc-exec-terminal panel">
          <header className="mc-exec-terminal-head">
            <span className="mc-exec-terminal-dot" />
            <span>Live stream</span>
          </header>
          <ul className="mc-exec-log" ref={logRef}>
            <AnimatePresence initial={false}>
              {execution.logs.length === 0 && (
                <li className="mc-exec-log-line muted small">Waiting for events…</li>
              )}
              {execution.logs.map((entry) => (
                <motion.li
                  key={entry.id}
                  className="mc-exec-log-line"
                  initial={{ opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <time>{new Date(entry.at).toLocaleTimeString()}</time>
                  {entry.agentId && (
                    <span className={`mc-exec-log-tag mc-exec-log-tag--${entry.agentId}`}>
                      {entry.agentId === 'pm'
                        ? 'PM'
                        : entry.agentId === 'architect'
                          ? 'ARCH'
                          : entry.agentId === 'qa'
                            ? 'QA'
                            : 'SCRUM'}
                    </span>
                  )}
                  <span>{entry.message}</span>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        </div>
      </div>
    </section>
  )
}
