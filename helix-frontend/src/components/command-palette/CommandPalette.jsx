import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { PRODUCT_PAGES, navPath } from '../../lib/productFlow'

function isTypingTarget(el) {
  const tag = el?.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || el?.isContentEditable
}

export default function CommandPalette() {
  const nav = useNavigate()
  const { id } = useParams()
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [idx, setIdx] = useState(0)

  const commands = useMemo(() => {
    const all = [
      ...PRODUCT_PAGES.map((mode) => ({
        id: mode.id,
        title: mode.label,
        subtitle: mode.tagline,
        keywords: `${mode.short} helix`,
        run: () => nav(navPath(id, mode.segment, mode.global)),
        disabled: mode.requiresProject && !id,
      })),
      ...(id
        ? [
            {
              id: 'launch',
              title: 'Launch AI team',
              subtitle: 'AI runs SDLC — you approve before export',
              keywords: 'agents pipeline sdlc mission',
              run: () => nav(`/project/${id}/mission-control`),
            },
          ]
        : []),
    ].filter((c) => !c.disabled)

    const needle = q.trim().toLowerCase()
    if (!needle) return all
    return all.filter((c) => {
      const hay = `${c.title} ${c.subtitle} ${c.keywords}`.toLowerCase()
      return hay.includes(needle)
    })
  }, [id, nav, q])

  useEffect(() => {
    queueMicrotask(() => {
      setIdx(0)
    })
  }, [q, open])

  const close = useCallback(() => {
    setOpen(false)
    setQ('')
  }, [])

  useEffect(() => {
    const onKey = (e) => {
      const mod = e.metaKey || e.ctrlKey
      if (mod && e.shiftKey && (e.key === 'p' || e.key === 'P')) {
        if (isTypingTarget(document.activeElement)) return
        e.preventDefault()
        setOpen((o) => !o)
        return
      }
      if (!open) return
      if (e.key === 'Escape') {
        e.preventDefault()
        close()
        return
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setIdx((i) => (commands.length ? Math.min(commands.length - 1, i + 1) : 0))
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setIdx((i) => (commands.length ? Math.max(0, i - 1) : 0))
        return
      }
      if (e.key === 'Enter' && commands[idx]) {
        e.preventDefault()
        commands[idx].run()
        close()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, close, commands, idx])

  if (!open) return null

  return (
    <dialog open className="modal command-palette-backdrop" onClick={close}>
      <div
        className="command-palette glass-panel"
        role="listbox"
        aria-label="Team commands"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          className="command-palette-input"
          autoFocus
          placeholder="Go to a team surface…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-autocomplete="list"
        />
        <ul className="command-palette-list">
          {commands.length === 0 ? (
            <li className="command-palette-empty muted small">No matches</li>
          ) : (
            commands.map((c, i) => (
              <li key={c.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={i === idx}
                  className={`command-palette-row ${i === idx ? 'active' : ''}`}
                  onMouseEnter={() => setIdx(i)}
                  onClick={() => {
                    c.run()
                    close()
                  }}
                >
                  <span className="command-palette-title">{c.title}</span>
                  <span className="command-palette-sub muted small">{c.subtitle}</span>
                </button>
              </li>
            ))
          )}
        </ul>
        <p className="muted small command-palette-hint">
          <kbd>↑</kbd> <kbd>↓</kbd> navigate · <kbd>Enter</kbd> run · <kbd>Esc</kbd> close ·{' '}
          <kbd>⌘</kbd>/<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd>
        </p>
      </div>
    </dialog>
  )
}
