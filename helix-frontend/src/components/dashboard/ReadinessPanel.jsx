import { useMemo } from 'react'

function Item({ ok, label, hint, jump, onJump }) {
  const content = (
    <>
      <span className="readiness-ico" aria-hidden>
        {ok ? '✓' : '○'}
      </span>
      <span className="readiness-item-text">
        <strong>{label}</strong>
        {hint ? <span className="muted small"> — {hint}</span> : null}
      </span>
    </>
  )

  if (onJump && jump) {
    return (
      <li>
        <button
          type="button"
          className={`readiness-item readiness-item-btn ${ok ? 'readiness-item--ok' : 'readiness-item--warn'}`}
          onClick={() => onJump(jump)}
          title="Jump to related panel"
        >
          {content}
        </button>
      </li>
    )
  }

  return (
    <li className={`readiness-item ${ok ? 'readiness-item--ok' : 'readiness-item--warn'}`}>{content}</li>
  )
}

export default function ReadinessPanel({
  summary,
  stories = [],
  tasks = [],
  testcases = [],
  ambiguities = [],
  citationItemRate,
  onJump,
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
        jump: 'summary',
      },
      {
        ok: stories.length > 0,
        label: 'User stories drafted',
        hint: stories.length === 0 ? 'Need at least one story' : `${stories.length} story(ies)`,
        jump: 'stories',
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
        jump: 'stories',
      },
      {
        ok: tasks.length > 0,
        label: 'Tasks on the board',
        hint: tasks.length === 0 ? 'Break work into tasks' : `${tasks.length} task(s)`,
        jump: 'tasks',
      },
      {
        ok: testcases.length > 0,
        label: 'Test coverage started',
        hint: testcases.length === 0 ? 'Generate tests' : `${testcases.length} case(s)`,
        jump: 'tests',
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
        jump: 'trace',
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
        jump: 'ambiguity',
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
        PM-style checklist: click any row to jump to the panel that fixes it.
      </p>
      <ul className="readiness-list">
        {rows.map((r) => (
          <Item key={r.label} {...r} onJump={onJump} />
        ))}
      </ul>
    </section>
  )
}
