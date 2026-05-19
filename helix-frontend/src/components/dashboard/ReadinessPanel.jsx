import { useMemo } from 'react'

function Item({ ok, label, hint }) {
  return (
    <li className={`readiness-item ${ok ? 'readiness-item--ok' : 'readiness-item--warn'}`}>
      <span className="readiness-ico" aria-hidden>
        {ok ? '✓' : '○'}
      </span>
      <span>
        <strong>{label}</strong>
        {hint ? <span className="muted small"> — {hint}</span> : null}
      </span>
    </li>
  )
}

export default function ReadinessPanel({
  summary,
  stories = [],
  tasks = [],
  testcases = [],
  ambiguities = [],
  citationItemRate,
}) {
  const { rows, score } = useMemo(() => {
    const storyGoals = stories.map((s) => (s.goal || '').trim().length)
    const avgGoal =
      storyGoals.length > 0 ? storyGoals.reduce((a, b) => a + b, 0) / storyGoals.length : 0
    const cite = citationItemRate == null ? null : Number(citationItemRate)
    const list = [
      {
        ok: !!summary?.one_liner,
        label: 'Executive summary',
        hint: !summary?.one_liner ? 'Generate artifacts' : null,
      },
      {
        ok: stories.length > 0,
        label: 'User stories drafted',
        hint: stories.length === 0 ? 'Need at least one story' : `${stories.length} story(ies)`,
      },
      {
        ok: stories.length === 0 || avgGoal >= 24,
        label: 'Stories have substantive goals',
        hint:
          stories.length && avgGoal < 24
            ? 'Expand goals with acceptance hints'
            : stories.length
              ? `Avg goal length ${Math.round(avgGoal)} chars`
              : null,
      },
      {
        ok: tasks.length > 0,
        label: 'Tasks on the board',
        hint: tasks.length === 0 ? 'Break work into tasks' : `${tasks.length} task(s)`,
      },
      {
        ok: testcases.length > 0,
        label: 'Test coverage started',
        hint: testcases.length === 0 ? 'Generate tests' : `${testcases.length} case(s)`,
      },
      {
        ok: cite == null || cite >= 0.35,
        label: 'Traceability / citations',
        hint:
          cite == null
            ? 'Run artifact generation to compute'
            : cite < 0.35
              ? `${Math.round(cite * 100)}% — tie work to requirement clauses`
              : `${Math.round(cite * 100)}% cited`,
      },
      {
        ok: ambiguities.length <= 2,
        label: 'Ambiguity load',
        hint:
          ambiguities.length > 2
            ? `${ambiguities.length} open questions — tighten wording`
            : ambiguities.length
              ? `${ambiguities.length} flagged (review in panel below)`
              : 'None flagged (or not scanned yet)',
      },
    ]
    const n = list.filter((r) => r.ok).length
    return { rows: list, score: Math.round((n / list.length) * 100) }
  }, [summary, stories, tasks, testcases, ambiguities.length, citationItemRate])

  return (
    <section className="panel readiness-panel" aria-labelledby="readiness-title">
      <div className="readiness-head">
        <h4 id="readiness-title">Readiness check</h4>
        <span className="readiness-score" title="Heuristic score before handoff">
          {score}%
        </span>
      </div>
      <p className="muted small readiness-lede">
        PM-style checklist (inspired by reviewer flows): surface gaps before export or stakeholder
        review.
      </p>
      <ul className="readiness-list">{rows.map((r) => <Item key={r.label} {...r} />)}</ul>
    </section>
  )
}
