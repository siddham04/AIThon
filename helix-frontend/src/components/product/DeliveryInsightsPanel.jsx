/**
 * Quality score + multi-agent review summary on Delivery Package.
 */
export default function DeliveryInsightsPanel({ quality, reviewBoard }) {
  if (!quality && !reviewBoard) return null

  const qScore = quality?.overall_score ?? quality?.quality_score
  const grade = quality?.grade
  const reviews = reviewBoard?.reviews || []
  const confidence = reviewBoard?.confidence
  const boardGrade = reviewBoard?.grade

  return (
    <section className="p5-panel hx-delivery-insights">
      <h2>Requirement quality &amp; review</h2>
      <p className="muted small">
        Layered heuristic + AI scoring and parallel specialist review from the demo pipeline.
      </p>
      <div className="hx-delivery-insights-grid">
        {quality && (
          <div className="hx-insight-card">
            <span className="hx-insight-label">Quality score</span>
            <strong className="hx-insight-value">
              {qScore != null ? `${Math.round(qScore)}%` : '—'}
              {grade ? ` · ${grade}` : ''}
            </strong>
            {quality.highlight_gaps?.length > 0 && (
              <ul className="muted small hx-insight-list">
                {quality.highlight_gaps.slice(0, 4).map((g) => (
                  <li key={g}>{g}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        {reviewBoard && (
          <div className="hx-insight-card">
            <span className="hx-insight-label">Review board</span>
            <strong className="hx-insight-value">
              {confidence != null ? `${Math.round(confidence)}% confidence` : 'Complete'}
              {boardGrade ? ` · ${boardGrade}` : ''}
            </strong>
            {reviews.length > 0 && (
              <ul className="muted small hx-insight-list">
                {reviews.slice(0, 5).map((r) => (
                  <li key={r.agent || r.role}>
                    <strong>{r.agent || r.role || 'Agent'}</strong>
                    {r.score != null ? ` — ${Math.round(r.score)}%` : ''}
                    {r.summary ? `: ${String(r.summary).slice(0, 80)}` : ''}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
