import { lazy, Suspense, useEffect, useState } from 'react'

const MermaidViewCore = lazy(() => import('./MermaidViewCore'))

/**
 * Lazy-loads Mermaid (~500KB) only when a diagram is shown.
 */
export default function MermaidView({ source, className = '' }) {
  const [show, setShow] = useState(false)

  useEffect(() => {
    if (!source?.trim()) {
      setShow(false)
      return undefined
    }
    const t = requestAnimationFrame(() => setShow(true))
    return () => cancelAnimationFrame(t)
  }, [source])

  if (!source?.trim()) return null
  if (!show) {
    return <p className={`muted small mermaid-lazy-placeholder ${className}`}>Loading diagram…</p>
  }

  return (
    <Suspense
      fallback={<p className={`muted small mermaid-lazy-placeholder ${className}`}>Loading diagram…</p>}
    >
      <MermaidViewCore source={source} className={className} />
    </Suspense>
  )
}
