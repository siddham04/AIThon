import { useEffect, useRef, useState } from 'react'
import mermaid from 'mermaid'
import { mountSanitizedSvg } from '../../lib/svgSanitize'

function ensureInit(theme) {
  mermaid.initialize({
    startOnLoad: false,
    theme: theme === 'dark' ? 'dark' : 'default',
    securityLevel: 'strict',
    flowchart: { htmlLabels: false, curve: 'basis', padding: 14 },
    fontFamily: 'Inter, system-ui, -apple-system, "Segoe UI", sans-serif',
  })
}

function detectTheme() {
  if (typeof document === 'undefined') return 'light'
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

let renderId = 0

export default function MermaidViewCore({ source, className = '' }) {
  const ref = useRef(null)
  const [error, setError] = useState(null)
  const [theme, setTheme] = useState(detectTheme())

  useEffect(() => {
    const obs = new MutationObserver(() => {
      const next = detectTheme()
      setTheme((prev) => (prev !== next ? next : prev))
    })
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    return () => obs.disconnect()
  }, [])

  useEffect(() => {
    if (!source || !ref.current) return
    let cancelled = false
    setError(null)
    try {
      ensureInit(theme)
    } catch {
      ensureInit(theme)
    }

    const id = `helix-mmd-${++renderId}`
    mermaid
      .render(id, source)
      .then(({ svg }) => {
        if (cancelled || !ref.current) return
        if (!mountSanitizedSvg(ref.current, svg)) {
          setError('Diagram failed security validation')
        }
      })
      .catch((e) => {
        if (cancelled) return
        console.error('Mermaid render failed', e)
        setError(e?.message || String(e))
      })
    return () => {
      cancelled = true
    }
  }, [source, theme])

  if (error) {
    return (
      <div className={`mermaid-error ${className}`}>
        <strong>Could not render diagram</strong>
        <pre className="muted small">{error}</pre>
      </div>
    )
  }

  return <div ref={ref} className={`mermaid-host ${className}`} />
}
