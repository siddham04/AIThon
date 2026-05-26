import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import toast from 'react-hot-toast'
import { api } from '../api/client'
import { DEFAULT_SHOWCASE_PROJECT_ID, resolveDemoUseAi } from '../lib/demoConfig'
import { loadWorkspaceData } from '../lib/loadWorkspaceData'
import ApprovalChecklist from '../components/product/ApprovalChecklist'
import ExecutiveDeliveryDashboard from '../components/executive/ExecutiveDeliveryDashboard'
import JiraCsvPreview from '../components/export/JiraCsvPreview'
import JiraPushPanel from '../components/export/JiraPushPanel'
import TraceabilityFlowAnimator from '../components/traceability/TraceabilityFlowAnimator'
import DeliveryInsightsPanel from '../components/product/DeliveryInsightsPanel'
import { APPROVE_EXPORT_CTA, POSITIONING_LINE } from '../lib/productMessaging'
import { readAuthToken } from '../lib/authTokenStorage'

export default function AiWorkspace() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [regenerating, setRegenerating] = useState(false)
  const [project, setProject] = useState(null)
  const [artifacts, setArtifacts] = useState(null)
  const [tests, setTests] = useState([])
  const [readiness, setReadiness] = useState(null)
  const [effort, setEffort] = useState(null)
  const [risk, setRisk] = useState(null)
  const [sprintPlan, setSprintPlan] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [approved, setApproved] = useState(false)
  const [prd, setPrd] = useState(null)
  const [quality, setQuality] = useState(null)
  const [reviewBoard, setReviewBoard] = useState(null)
  const [architectureDiagram, setArchitectureDiagram] = useState(null)
  const [apiContracts, setApiContracts] = useState(null)
  const [deliverySummary, setDeliverySummary] = useState(null)

  const applySlice = useCallback((data) => {
    if (!data) return
    if (data.project) setProject(data.project)
    if (data.artifacts !== undefined) setArtifacts(data.artifacts)
    if (data.tests !== undefined) setTests(data.tests)
    if (data.readiness !== undefined) setReadiness(data.readiness)
    if (data.effort !== undefined) setEffort(data.effort)
    if (data.risk !== undefined) setRisk(data.risk)
    if (data.sprintPlan !== undefined) setSprintPlan(data.sprintPlan)
    if (data.prd !== undefined) setPrd(data.prd)
    if (data.quality !== undefined) setQuality(data.quality)
    if (data.reviewBoard !== undefined) setReviewBoard(data.reviewBoard)
    if (data.architectureDiagram !== undefined) setArchitectureDiagram(data.architectureDiagram)
    if (data.apiContracts !== undefined) setApiContracts(data.apiContracts)
    if (data.deliverySummary !== undefined) setDeliverySummary(data.deliverySummary)
    if (data.approved !== undefined) setApproved(data.approved)
  }, [])

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      const data = await loadWorkspaceData(id, {
        onPartial: (partial) => {
          applySlice(partial)
          if (partial.project && !partial.loadingSlices) {
            setLoading(false)
          }
        },
      })
      if (!data.project) {
        toast.error('Could not load project')
        return
      }
      applySlice(data)
      if (data.failed > 0) {
        toast.error(`Some sections failed to load (${data.failed}) — showing partial package`)
      }
    } catch {
      toast.error('Could not load AI workspace')
    } finally {
      setLoading(false)
    }
  }, [id, applySlice])

  useEffect(() => {
    if (!id) return undefined
    let cancelled = false
    ;(async () => {
      try {
        const data = await loadWorkspaceData(id, {
          onPartial: (partial) => {
            if (cancelled) return
            applySlice(partial)
            if (partial.project && !partial.loadingSlices) setLoading(false)
          },
        })
        if (cancelled) return
        if (!data.project) {
          toast.error('Could not load project')
          return
        }
        applySlice(data)
        if (data.failed > 0) {
          toast.error(
            `Some sections failed to load (${data.failed}) — showing partial package`,
          )
        }
      } catch {
        if (!cancelled) toast.error('Could not load AI workspace')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id, applySlice])

  const approveAll = async () => {
    const stories = artifacts?.stories || []
    if (!stories.length) {
      toast.error('No stories to approve — run the AI team first')
      return false
    }
    try {
      await Promise.all(
        stories.map((s) =>
          api.patch(`/artifacts/${id}/stories/${s.id}/approval`, {
            approved_for_export: true,
          }),
        ),
      )
      setApproved(true)
      return true
    } catch {
      toast.error('Approval failed')
      return false
    }
  }

  const downloadExport = async (kind) => {
    setExporting(true)
    try {
      if (kind === 'jira') {
        const ok = await approveAll()
        if (!ok) return
        const { data } = await api.get(`/backlog/${id}/jira-csv`, { responseType: 'text' })
        const blob = new Blob([data], { type: 'text/csv' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `helix-${id}-jira.csv`
        a.click()
        URL.revokeObjectURL(url)
        toast.success('Jira CSV downloaded')
        return
      }
      if (kind === 'ado') {
        const { data } = await api.get(`/backlog/${id}/ado-csv`, { responseType: 'text' })
        const blob = new Blob([data], { type: 'text/csv' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `helix-${id}-ado.csv`
        a.click()
        URL.revokeObjectURL(url)
        toast.success('Azure DevOps CSV downloaded')
        return
      }
      if (kind === 'md') {
        const { data } = await api.get(`/export/markdown/${id}`, { responseType: 'text' })
        const blob = new Blob([data], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `helix-${id}.md`
        a.click()
        URL.revokeObjectURL(url)
        toast.success('Markdown export downloaded')
        return
      }
      if (kind === 'json') {
        const { data } = await api.get(`/export/json/${id}`)
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `helix-${id}.json`
        a.click()
        URL.revokeObjectURL(url)
        toast.success('Full project JSON downloaded')
        return
      }
      if (kind === 'backlog') {
        const { data } = await api.get(`/backlog/${id}/json`, { responseType: 'text' })
        const blob = new Blob([data], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `helix-${id}-backlog.json`
        a.click()
        URL.revokeObjectURL(url)
        toast.success('Backlog JSON downloaded')
        return
      }
      if (kind === 'tasks') {
        const { data } = await api.get(`/export/csv/${id}`, { responseType: 'text' })
        const blob = new Blob([data], { type: 'text/csv' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `helix-${id}-tasks.csv`
        a.click()
        URL.revokeObjectURL(url)
        toast.success('Tasks CSV downloaded')
      }
    } catch {
      toast.error('Export failed')
    } finally {
      setExporting(false)
    }
  }

  const approveAndExport = async () => {
    await downloadExport('jira')
    await load()
    // Echo the AI Delivery Manager's verdict next to the download
    // toast so judges immediately see "GO" / "GO with caveats" /
    // "NO-GO" at the moment they hit Approve & Export. The dashboard
    // also re-renders at the top of the page after the load() above.
    if (deliverySummary?.verdict_label) {
      const verdict = deliverySummary.verdict
      const msg = `Delivery verdict: ${deliverySummary.verdict_label.toUpperCase()}`
      if (verdict === 'GO') toast.success(msg)
      else if (verdict === 'NO_GO') toast.error(msg)
      else toast(msg, { icon: '⚠' })
    }
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  const regenerate = async () => {
    if (!window.confirm('Regenerate full SDLC output? This re-runs the AI team.')) return
    setRegenerating(true)
    try {
      const token = readAuthToken()
      const base = import.meta.env.VITE_API_BASE?.replace(/\/$/, '') || '/api'
      const root = base.startsWith('http') ? base : `${window.location.origin}${base}`
      const res = await fetch(`${root}/demo/${id}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ use_ai: resolveDemoUseAi(true) }),
      })
      if (!res.ok) throw new Error('Pipeline failed')
      const reader = res.body?.getReader()
      const dec = new TextDecoder()
      let buf = ''
      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buf += dec.decode(value, { stream: true })
          if (buf.includes('"step": "complete"') || buf.includes('"step":"complete"')) break
        }
      }
      toast.success('Regeneration complete')
      await load()
    } catch (e) {
      toast.error(e?.message || 'Regenerate failed')
    } finally {
      setRegenerating(false)
    }
  }

  if (!id) {
    const showcase = DEFAULT_SHOWCASE_PROJECT_ID
    return (
      <div className="p5-page p5-empty">
        <h1>Delivery Package</h1>
        <p className="muted">
          Nothing to show until a pipeline runs. Open the pre-baked showcase package for judges, or
          start your own run.
        </p>
        <div className="p5-empty-actions">
          <Link to={`/project/${showcase}/ai-workspace`} className="btn btn-primary">
            Open showcase package
          </Link>
          <Link to="/judge-demo" className="btn ghost">
            Start Judge Demo
          </Link>
          <Link to="/mission-control" className="btn ghost small">
            Mission Control (custom upload)
          </Link>
        </div>
      </div>
    )
  }

  const stories = artifacts?.stories || []
  const tasks = artifacts?.tasks || []
  const summary = artifacts?.summary
  const riskCount =
    (risk?.reasons?.length || 0) + (project?.risks?.length || 0)
  // The backend's AutoSprintPlan model exposes { tasks, total_story_points,
  // suggested_sprint, suggested_sprint_number, sprint_capacity }; the legacy
  // TeamSprintPlan model used { sprints | plan | total_sprints }. We check
  // both shapes so the workspace checklist flips green whichever endpoint
  // populated `sprintPlan` (was previously stuck at "pending" for every
  // AutoSprintPlan because we only checked legacy field names).
  const sprintReady =
    Boolean(sprintPlan?.tasks?.length) ||
    Boolean(sprintPlan?.total_story_points) ||
    Boolean(sprintPlan?.suggested_sprint) ||
    Boolean(sprintPlan?.sprints?.length) ||
    Boolean(sprintPlan?.plan?.length) ||
    Boolean(sprintPlan?.total_sprints)

  const checklistItems = [
    {
      id: 'stories',
      label: 'Stories generated',
      done: stories.length > 0,
      detail: stories.length ? `${stories.length}` : 'pending',
    },
    {
      id: 'tasks',
      label: 'Tasks generated',
      done: tasks.length > 0,
      detail: tasks.length ? `${tasks.length}` : 'pending',
    },
    {
      id: 'tests',
      label: 'Test cases generated',
      done: tests.length > 0,
      detail: tests.length ? `${tests.length}` : 'pending',
    },
    {
      id: 'sprint',
      label: 'Sprint plan generated',
      done: sprintReady,
      detail: sprintReady ? 'ready' : 'pending',
    },
    {
      id: 'risks',
      label: 'Risks detected',
      done: riskCount > 0,
      detail: riskCount ? `${riskCount} flagged` : 'none yet',
    },
  ]

  const pipelineReady = checklistItems.some((i) => i.done)
  const needsPipeline =
    !loading && !pipelineReady && (!artifacts || !stories.length)

  return (
    <div className="p5-page">
      {needsPipeline && (
        <section className="p5-panel p5-empty-run" role="alert">
          <h2>AI team has not run yet</h2>
          <p className="muted">
            This project has no artifacts yet. Judges: use <strong>Judge Demo</strong> or open the
            showcase backup — no empty wait on stage.
          </p>
          <div className="p5-empty-actions">
            <Link to="/judge-demo" className="btn btn-primary">
              Judge Demo →
            </Link>
            <Link
              to={`/project/${DEFAULT_SHOWCASE_PROJECT_ID}/ai-workspace`}
              className="btn ghost"
            >
              Showcase package
            </Link>
            <Link to={`/project/${id}/mission-control`} className="btn ghost small">
              Mission Control
            </Link>
          </div>
        </section>
      )}

      <header className="p5-hero">
        <p className="p5-eyebrow">Autonomous by default · human approves</p>
        <h1>{project?.name || 'AI Workspace'}</h1>
        <p className="muted small">{POSITIONING_LINE}</p>
      </header>

      {loading && <p className="muted">Loading AI output…</p>}

      {!loading && (
        <>
          {/* AI Delivery Manager hero: one-screen GO/NO-GO verdict with
              counts (Requirements / Epics / Stories / Tasks / APIs /
              Tests / Risks / Ambiguities / Architecture Components /
              Readiness), sprint plan tiles, delivery snapshot (weeks,
              cost, value displaced), and reasons/blockers. Rendered
              before the checklist so judges see the verdict first. */}
          {deliverySummary && (
            <ExecutiveDeliveryDashboard summary={deliverySummary} />
          )}

          {tasks.length > 0 && (
            <p className="hx-tasks-banner" role="status">
              <strong>{tasks.length} engineering tasks</strong> linked to stories — Jira export
              includes Task rows (sprint-ready backlog, not stories-only).
            </p>
          )}

          <ApprovalChecklist items={checklistItems} approved={approved} />

          <DeliveryInsightsPanel quality={quality} reviewBoard={reviewBoard} />

          <div className="hx-approval-cta-wrap">
            <button type="button" className="btn ghost small" onClick={() => void load()}>
              Refresh
            </button>
            <button
              type="button"
              className="btn ghost small"
              onClick={() => void regenerate()}
              disabled={regenerating}
            >
              {regenerating ? 'Regenerating…' : 'Regenerate AI output'}
            </button>
            <button
              type="button"
              className="btn ghost small"
              onClick={() => navigate(`/project/${id}/delivery-command`)}
            >
              Delivery Center →
            </button>
          </div>
          {pipelineReady && (
            <section className="p5-panel hx-export-hub">
              <h2>Export &amp; handoff</h2>
              <p className="muted small">
                Jira CSV, ADO CSV, Markdown brief, and full JSON — not CSV-only.
              </p>
              <div className="hx-export-hub-actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={exporting}
                  onClick={() => void approveAndExport()}
                >
                  {exporting ? 'Exporting…' : APPROVE_EXPORT_CTA}
                </button>
                <button
                  type="button"
                  className="btn ghost"
                  disabled={exporting}
                  onClick={() => void downloadExport('ado')}
                >
                  ADO CSV
                </button>
                <button
                  type="button"
                  className="btn ghost"
                  disabled={exporting}
                  onClick={() => void downloadExport('md')}
                >
                  Markdown
                </button>
                <button
                  type="button"
                  className="btn ghost"
                  disabled={exporting}
                  onClick={() => void downloadExport('json')}
                >
                  Project JSON
                </button>
                <button
                  type="button"
                  className="btn ghost"
                  disabled={exporting}
                  onClick={() => void downloadExport('backlog')}
                >
                  Backlog JSON
                </button>
                <button
                  type="button"
                  className="btn ghost"
                  disabled={exporting}
                  onClick={() => void downloadExport('tasks')}
                >
                  Tasks CSV
                </button>
              </div>
            </section>
          )}

          {pipelineReady && (
            <>
              <TraceabilityFlowAnimator key={id} projectId={id} />
              <JiraCsvPreview projectId={id} enabled={pipelineReady} />
              <JiraPushPanel projectId={id} disabled={!pipelineReady} />
            </>
          )}

          <section className="p5-panel" id="summary">
            <div className="p5-section-head">
              <h2>Executive Summary</h2>
            </div>
            {prd?.executive_summary ? (
              <ReactMarkdown>{prd.executive_summary}</ReactMarkdown>
            ) : summary?.objective ? (
              <ReactMarkdown>{summary.objective}</ReactMarkdown>
            ) : prd?.one_liner ? (
              <p>{prd.one_liner}</p>
            ) : (
              <p className="muted">Run the AI team from Mission Control.</p>
            )}
          </section>

          <section className="p5-panel" id="stories">
            <div className="p5-section-head">
              <h2>User Stories ({stories.length})</h2>
            </div>
            {stories.length === 0 ? (
              <p className="muted">No stories yet.</p>
            ) : (
              <ul className="p5-list">
                {stories.map((s) => (
                  <li key={s.id}>
                    <strong>{s.title}</strong>
                    {s.approved_for_export && (
                      <span className="muted small"> · approved</span>
                    )}
                    <p className="muted small">
                      As a {s.persona}, I want {s.goal}, so that {s.benefit}.
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="p5-panel" id="tasks">
            <div className="p5-section-head">
              <h2>Tasks ({tasks.length})</h2>
            </div>
            {tasks.length === 0 ? (
              <p className="muted">No engineering tasks yet — Scrum step may need another run.</p>
            ) : (
              <ul className="p5-list">
                {tasks.map((t) => (
                  <li key={t.id}>
                    <strong>{t.title}</strong>
                    <span className="muted small">
                      {' '}
                      · {t.type} · {t.priority}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="p5-panel" id="architecture">
            <div className="p5-section-head">
              <h2>Architecture</h2>
              {architectureDiagram?.nodes_count != null && (
                <span className="muted small">
                  {(architectureDiagram.layers || []).length} layers ·{' '}
                  {architectureDiagram.nodes_count} nodes
                </span>
              )}
            </div>
            {!architectureDiagram ? (
              <p className="muted">
                Architecture appears after the pipeline runs (frontend · backend ·
                database layers plus a Mermaid diagram).
              </p>
            ) : (
              <>
                {(architectureDiagram.layers || []).length > 0 && (
                  <div className="p5-arch-layers">
                    {architectureDiagram.layers.map((layer) => (
                      <div key={layer.name} className="p5-arch-layer">
                        <strong>{layer.name}</strong>
                        <ul className="p5-list p5-list--inline">
                          {(layer.items || []).map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}
                {architectureDiagram.mermaid && (
                  <details className="p5-mermaid-details">
                    <summary>Mermaid diagram (raw)</summary>
                    <pre className="p5-code-block">
                      {architectureDiagram.mermaid}
                    </pre>
                  </details>
                )}
                {architectureDiagram.tree_text && (
                  <details className="p5-mermaid-details">
                    <summary>Component tree</summary>
                    <pre className="p5-code-block">
                      {architectureDiagram.tree_text}
                    </pre>
                  </details>
                )}
              </>
            )}
          </section>

          <section className="p5-panel" id="api-contracts">
            <div className="p5-section-head">
              <h2>API Contracts ({(apiContracts?.contracts || []).length})</h2>
            </div>
            {!apiContracts || !(apiContracts.contracts || []).length ? (
              <p className="muted">
                API contracts appear after the pipeline runs (REST endpoints
                derived from each user story).
              </p>
            ) : (
              <ul className="p5-list p5-list--apis">
                {apiContracts.contracts.slice(0, 16).map((c, i) => (
                  <li key={`${c.method}-${c.endpoint}-${i}`}>
                    <code className={`p5-api-method p5-api-method--${(c.method || 'get').toLowerCase()}`}>
                      {c.method || 'GET'}
                    </code>
                    <code className="p5-api-endpoint">{c.endpoint}</code>
                    {c.description && (
                      <span className="muted small"> · {c.description}</span>
                    )}
                  </li>
                ))}
                {apiContracts.contracts.length > 16 && (
                  <li className="muted small">
                    + {apiContracts.contracts.length - 16} more — export OpenAPI for the full list
                  </li>
                )}
              </ul>
            )}
          </section>

          <section className="p5-panel" id="tests">
            <div className="p5-section-head">
              <h2>Test Cases ({tests.length})</h2>
            </div>
            {tests.length === 0 ? (
              <p className="muted">No tests yet.</p>
            ) : (
              <ul className="p5-list">
                {tests.slice(0, 12).map((t) => (
                  <li key={t.id}>
                    <strong>{t.title}</strong>
                    <span className="muted small"> · {t.type}</span>
                  </li>
                ))}
                {tests.length > 12 && (
                  <li className="muted small">+ {tests.length - 12} more</li>
                )}
              </ul>
            )}
          </section>

          <section className="p5-panel" id="risks">
            <div className="p5-section-head">
              <h2>Risks</h2>
            </div>
            <ul className="p5-list">
              {(risk?.reasons || project?.risks?.map((r) => r.title) || [])
                .slice(0, 8)
                .map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
            </ul>
            {!risk?.reasons?.length && !project?.risks?.length && (
              <p className="muted">No risks flagged.</p>
            )}
          </section>

          <section className="p5-panel" id="estimates">
            <div className="p5-section-head">
              <h2>Estimates</h2>
            </div>
            {effort ? (
              <p>
                <strong>{effort.story_points ?? effort.total_story_points ?? '—'}</strong> story points
                {effort.estimated_weeks != null && (
                  <span className="muted"> · ~{effort.estimated_weeks} weeks</span>
                )}
                {readiness?.readiness != null && (
                  <span className="muted"> · readiness {readiness.readiness}%</span>
                )}
              </p>
            ) : (
              <p className="muted">Estimates appear after pipeline run.</p>
            )}
          </section>
        </>
      )}
    </div>
  )
}
