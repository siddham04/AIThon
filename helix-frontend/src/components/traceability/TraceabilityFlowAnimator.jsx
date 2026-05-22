import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../../api/client'

const LANES = [
  { key: 'clause', label: 'Clause', color: '#6366f1' },
  { key: 'story', label: 'Story', color: '#22c55e' },
  { key: 'task', label: 'Task', color: '#38bdf8' },
  { key: 'test', label: 'Test', color: '#f59e0b' },
]

export default function TraceabilityFlowAnimator({ projectId }) {
  const [graph, setGraph] = useState(null)
  const [pulse, setPulse] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!projectId) return undefined
    let cancelled = false
    api
      .get(`/traceability/${projectId}/graph`)
      .then(({ data }) => {
        if (!cancelled) setGraph(data)
      })
      .catch(() => {
        if (!cancelled) setGraph(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [projectId])

  useEffect(() => {
    if (!graph?.nodes?.length) return undefined
    const id = setInterval(() => setPulse((p) => p + 1), 1400)
    return () => clearInterval(id)
  }, [graph])

  const counts = useMemo(() => {
    const nodes = graph?.nodes || []
    const byKind = {}
    for (const n of nodes) {
      const k = (n.kind || n.type || 'other').toLowerCase()
      byKind[k] = (byKind[k] || 0) + 1
    }
    return byKind
  }, [graph])

  const activeLane = LANES[pulse % LANES.length]?.key

  if (!projectId) return null
  if (loading) return <p className="muted small">Loading traceability…</p>
  if (!graph?.nodes?.length) {
    return (
      <p className="muted small trace-flow-empty">
        Traceability graph appears after the AI pipeline runs.
      </p>
    )
  }

  return (
    <div className="trace-flow-anim panel" aria-label="Traceability flow animation">
      <p className="trace-flow-title">
        <strong>Traceability chain</strong> — requirement clauses linked to delivery artifacts
      </p>
      <div className="trace-flow-lanes">
        {LANES.map((lane, i) => {
          const count =
            counts[lane.key] ||
            counts[`${lane.key}s`] ||
            (lane.key === 'clause' ? counts.requirement : 0) ||
            0
          const active = activeLane === lane.key
          return (
            <div key={lane.key} className="trace-flow-lane-wrap">
              {i > 0 && (
                <motion.span
                  className="trace-flow-arrow"
                  animate={{ opacity: active ? 1 : 0.35, x: active ? 4 : 0 }}
                >
                  →
                </motion.span>
              )}
              <motion.div
                className={`trace-flow-lane${active ? ' is-active' : ''}`}
                style={{ borderColor: lane.color }}
                animate={{
                  scale: active ? 1.04 : 1,
                  boxShadow: active
                    ? `0 0 24px ${lane.color}44`
                    : '0 0 0 transparent',
                }}
                transition={{ duration: 0.35 }}
              >
                <span className="trace-flow-lane-label">{lane.label}</span>
                <AnimatePresence mode="wait">
                  <motion.span
                    key={`${lane.key}-${count}-${pulse}`}
                    className="trace-flow-lane-count"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                  >
                    {count}
                  </motion.span>
                </AnimatePresence>
              </motion.div>
            </div>
          )
        })}
      </div>
      <p className="muted small">
        {graph.edges?.length || 0} trace links · click nodes in Delivery Center for full graph
      </p>
    </div>
  )
}
