import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '../api/client'
import { loadHumanSettings } from '../lib/helixSettings'

const DependencyGraphFlow = lazy(() => import('../components/fx/DependencyGraphFlow'))

export default function DeliveryCommandCenter() {
  const { id } = useParams()
  const human = loadHumanSettings()
  const [loading, setLoading] = useState(() => Boolean(id))
  const [sprintPlan, setSprintPlan] = useState(null)
  const [forecast, setForecast] = useState(null)
  const [artifacts, setArtifacts] = useState(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      const settled = await Promise.allSettled([
        api.get(`/sprint-plan/${id}/auto`),
        api.get(`/artifacts/${id}`),
        api.get(`/delivery/pm/${id}`),
      ])
      const val = (i) => (settled[i].status === 'fulfilled' ? settled[i].value.data : null)
      setSprintPlan(val(0))
      setArtifacts(val(1))
      setForecast(val(2))
    } catch {
      toast.error('Could not load command center')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    if (!id) return undefined
    let cancelled = false
    ;(async () => {
      try {
        const settled = await Promise.allSettled([
          api.get(`/sprint-plan/${id}/auto`),
          api.get(`/artifacts/${id}`),
          api.get(`/delivery/pm/${id}`),
        ])
        if (cancelled) return
        const val = (i) => (settled[i].status === 'fulfilled' ? settled[i].value.data : null)
        setSprintPlan(val(0))
        setArtifacts(val(1))
        setForecast(val(2))
      } catch {
        if (!cancelled) toast.error('Could not load command center')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id])

  const refreshPlan = async () => {
    try {
      const { data } = await api.post(`/sprint-plan/${id}/auto`)
      setSprintPlan(data)
      toast.success('Sprint plan refreshed')
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Sprint plan failed')
    }
  }

  if (!id) {
    return (
      <div className="p5-page p5-empty">
        <h1>Delivery Center</h1>
        <p className="muted">Run Mission Control first.</p>
        <Link to="/mission-control" className="btn btn-primary">
          Mission Control
        </Link>
      </div>
    )
  }

  const sprints = sprintPlan?.sprints || []
  const assignments = sprintPlan?.assignments || sprintPlan?.team_assignments || []
  const timeline = forecast?.timeline || forecast?.milestones || []

  return (
    <div className="p5-page">
      <header className="p5-hero">
        <p className="p5-eyebrow">AI-maintained delivery</p>
        <h1>Delivery Center</h1>
        <p className="muted small">
          Sprint plan, team allocation, dependencies, and timeline — updated by the AI team.
        </p>
        <div className="p5-actions" style={{ marginTop: '0.75rem' }}>
          <button type="button" className="btn ghost small" onClick={() => void load()}>
            Refresh
          </button>
          <button type="button" className="btn ghost small" onClick={() => void refreshPlan()}>
            Re-plan sprint
          </button>
        </div>
      </header>

      {!loading && !sprints.length && !(artifacts?.stories?.length) && (
        <section className="p5-panel p5-empty-run" role="alert">
          <h2>No delivery plan yet</h2>
          <p className="muted">Launch the AI team on Mission Control first.</p>
          <Link to={`/project/${id}/mission-control`} className="btn btn-primary">
            Mission Control →
          </Link>
        </section>
      )}

      {loading && <p className="muted">Loading plan…</p>}

      {!loading && (
        <>
          <div className="p5-grid-2">
            <div className="p5-stat">
              <p className="p5-stat-label">Team size</p>
              <p className="p5-stat-value">{human.teamSize}</p>
            </div>
            <div className="p5-stat">
              <p className="p5-stat-label">Velocity</p>
              <p className="p5-stat-value">{human.velocity} pts/sprint</p>
            </div>
            <div className="p5-stat">
              <p className="p5-stat-label">Sprints</p>
              <p className="p5-stat-value">{sprints.length || '—'}</p>
            </div>
            <div className="p5-stat">
              <p className="p5-stat-label">Release risk</p>
              <p className="p5-stat-value">{forecast?.release_risk || '—'}</p>
            </div>
          </div>

          <section className="p5-panel">
            <div className="p5-section-head">
              <h2>Sprint plan</h2>
            </div>
            {sprints.length === 0 ? (
              <p className="muted">No sprint plan yet. Run the pipeline or Re-plan sprint.</p>
            ) : (
              sprints.map((sp, i) => (
                <div key={sp.id || i} className="p5-timeline-item">
                  <div>
                    <strong>{sp.name || `Sprint ${i + 1}`}</strong>
                    <p className="muted small">
                      {(sp.story_ids || sp.stories || []).length} stories
                      {sp.total_points != null && ` · ${sp.total_points} pts`}
                    </p>
                  </div>
                </div>
              ))
            )}
          </section>

          <section className="p5-panel">
            <div className="p5-section-head">
              <h2>Team allocation</h2>
            </div>
            {assignments.length === 0 ? (
              <p className="muted">
                Allocation derived from {human.teamSize} engineers @ {human.velocity} velocity.
              </p>
            ) : (
              <ul className="p5-list">
                {assignments.slice(0, 10).map((a, i) => (
                  <li key={i}>
                    {a.member || a.developer || 'Engineer'} → {a.task_id || a.story_id || a.label}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="p5-panel">
            <div className="p5-section-head">
              <h2>Dependency graph</h2>
            </div>
            <div className="p5-graph-wrap">
              <Suspense fallback={<p className="muted">Loading graph…</p>}>
                <DependencyGraphFlow />
              </Suspense>
            </div>
            <p className="muted small" style={{ marginTop: '0.5rem' }}>
              {(artifacts?.tasks || []).length} tasks in backlog
            </p>
          </section>

          <section className="p5-panel">
            <div className="p5-section-head">
              <h2>Timeline</h2>
            </div>
            {Array.isArray(timeline) && timeline.length > 0 ? (
              <div className="p5-timeline">
                {timeline.map((m, i) => (
                  <div key={i} className="p5-timeline-item">
                    <strong>{m.label || m.name || m.phase}</strong>
                    <span className="muted small">
                      {m.date || m.week || m.duration || ''}
                    </span>
                  </div>
                ))}
              </div>
            ) : forecast?.critical_path?.length ? (
              <ul className="p5-list">
                {forecast.critical_path.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">
                Timeline from PM forecast appears after pipeline. Critical path:{' '}
                {(forecast?.critical_path || []).join(' → ') || '—'}
              </p>
            )}
          </section>
        </>
      )}
    </div>
  )
}
