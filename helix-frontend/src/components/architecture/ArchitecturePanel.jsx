import { useEffect, useMemo, useRef, useState } from 'react'
import mermaid from 'mermaid'

mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  securityLevel: 'strict',
  flowchart: { htmlLabels: true, curve: 'basis' },
})

/**
 * Architecture panel rendered on the AI Workspace.
 *
 * Replaces the previous "raw Mermaid in a <details>" UX with a
 * live-rendered SVG diagram judges can actually see. Also exposes:
 *   * Layer cards with component chips (already worked)
 *   * Download Mermaid (.mmd) and Download SVG buttons
 *   * Collapsible component tree for the engineering audience
 *
 * The Mermaid source comes from the backend (mermaid + mermaid_layers
 * fields). We prefer the flow diagram (`mermaid`) because it shows
 * data movement; the layered diagram (`mermaid_layers`) is the fallback.
 */
export default function ArchitecturePanel({ projectId, diagram }) {
  const layers = diagram?.layers || []
  const [activeDiagram, setActiveDiagram] = useState('flow') // flow | layers
  const containerRef = useRef(null)
  const renderIdRef = useRef(0)
  const [svg, setSvg] = useState('')
  const [renderError, setRenderError] = useState(null)

  const source = useMemo(() => {
    if (!diagram) return ''
    if (activeDiagram === 'layers' && diagram.mermaid_layers) {
      return diagram.mermaid_layers
    }
    return diagram.mermaid || diagram.mermaid_layers || ''
  }, [diagram, activeDiagram])

  useEffect(() => {
    if (!source) {
      setSvg('')
      setRenderError(null)
      return
    }
    let cancelled = false
    renderIdRef.current += 1
    const id = `hx-arch-mmd-${renderIdRef.current}`
    mermaid
      .render(id, source)
      .then(({ svg: out }) => {
        if (cancelled) return
        setSvg(out)
        setRenderError(null)
      })
      .catch((err) => {
        if (cancelled) return
        setRenderError(err?.message || 'Could not render diagram')
        setSvg('')
      })
    return () => {
      cancelled = true
    }
  }, [source])

  const downloadFile = (filename, contents, mime) => {
    const blob = new Blob([contents], { type: mime })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const downloadMermaid = () => {
    if (!source) return
    downloadFile(
      `helix-architecture-${(projectId || 'project').slice(0, 8)}.mmd`,
      source,
      'text/plain;charset=utf-8',
    )
  }

  const downloadSvg = () => {
    if (!svg) return
    downloadFile(
      `helix-architecture-${(projectId || 'project').slice(0, 8)}.svg`,
      svg,
      'image/svg+xml;charset=utf-8',
    )
  }

  return (
    <section className="p5-panel" id="architecture">
      <div className="p5-section-head">
        <h2>Architecture</h2>
        {diagram?.nodes_count != null && (
          <div className="hx-arch-meta">
            <span className="muted small">
              {layers.length} layers · {diagram.nodes_count} nodes · {diagram.edges_count} edges
            </span>
            {(diagram.mermaid || diagram.mermaid_layers) && (
              <div className="hx-arch-actions">
                {diagram.mermaid && diagram.mermaid_layers && (
                  <div className="hx-arch-toggle" role="tablist">
                    <button
                      type="button"
                      className={`btn ghost small${activeDiagram === 'flow' ? ' is-active' : ''}`}
                      onClick={() => setActiveDiagram('flow')}
                      aria-pressed={activeDiagram === 'flow'}
                    >
                      Flow
                    </button>
                    <button
                      type="button"
                      className={`btn ghost small${activeDiagram === 'layers' ? ' is-active' : ''}`}
                      onClick={() => setActiveDiagram('layers')}
                      aria-pressed={activeDiagram === 'layers'}
                    >
                      Layered
                    </button>
                  </div>
                )}
                <button type="button" className="btn ghost small" onClick={downloadMermaid}>
                  Download .mmd
                </button>
                <button
                  type="button"
                  className="btn ghost small"
                  onClick={downloadSvg}
                  disabled={!svg}
                >
                  Download SVG
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {!diagram ? (
        <p className="muted">
          Architecture appears after the pipeline runs (frontend · backend ·
          database layers plus a Mermaid diagram).
        </p>
      ) : (
        <>
          {/* Live-rendered Mermaid diagram. Judges see an actual
              labelled flow chart instead of raw text. */}
          {source && (
            <div className="hx-arch-diagram-wrap" aria-label="Architecture diagram">
              {renderError ? (
                <p className="muted small">
                  Diagram render failed: {renderError}. The raw Mermaid is
                  available via "Download .mmd".
                </p>
              ) : svg ? (
                <div
                  ref={containerRef}
                  className="hx-arch-diagram"
                  // eslint-disable-next-line react/no-danger
                  dangerouslySetInnerHTML={{ __html: svg }}
                />
              ) : (
                <p className="muted small">Rendering diagram…</p>
              )}
            </div>
          )}

          {/* Layer cards with component chips */}
          {layers.length > 0 && (
            <div className="p5-arch-layers">
              {layers.map((layer) => (
                <div key={layer.name} className="p5-arch-layer">
                  <strong>{layer.name}</strong>
                  <ul className="p5-list p5-list--inline">
                    {(layer.items || []).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}

          {/* Engineering-grade extras */}
          {(diagram.mermaid || diagram.tree_text) && (
            <div className="hx-arch-extras">
              {diagram.mermaid && (
                <details className="p5-mermaid-details">
                  <summary>Mermaid source ({source.split('\n').length} lines)</summary>
                  <pre className="p5-code-block">{source}</pre>
                </details>
              )}
              {diagram.tree_text && (
                <details className="p5-mermaid-details">
                  <summary>Component tree</summary>
                  <pre className="p5-code-block">{diagram.tree_text}</pre>
                </details>
              )}
            </div>
          )}
        </>
      )}
    </section>
  )
}
