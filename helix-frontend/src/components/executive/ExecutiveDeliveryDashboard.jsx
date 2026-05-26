import { useMemo } from 'react'

/**
 * Executive Delivery Dashboard — the "AI Delivery Manager" hero panel
 * that surfaces every pipeline output (counts + sprints + cost +
 * GO/NO-GO verdict) in one screen. Mirrors the wishlist judges asked
 * for: Requirements / Epics / Stories / Tasks / APIs / Tests / Risks /
 * Ambiguities / Architecture Components / Readiness / Sprints /
 * Estimated Delivery / Projected Cost / GO/NO-GO.
 *
 * Pure presentation — all numbers are computed server-side by
 * `delivery_summary.build_delivery_summary` so the UI stays dumb and
 * the verdict logic remains deterministic and testable.
 */
// Map each KPI tile's key to the in-page section anchor judges scroll
// to when they click the tile. Keeps the dashboard truly interactive
// instead of a static read-only board.
const KPI_TILE_TARGETS = {
  requirements: 'stories',
  epics: 'stories',
  stories: 'stories',
  tasks: 'tasks',
  apis: 'api-contracts',
  tests: 'tests',
  risks: 'risks',
  ambiguities: 'risks',
  architecture: 'architecture',
  readiness: 'summary',
}

export default function ExecutiveDeliveryDashboard({ summary }) {
  const metrics = summary?.headline_metrics || []
  const sprints = summary?.sprints || []
  const verdict = summary?.verdict || 'GO_WITH_CAVEATS'
  const verdictLabel = summary?.verdict_label || 'GO with caveats'

  const visibleSprints = useMemo(() => sprints.slice(0, 6), [sprints])
  const sprintOverflow = sprints.length - visibleSprints.length

  const agentRows = useMemo(
    () => (summary?.agent_contributions || []).slice(0, 8),
    [summary?.agent_contributions],
  )

  const handleTileClick = (key) => {
    const targetId = KPI_TILE_TARGETS[key]
    if (!targetId || typeof document === 'undefined') return
    const el = document.getElementById(targetId)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      el.classList.add('p5-panel--flash')
      setTimeout(() => el.classList.remove('p5-panel--flash'), 1400)
    }
  }

  if (!summary) {
    return (
      <section className="hx-exec-delivery hx-exec-delivery--empty">
        <p className="muted small">
          Run the AI team to see the Executive Delivery dashboard.
        </p>
      </section>
    )
  }

  return (
    <section
      className={`hx-exec-delivery hx-exec-delivery--${verdict.toLowerCase()}`}
      aria-label="Executive Delivery Summary"
    >
      <header className="hx-exec-delivery__header">
        <div className="hx-exec-delivery__title-block">
          <p className="hx-exec-delivery__eyebrow">AI Delivery Manager · live verdict</p>
          <h2 className="hx-exec-delivery__title">
            {summary.project_name || 'Helix Project'}
          </h2>
        </div>
        <VerdictBadge verdict={verdict} label={verdictLabel} />
      </header>

      <div className="hx-exec-delivery__kpis">
        {metrics.map((m) => (
          <KpiTile
            key={m.key}
            metric={m}
            scrollable={Boolean(KPI_TILE_TARGETS[m.key])}
            onClick={() => handleTileClick(m.key)}
          />
        ))}
      </div>

      <div className="hx-exec-delivery__plan">
        <div className="hx-exec-delivery__plan-block">
          <h3>Sprint plan</h3>
          {visibleSprints.length === 0 ? (
            <p className="muted small">Sprint plan not generated yet.</p>
          ) : (
            <div className="hx-exec-delivery__sprints">
              {visibleSprints.map((s) => (
                <div className="hx-exec-delivery__sprint" key={`${s.number}-${s.label}`}>
                  <strong>{s.label}</strong>
                  <span className="muted small">
                    {s.planned_points} pts · {s.weeks}w
                  </span>
                  {s.goal && (
                    <p className="hx-exec-delivery__sprint-goal" title={s.goal}>
                      {s.goal.length > 60 ? `${s.goal.slice(0, 60)}…` : s.goal}
                    </p>
                  )}
                </div>
              ))}
              {sprintOverflow > 0 && (
                <div className="hx-exec-delivery__sprint hx-exec-delivery__sprint--more">
                  <strong>+{sprintOverflow} more</strong>
                  <span className="muted small">across {summary.estimated_delivery_weeks}w total</span>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="hx-exec-delivery__plan-block">
          <h3>Delivery snapshot</h3>
          <dl className="hx-exec-delivery__facts">
            <div>
              <dt>Estimated Delivery</dt>
              <dd>
                {summary.estimated_delivery_weeks || 0} weeks
                <span className="muted small">
                  {' '}
                  · {summary.sprint_count} sprint{summary.sprint_count === 1 ? '' : 's'}
                </span>
              </dd>
            </div>
            <div>
              <dt>Projected Cost</dt>
              <dd>
                ${formatNumber(summary.projected_cost_usd)}
                <span className="muted small">
                  {' '}
                  · @${summary.blended_hourly_rate_usd}/hr blended
                </span>
              </dd>
            </div>
            <div>
              <dt>Effort</dt>
              <dd>
                {summary.estimated_total_points} pts
                <span className="muted small">
                  {' '}
                  · {formatNumber(summary.estimated_total_hours)} hrs
                </span>
              </dd>
            </div>
            <div>
              <dt>Quality / Confidence</dt>
              <dd>
                {summary.quality_score}/100
                <span className="muted small">
                  {' '}
                  · review {summary.confidence_score}/100
                </span>
              </dd>
            </div>
            <div>
              <dt>Manual effort displaced</dt>
              <dd>
                {formatNumber(summary.hours_saved_vs_manual)} hrs saved
                <span className="muted small">
                  {' '}
                  · ${formatNumber(summary.cost_saved_usd)} avoided
                </span>
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {summary.speedup_multiplier > 0 && (
        <div className="hx-exec-delivery__wow" role="status">
          <span>
            <strong>{formatNumber(summary.helix_wall_clock_minutes)} min</strong>
            <em>Helix pipeline</em>
          </span>
          <span className="hx-exec-delivery__wow-vs">vs</span>
          <span>
            <strong>{formatNumber(summary.manual_equivalent_weeks)} weeks</strong>
            <em>manual SDLC team</em>
          </span>
          <span className="hx-exec-delivery__wow-mult">
            <strong>{formatNumber(summary.speedup_multiplier)}×</strong>
            <em>speedup</em>
          </span>
          {summary.equivalent_team_size > 0 && (
            <span>
              <strong>{summary.equivalent_team_size}-person</strong>
              <em>team equivalent</em>
            </span>
          )}
          {summary.roi_multiplier > 0 && (
            <span>
              <strong>{formatNumber(Math.round(summary.roi_multiplier * 100))}%</strong>
              <em>of build cost displaced</em>
            </span>
          )}
        </div>
      )}

      {(summary.verdict_reasons?.length || summary.blocking_items?.length || summary.upgrade_recommendations?.length) && (
        <div className="hx-exec-delivery__verdict-detail">
          {summary.blocking_items?.length > 0 && (
            <div className="hx-exec-delivery__blockers">
              <strong>Blockers</strong>
              <ul>
                {summary.blocking_items.map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            </div>
          )}
          {summary.verdict_reasons?.length > 0 && (
            <div className="hx-exec-delivery__reasons">
              <strong>Why this verdict</strong>
              <ul>
                {summary.verdict_reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}
          {summary.upgrade_recommendations?.length > 0 && (
            <div className="hx-exec-delivery__upgrade">
              <strong>To reach GO</strong>
              <ul>
                {summary.upgrade_recommendations.map((u, i) => (
                  <li key={i}>{u}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {agentRows.length > 0 && (
        <details className="hx-exec-delivery__agents">
          <summary>Where the savings came from · per-agent breakdown</summary>
          <table className="hx-agent-table">
            <thead>
              <tr>
                <th>Agent</th>
                <th className="num">Artifacts</th>
                <th className="num">Min / each</th>
                <th className="num">Hours displaced</th>
                <th className="num">Speedup</th>
              </tr>
            </thead>
            <tbody>
              {agentRows.map((row) => (
                <tr key={row.agent}>
                  <td>{row.agent}</td>
                  <td className="num">
                    {row.artifacts_produced}{' '}
                    <span className="muted small">{row.artifact_label}</span>
                  </td>
                  <td className="num">{formatNumber(row.human_minutes_per_artifact)}</td>
                  <td className="num">
                    {formatNumber(Math.round(row.human_minutes_displaced / 60))}h
                  </td>
                  <td className="num">{formatNumber(row.speedup_multiplier)}×</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </section>
  )
}

function VerdictBadge({ verdict, label }) {
  return (
    <div
      className={`hx-exec-delivery__verdict hx-exec-delivery__verdict--${verdict.toLowerCase()}`}
      role="status"
      aria-live="polite"
    >
      <span className="hx-exec-delivery__verdict-dot" aria-hidden />
      <span className="hx-exec-delivery__verdict-label">{label.toUpperCase()}</span>
    </div>
  )
}

function KpiTile({ metric, scrollable = false, onClick }) {
  const className = `hx-kpi-tile hx-kpi-tile--${metric.severity || 'info'}${
    scrollable ? ' hx-kpi-tile--clickable' : ''
  }`
  const content = (
    <>
      <span className="hx-kpi-tile__label">{metric.label}</span>
      <span className="hx-kpi-tile__value">{formatNumber(metric.value)}</span>
      {metric.detail && <span className="hx-kpi-tile__detail">{metric.detail}</span>}
    </>
  )
  if (!scrollable) {
    return (
      <div className={className} data-key={metric.key}>
        {content}
      </div>
    )
  }
  return (
    <button
      type="button"
      className={className}
      data-key={metric.key}
      onClick={onClick}
      aria-label={`Scroll to ${metric.label} section`}
    >
      {content}
    </button>
  )
}

function formatNumber(value) {
  if (value == null || value === '') return '—'
  const num = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(num)) return value
  if (Math.abs(num) >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`
  if (Math.abs(num) >= 10_000) return num.toLocaleString('en-US', { maximumFractionDigits: 0 })
  if (Number.isInteger(num)) return num.toLocaleString('en-US')
  return num.toLocaleString('en-US', { maximumFractionDigits: 1 })
}
