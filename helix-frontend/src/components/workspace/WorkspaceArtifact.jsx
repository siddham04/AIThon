import { lazy, Suspense } from 'react'
import ReactMarkdown from 'react-markdown'

const MermaidView = lazy(() => import('../studio/MermaidView'))

function hasMermaidSource(diagram) {
  const src = diagram?.mermaid_layers || diagram?.mermaid || ''
  return typeof src === 'string' && src.trim().length > 0
}

function SprintArtifact({ plan }) {
  if (!plan) return <p className="muted small">No sprint plan data yet.</p>
  const tasks = plan.tasks || []
  return (
    <div className="ws-artifact-sprint">
      <div className="ws-artifact-meta">
        <span>
          <strong>{plan.total_story_points ?? '—'}</strong> story points
        </span>
        <span>Suggested: <strong>{plan.suggested_sprint || 'Sprint 1'}</strong></span>
        <span>{tasks.length} tasks</span>
      </div>
      <div className="ws-artifact-scroll">
        <table className="ws-table">
          <thead>
            <tr>
              <th>Task</th>
              <th>Points</th>
              <th>Priority</th>
              <th>Sprint</th>
            </tr>
          </thead>
          <tbody>
            {tasks.slice(0, 24).map((t, i) => (
              <tr key={t.id || i}>
                <td>{t.title}</td>
                <td>{t.story_points ?? '—'}</td>
                <td>{t.priority || 'medium'}</td>
                <td>{t.suggested_sprint || plan.suggested_sprint || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function RisksArtifact({ risk, projectRisks }) {
  const reasons = risk?.reasons || []
  const items = projectRisks?.length ? projectRisks : []
  return (
    <div className="ws-artifact-risks">
      {risk?.risk_level && (
        <p className="ws-risk-level">
          Overall: <strong>{risk.risk_level}</strong>
          {risk.payment_gateway_detected ? ' · ⚠ Payment gateway' : ''}
        </p>
      )}
      <ul className="ws-risk-list">
        {reasons.map((r, i) => (
          <li key={`r-${i}`}>{typeof r === 'string' ? r : r}</li>
        ))}
        {items.slice(0, 12).map((r) => (
          <li key={r.id}>
            <strong>{r.title || r.category}</strong>
            {r.description ? ` — ${r.description}` : ''}
          </li>
        ))}
      </ul>
    </div>
  )
}

function TestsArtifact({ cases }) {
  if (!cases?.length) return <p className="muted small">No test cases yet.</p>
  return (
    <ul className="ws-test-list">
      {cases.slice(0, 16).map((tc) => (
        <li key={tc.id}>
          <strong>{tc.title || tc.name}</strong>
          {tc.priority && <span className="ws-tag">{tc.priority}</span>}
        </li>
      ))}
      {cases.length > 16 && (
        <li className="muted small">+{cases.length - 16} more</li>
      )}
    </ul>
  )
}

function EffortArtifact({ effort }) {
  if (!effort) return null
  return (
    <dl className="ws-effort-grid">
      <div>
        <dt>Story points</dt>
        <dd>{effort.story_points ?? effort.total_story_points ?? '—'}</dd>
      </div>
      <div>
        <dt>Complexity</dt>
        <dd>{effort.complexity || '—'}</dd>
      </div>
      <div>
        <dt>Est. hours</dt>
        <dd>{Math.round(effort.estimated_hours ?? 0)}</dd>
      </div>
      <div>
        <dt>Team velocity</dt>
        <dd>{effort.team_velocity ?? '—'}</dd>
      </div>
    </dl>
  )
}

export default function WorkspaceArtifact({ artifact }) {
  if (!artifact) return null

  const showMermaid =
    artifact.type === 'architecture' && hasMermaidSource(artifact.diagram)

  return (
    <div className="ws-artifact">
      {artifact.type === 'architecture' && (
        <>
          {artifact.diagram?.tree_text && (
            <pre className="ws-arch-tree">{artifact.diagram.tree_text}</pre>
          )}
          {showMermaid && (
            <div className="ws-mermaid-wrap">
              <Suspense fallback={<p className="muted small">Loading diagram…</p>}>
                <MermaidView
                  source={
                    artifact.diagram.mermaid_layers || artifact.diagram.mermaid || ''
                  }
                />
              </Suspense>
            </div>
          )}
        </>
      )}
      {artifact.type === 'sprint' && <SprintArtifact plan={artifact.plan} />}
      {artifact.type === 'risks' && (
        <RisksArtifact risk={artifact.risk} projectRisks={artifact.projectRisks} />
      )}
      {artifact.type === 'tests' && <TestsArtifact cases={artifact.cases} />}
      {artifact.type === 'effort' && <EffortArtifact effort={artifact.effort} />}
    </div>
  )
}

export function MarkdownAnswer({ text }) {
  if (!text) return null
  return (
    <div className="ws-markdown">
      <ReactMarkdown>{text}</ReactMarkdown>
    </div>
  )
}
