function level(score) {
  if (score >= 0.7) return 'high'
  if (score >= 0.45) return 'medium'
  return 'low'
}

export default function AmbiguityView({ text, hits }) {
  if (!text) {
    return <p className="muted">No requirement text loaded for this session.</p>
  }
  if (!hits?.length) {
    return <p className="muted">No ambiguities detected. Run analysis from the toolbar.</p>
  }

  const segments = []
  let cursor = 0
  const sorted = [...hits].sort((a, b) => b.span.length - a.span.length)

  const ranges = []
  for (const h of sorted) {
    const span = h.span
    if (!span) continue
    let idx = text.indexOf(span, cursor)
    if (idx === -1) idx = text.indexOf(span)
    if (idx === -1) continue
    ranges.push({ start: idx, end: idx + span.length, hit: h })
  }
  ranges.sort((a, b) => a.start - b.start)

  let i = 0
  for (const r of ranges) {
    if (r.start > i) segments.push({ type: 'plain', text: text.slice(i, r.start) })
    segments.push({ type: 'amb', text: text.slice(r.start, r.end), hit: r.hit })
    i = Math.max(i, r.end)
  }
  if (i < text.length) segments.push({ type: 'plain', text: text.slice(i) })

  return (
    <div className="ambiguity-view">
      <h4>Ambiguity map</h4>
      <p className="muted small">Hover a highlight for a clarifying question.</p>
      <div className="ambiguity-text">
        {segments.map((s, idx) =>
          s.type === 'plain' ? (
            <span key={idx}>{s.text}</span>
          ) : (
            <span
              key={idx}
              className={`amb-mark amb-${level(s.hit.score)}`}
              title={s.hit.suggestion}
            >
              {s.text}
            </span>
          ),
        )}
      </div>
    </div>
  )
}
