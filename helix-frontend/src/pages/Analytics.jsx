import { useCallback, useEffect, useMemo, useState, startTransition } from 'react'
import { useParams } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import toast from 'react-hot-toast'
import { api } from '../api/client'
import { useArtifactStore } from '../store/useStore'
import TraceGraph3D from '../components/analytics/TraceGraph3D'
import GraphErrorBoundary from '../components/analytics/GraphErrorBoundary'
import { DashboardSkeleton } from '../components/ui/Skeleton'
import { useDarkMode } from '../hooks/useDarkMode'

const TYPE_COLORS = ['#38bdf8', '#a78bfa', '#34d399', '#fbbf24', '#fb7185', '#94a3b8']

const PRIORITY_ORDER = ['critical', 'high', 'medium', 'low']
const PRIORITY_COLORS = {
  critical: '#fb7185',
  high: '#fbbf24',
  medium: '#38bdf8',
  low: '#94a3b8',
}

function pct1(n) {
  if (n == null || Number.isNaN(n)) return '—'
  return `${Math.round(Number(n) * 1000) / 10}%`
}

function PipelineTimings({ timings, dark }) {
  const rows = useMemo(() => {
    if (!timings || typeof timings !== 'object') return []
    return Object.entries(timings)
      .map(([stage, ms]) => ({ stage, ms: Number(ms) || 0 }))
      .sort((a, b) => b.ms - a.ms)
  }, [timings])

  if (!rows.length) {
    return (
      <p className="muted small">
        Run a full analyze on this project to record per-stage pipeline timings (shown here after the next
        successful run).
      </p>
    )
  }

  const maxMs = Math.max(...rows.map((r) => r.ms), 1)

  return (
    <ul className="pipeline-timing-list" aria-label="Last pipeline stage timings">
      {rows.map(({ stage, ms }) => (
        <li key={stage} className="pipeline-timing-row">
          <span className="pipeline-timing-label" title={stage}>
            {stage}
          </span>
          <div className="pipeline-timing-track" role="presentation">
            <div
              className="pipeline-timing-fill"
              style={{
                width: `${Math.min(100, (ms / maxMs) * 100)}%`,
                background: dark
                  ? 'linear-gradient(90deg, #38bdf8, #a78bfa)'
                  : 'linear-gradient(90deg, #0284c7, #7c3aed)',
              }}
            />
          </div>
          <span className="pipeline-timing-ms">{ms.toLocaleString()} ms</span>
        </li>
      ))}
    </ul>
  )
}

export default function Analytics() {
  const { id } = useParams()
  const { dark } = useDarkMode()
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const {
    stories,
    tasks,
    testcases,
    setBundle,
    setTestcases,
    citationItemRate,
    summary,
    lastPipelineTimingsMs,
  } = useArtifactStore()

  const load = useCallback(async () => {
    if (!id) return
    setLoadError(null)
    setLoading(true)
    try {
      const [a, t] = await Promise.all([api.get(`/artifacts/${id}`), api.get(`/testcases/${id}`)])
      setBundle(a.data)
      setTestcases(t.data)
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Failed to load analytics'
      setLoadError(msg)
      toast.error(typeof msg === 'string' ? msg : 'Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }, [id, setBundle, setTestcases])

  useEffect(() => {
    startTransition(() => {
      void load()
    })
  }, [load])

  const effortData = useMemo(() => {
    return (tasks || []).reduce((acc, t) => {
      const k = String(t.type || 'feature')
      const pts = Number(t.estimate_points) || 1
      const row = acc.find((r) => r.name === k)
      if (row) row.value += pts
      else acc.push({ name: k, value: pts })
      return acc
    }, [])
  }, [tasks])

  const prioData = useMemo(() => {
    return PRIORITY_ORDER.map((p) => ({
      priority: p,
      count: (tasks || []).filter((t) => String(t.priority || '').toLowerCase() === p).length,
    }))
  }, [tasks])

  const avgTaskConfidence = useMemo(() => {
    const vals = (tasks || [])
      .map((t) => (t.confidence != null && t.confidence !== '' ? Number(t.confidence) : null))
      .filter((v) => v != null && !Number.isNaN(v))
    if (!vals.length) return null
    return vals.reduce((a, b) => a + b, 0) / vals.length
  }, [tasks])

  const testTaskLinkRate = useMemo(() => {
    const tests = testcases || []
    if (!tests.length) return null
    const linked = tests.filter((tc) => !!(tc.extra?.task_id || tc.task_id)).length
    return linked / tests.length
  }, [testcases])

  const exportReadyStories = useMemo(() => {
    const s = stories || []
    if (!s.length) return null
    const ok = s.filter((x) => x.approved_for_export).length
    return { ok, total: s.length }
  }, [stories])

  if (loading) return <DashboardSkeleton />

  if (loadError) {
    return (
      <div className="page analytics-page">
        <header className="page-head">
          <h1>Analytics</h1>
        </header>
        <div className="panel analytics-error-panel" role="alert">
          <h3>Could not load data</h3>
          <p className="muted">{loadError}</p>
          <button type="button" className="btn btn-primary" onClick={() => void load()}>
            Retry
          </button>
        </div>
      </div>
    )
  }

  const pieData = effortData.length ? effortData : [{ name: 'No tasks', value: 1 }]
  const pieHasReal = effortData.length > 0

  return (
    <div className="page analytics-page">
      <header className="page-head">
        <h1>Analytics</h1>
        <p className="muted">
          Traceability KPIs, effort and priority views, last-run pipeline timings, and an interactive 3D
          requirement → story → task → test graph with legends.
        </p>
      </header>

      <section className="analytics-kpi-strip" aria-label="Project metrics">
        <div className="analytics-kpi-card">
          <span className="analytics-kpi-label">Stories</span>
          <span className="analytics-kpi-value">{(stories || []).length}</span>
        </div>
        <div className="analytics-kpi-card">
          <span className="analytics-kpi-label">Tasks</span>
          <span className="analytics-kpi-value">{(tasks || []).length}</span>
        </div>
        <div className="analytics-kpi-card">
          <span className="analytics-kpi-label">Tests</span>
          <span className="analytics-kpi-value">{(testcases || []).length}</span>
        </div>
        <div className="analytics-kpi-card" title="Fraction of stories, tasks, and tests with ≥1 source clause">
          <span className="analytics-kpi-label">Citation rate</span>
          <span className="analytics-kpi-value">{pct1(citationItemRate)}</span>
        </div>
        <div className="analytics-kpi-card" title="Mean model confidence on tasks (0–100%)">
          <span className="analytics-kpi-label">Avg task confidence</span>
          <span className="analytics-kpi-value">
            {avgTaskConfidence == null ? '—' : `${Math.round(avgTaskConfidence * 100)}%`}
          </span>
        </div>
        <div className="analytics-kpi-card" title="Tests with a linked task">
          <span className="analytics-kpi-label">Tests linked to tasks</span>
          <span className="analytics-kpi-value">
            {testTaskLinkRate == null ? '—' : pct1(testTaskLinkRate)}
          </span>
        </div>
        {exportReadyStories && (
          <div className="analytics-kpi-card" title="Stories marked approved for export">
            <span className="analytics-kpi-label">Export-ready stories</span>
            <span className="analytics-kpi-value">
              {exportReadyStories.ok}/{exportReadyStories.total}
            </span>
          </div>
        )}
      </section>

      {summary?.title && (
        <div className="panel analytics-summary-banner">
          <span className="muted small">Initiative</span>
          <p className="analytics-summary-title">{summary.title}</p>
          {summary.objective && <p className="muted small analytics-summary-obj">{summary.objective}</p>}
        </div>
      )}

      <div className="analytics-grid">
        <div className="panel">
          <h3>Effort by task category</h3>
          <p className="muted small chart-sub">Story points rolled up by task type (Fibonacci estimates).</p>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={88}
                  innerRadius={0}
                  paddingAngle={pieHasReal ? 2 : 0}
                  label={({ name, percent }) =>
                    pieHasReal ? `${name} (${(percent * 100).toFixed(0)}%)` : name
                  }
                >
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={TYPE_COLORS[i % TYPE_COLORS.length]} stroke="var(--panel-bg)" />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name) => [`${value} pts`, name]} />
                <Legend verticalAlign="bottom" height={28} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="panel">
          <h3>Tasks by priority</h3>
          <p className="muted small chart-sub">Backlog shape by severity (normalized counts).</p>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={prioData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="priority" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fill: 'var(--text-muted)', fontSize: 12 }} width={36} />
                <Tooltip
                  cursor={{ fill: 'rgba(56, 189, 248, 0.08)' }}
                  contentStyle={{
                    borderRadius: 8,
                    border: '1px solid var(--border)',
                    background: 'var(--panel-bg)',
                  }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]} name="Tasks">
                  {prioData.map((entry) => (
                    <Cell
                      key={entry.priority}
                      fill={PRIORITY_COLORS[entry.priority] || '#38bdf8'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="panel wide analytics-pipeline-panel">
          <h3>Last analyze — stage timings</h3>
          <p className="muted small chart-sub">
            Wall time per agent stage from the most recent successful pipeline run (server-side).
          </p>
          <PipelineTimings timings={lastPipelineTimingsMs} dark={dark} />
        </div>

        <div className="panel wide analytics-graph-panel">
          <h3>Traceability graph (3D)</h3>
          <p className="muted small chart-sub">
            Colored edges encode relationship type; use the sidebar legend and inspector. Drag to orbit, scroll
            to zoom, Esc clears a pinned node.
          </p>
          <GraphErrorBoundary>
            <TraceGraph3D dark={dark} stories={stories} tasks={tasks} testcases={testcases} />
          </GraphErrorBoundary>
        </div>
      </div>
    </div>
  )
}
