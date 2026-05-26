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
export default function ExecutiveDeliveryDashboard({ summary }) {
  const metrics = summary?.headline_metrics || []
  const sprints = summary?.sprints || []
  const verdict = summary?.verdict || 'GO_WITH_CAVEATS'
  const verdictLabel = summary?.verdict_label || 'GO with caveats'

  const visibleSprints = useMemo(() => sprints.slice(0, 6), [sprints])
  const sprintOverflow = sprints.length - visibleSprints.length

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
          <KpiTile key={m.key} metric={m} />
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

      {(summary.verdict_reasons?.length || summary.blocking_items?.length) && (
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
        </div>
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

function KpiTile({ metric }) {
  return (
    <div
      className={`hx-kpi-tile hx-kpi-tile--${metric.severity || 'info'}`}
      data-key={metric.key}
    >
      <span className="hx-kpi-tile__label">{metric.label}</span>
      <span className="hx-kpi-tile__value">{formatNumber(metric.value)}</span>
      {metric.detail && <span className="hx-kpi-tile__detail">{metric.detail}</span>}
    </div>
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
