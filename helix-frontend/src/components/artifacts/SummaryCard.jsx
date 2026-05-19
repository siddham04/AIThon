import { useEffect, useMemo, useRef, useState } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import {
  defaultStoryMeta,
  loadStoryPlanningMap,
  riceScore,
  saveStoryPlanningMap,
  sortStoriesForPlanning,
} from '../../lib/storyPlanningMeta'

const EXPORT_GATE_HELP =
  'Only items marked approved for export are sent when you enable “Approved only” on exports — unreviewed work stays in Helix.'

export default function SummaryCard({
  summary,
  stories = [],
  projectId,
  onStoryExportToggle,
  onGenerateArtifacts,
}) {
  const [open, setOpen] = useState(false)
  const [storyMeta, setStoryMeta] = useState({})
  const [sortMode, setSortMode] = useState('backlog')
  const saveTimerRef = useRef(null)
  const rootRef = useRef(null)
  const listRef = useRef(null)

  useEffect(() => {
    if (!projectId) {
      queueMicrotask(() => setStoryMeta({}))
      return
    }
    queueMicrotask(() => {
      setStoryMeta(loadStoryPlanningMap(projectId))
    })
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    window.clearTimeout(saveTimerRef.current)
    saveTimerRef.current = window.setTimeout(() => {
      saveStoryPlanningMap(projectId, storyMeta)
    }, 400)
    return () => window.clearTimeout(saveTimerRef.current)
  }, [projectId, storyMeta])

  const sortedStories = useMemo(
    () => sortStoriesForPlanning(stories, storyMeta, sortMode),
    [stories, storyMeta, sortMode],
  )

  const patchStoryMeta = (storyKey, patch) => {
    setStoryMeta((prev) => ({
      ...prev,
      [storyKey]: { ...defaultStoryMeta(), ...prev[storyKey], ...patch },
    }))
  }

  useGSAP(
    () => {
      const root = rootRef.current
      if (!root) return
      const ctx = gsap.context(() => {
        const tl = gsap.timeline({ defaults: { ease: 'power2.out' } })
        tl.from(root, { opacity: 0, y: 10, duration: 0.35 })
          .from('.summary-head h2', { opacity: 0, duration: 0.25 }, '-=0.2')
          .from(
            '.summary-block',
            { opacity: 0, y: 8, duration: 0.28, stagger: 0.06 },
            '-=0.15',
          )
      }, root)
      return () => ctx.revert()
    },
    { scope: rootRef, dependencies: [summary?.title] },
  )

  useGSAP(
    () => {
      const el = listRef.current
      if (!el || stories.length === 0) return
      if (open) {
        el.style.overflow = 'hidden'
        gsap.killTweensOf(el)
        const full = el.scrollHeight
        gsap.fromTo(
          el,
          { height: 0, opacity: 0 },
          {
            height: full,
            opacity: 1,
            duration: 0.35,
            ease: 'power2.out',
            onComplete: () => {
              el.style.height = 'auto'
              el.style.overflow = ''
            },
          },
        )
        const items = el.querySelectorAll('li')
        gsap.from(items, {
          opacity: 0,
          x: -6,
          duration: 0.2,
          stagger: 0.035,
          delay: 0.06,
          ease: 'power2.out',
        })
      } else {
        gsap.killTweensOf(el)
        const h = el.scrollHeight
        if (h <= 0) {
          gsap.set(el, { height: 0, opacity: 0 })
          return
        }
        el.style.overflow = 'hidden'
        el.style.height = `${h}px`
        gsap.to(el, {
          height: 0,
          opacity: 0,
          duration: 0.25,
          ease: 'power2.in',
          onComplete: () => {
            el.style.height = '0'
          },
        })
      }
    },
    { dependencies: [open] },
  )

  if (!summary) {
    return (
      <div id="helix-panel-summary" className="summary-card empty">
        <p className="muted">No AI summary yet. Generate artifacts to populate this card.</p>
        {onGenerateArtifacts ? (
          <button type="button" className="btn btn-primary" onClick={() => onGenerateArtifacts()}>
            Generate artifacts
          </button>
        ) : null}
      </div>
    )
  }

  const conf = summary.coverage_score ?? summary.confidence ?? 0.72
  const badge = Math.round(Number(conf) * 100)

  const blocks = [
    { title: 'Objective', body: summary.objective },
    { title: 'In scope', body: (summary.in_scope || []).join(' · ') },
    { title: 'Out of scope', body: (summary.out_of_scope || []).join(' · ') },
    { title: 'Success metrics', body: (summary.success_metrics || []).join(' · ') },
  ].filter((b) => b.body)

  const approvedStoryExport = stories.filter((x) => x.approved_for_export).length

  return (
    <div ref={rootRef} id="helix-panel-summary" className="summary-card">
      <div className="summary-head">
        <div>
          <h2>{summary.title || 'Project summary'}</h2>
          <p className="summary-one">{summary.one_liner}</p>
        </div>
        <span className="confidence-badge" title="Model confidence / coverage">
          {badge}% confidence
        </span>
      </div>

      <div className="summary-grid">
        {blocks.map((b) => (
          <section key={b.title} className="summary-block">
            <h4>{b.title}</h4>
            <p>{b.body}</p>
          </section>
        ))}
      </div>

      {stories.length > 0 && (
        <div className="summary-stories">
          <div className="summary-stories-head">
            <button type="button" className="linkish" onClick={() => setOpen((o) => !o)}>
              {open ? 'Hide' : 'Show'} user stories ({stories.length} · {approvedStoryExport}{' '}
              approved for export)
            </button>
            <button
              type="button"
              className="export-gate-tip-btn"
              title={EXPORT_GATE_HELP}
              aria-label={EXPORT_GATE_HELP}
            >
              ⓘ
            </button>
          </div>
          {open && projectId ? (
            <div className="story-sort-row">
              <span className="muted small">Order</span>
              <select
                value={sortMode}
                onChange={(e) => setSortMode(e.target.value)}
                aria-label="Story sort order"
              >
                <option value="backlog">Backlog (API)</option>
                <option value="priority">Priority (P1 first)</option>
                <option value="rice">RICE score (high first)</option>
              </select>
            </div>
          ) : null}
          <ul ref={listRef} className="story-list" aria-hidden={!open}>
            {sortedStories.map((s, idx) => {
              const storyKey = s.id || `idx-${idx}`
              const meta = { ...defaultStoryMeta(), ...storyMeta[storyKey] }
              const score = riceScore(meta)
              return (
              <li key={s.id || idx}>
                <div className="story-row-head">
                  <strong>{s.title || `Story ${idx + 1}`}</strong>
                  {projectId && onStoryExportToggle && s.id ? (
                    <label
                      className="export-approve-toggle"
                      title={EXPORT_GATE_HELP}
                      onClick={(e) => e.stopPropagation()}
                      onPointerDown={(e) => e.stopPropagation()}
                    >
                      <span className="muted small">Export OK</span>
                      <input
                        type="checkbox"
                        checked={!!s.approved_for_export}
                        onChange={(e) => void onStoryExportToggle(s.id, e.target.checked)}
                        aria-label={`Approve story “${s.title || s.id}” for export`}
                      />
                    </label>
                  ) : null}
                </div>
                <p className="muted small">{s.goal}</p>
                {projectId ? (
                  <div className="story-planning-row">
                    <label>
                      Pri
                      <select
                        value={meta.priority}
                        onChange={(e) => patchStoryMeta(storyKey, { priority: e.target.value })}
                      >
                        {['P1', 'P2', 'P3', 'P4'].map((p) => (
                          <option key={p} value={p}>
                            {p}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      R
                      <input
                        type="number"
                        min={1}
                        max={5}
                        value={meta.reach}
                        onChange={(e) =>
                          patchStoryMeta(storyKey, { reach: Number(e.target.value) || 1 })
                        }
                      />
                    </label>
                    <label>
                      I
                      <input
                        type="number"
                        min={1}
                        max={5}
                        value={meta.impact}
                        onChange={(e) =>
                          patchStoryMeta(storyKey, { impact: Number(e.target.value) || 1 })
                        }
                      />
                    </label>
                    <label>
                      C%
                      <select
                        value={meta.confidence}
                        onChange={(e) =>
                          patchStoryMeta(storyKey, { confidence: Number(e.target.value) })
                        }
                      >
                        <option value={50}>50</option>
                        <option value={80}>80</option>
                        <option value={100}>100</option>
                      </select>
                    </label>
                    <label>
                      E
                      <input
                        type="number"
                        min={1}
                        max={5}
                        value={meta.effort}
                        onChange={(e) =>
                          patchStoryMeta(storyKey, { effort: Number(e.target.value) || 1 })
                        }
                      />
                    </label>
                    <span title="(R×I×C%)/E" className="muted small">
                      RICE {score.toFixed(2)}
                    </span>
                  </div>
                ) : null}
              </li>
            )})}
          </ul>
        </div>
      )}
    </div>
  )
}
