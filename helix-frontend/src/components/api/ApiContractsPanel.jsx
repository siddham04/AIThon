import { useMemo, useState } from 'react'
import { api } from '../../api/client'

/**
 * API Contracts panel rendered on the AI Workspace.
 *
 * Each contract row is collapsed by default (one-line method + path)
 * and expands to show request/response fields, example payloads, and
 * status codes — judges go from "13 endpoints" to "here is the
 * actual JSON contract" in one click without leaving the page.
 *
 * The panel also shows per-method count badges (GET 4 · POST 6 ·
 * PUT 2 · DELETE 1) and a Download OpenAPI button that streams the
 * generated spec straight to disk.
 */
export default function ApiContractsPanel({ projectId, contracts }) {
  const list = contracts?.contracts || []
  const [expanded, setExpanded] = useState(() => new Set())
  const [downloading, setDownloading] = useState(false)

  const counts = useMemo(() => {
    const out = {}
    for (const c of list) {
      const m = (c.method || 'GET').toUpperCase()
      out[m] = (out[m] || 0) + 1
    }
    return out
  }, [list])

  const toggle = (key) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const expandAll = () => {
    setExpanded(new Set(list.map((c, i) => keyFor(c, i))))
  }

  const collapseAll = () => setExpanded(new Set())

  const downloadOpenApi = async () => {
    if (!projectId) return
    setDownloading(true)
    try {
      const res = await api.get(`/devstudio/contract/${projectId}/openapi`, {
        responseType: 'blob',
      })
      const blob = res.data instanceof Blob ? res.data : new Blob([res.data], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `helix-openapi-${projectId.slice(0, 8)}.json`
      document.body.appendChild(link)
      link.click()
      link.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (_) {
      // The endpoint returns 404 when contracts haven't been generated
      // — surface a quiet hint instead of a thrown error.
      // eslint-disable-next-line no-alert
      window.alert('OpenAPI spec not available yet. Run the API contracts step first.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <section className="p5-panel" id="api-contracts">
      <div className="p5-section-head">
        <h2>API Contracts ({list.length})</h2>
        {list.length > 0 && (
          <div className="hx-api-actions">
            <MethodBadges counts={counts} />
            <button type="button" className="btn ghost small" onClick={expandAll}>
              Expand all
            </button>
            <button type="button" className="btn ghost small" onClick={collapseAll}>
              Collapse all
            </button>
            <button
              type="button"
              className="btn ghost small"
              onClick={() => void downloadOpenApi()}
              disabled={downloading}
            >
              {downloading ? 'Downloading…' : 'Download OpenAPI'}
            </button>
          </div>
        )}
      </div>

      {list.length === 0 ? (
        <p className="muted">
          API contracts appear after the pipeline runs (REST endpoints derived
          from each user story).
        </p>
      ) : (
        <ul className="p5-list p5-list--apis hx-api-list">
          {list.map((c, i) => {
            const key = keyFor(c, i)
            const isOpen = expanded.has(key)
            const method = (c.method || 'GET').toUpperCase()
            return (
              <li key={key} className={`hx-api-row${isOpen ? ' hx-api-row--open' : ''}`}>
                <button
                  type="button"
                  className="hx-api-row__head"
                  onClick={() => toggle(key)}
                  aria-expanded={isOpen}
                >
                  <code className={`p5-api-method p5-api-method--${method.toLowerCase()}`}>
                    {method}
                  </code>
                  <code className="p5-api-endpoint">{c.endpoint}</code>
                  {c.summary && (
                    <span className="muted small hx-api-row__summary">{c.summary}</span>
                  )}
                  <span className="hx-api-row__chevron" aria-hidden>
                    {isOpen ? '▾' : '▸'}
                  </span>
                </button>

                {isOpen && <ContractDetails contract={c} />}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

function keyFor(c, i) {
  return `${(c.method || 'GET').toUpperCase()}-${c.endpoint}-${i}`
}

function MethodBadges({ counts }) {
  const order = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
  const entries = order.filter((m) => counts[m])
  if (entries.length === 0) return null
  return (
    <div className="hx-api-method-badges" aria-label="Endpoints by HTTP method">
      {entries.map((m) => (
        <span
          key={m}
          className={`hx-api-method-badge hx-api-method-badge--${m.toLowerCase()}`}
        >
          <strong>{m}</strong> {counts[m]}
        </span>
      ))}
    </div>
  )
}

function ContractDetails({ contract }) {
  const reqFields = contract.request_fields || []
  const respFields = contract.response_fields || []
  const statusCodes = contract.status_codes || []
  return (
    <div className="hx-api-row__body">
      {contract.description && (
        <p className="hx-api-row__description">{contract.description}</p>
      )}

      <div className="hx-api-row__cols">
        <FieldTable label="Request fields" fields={reqFields} />
        <FieldTable label="Response fields" fields={respFields} />
      </div>

      {(contract.request_example || contract.response_example) && (
        <div className="hx-api-row__examples">
          {contract.request_example && (
            <ExampleBlock label="Request example" value={contract.request_example} />
          )}
          {contract.response_example && (
            <ExampleBlock label="Response example" value={contract.response_example} />
          )}
        </div>
      )}

      {statusCodes.length > 0 && (
        <div className="hx-api-row__status">
          {statusCodes.map((s, i) => (
            <span key={i} className="hx-api-status">
              <strong>{s.code}</strong> {s.description}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function FieldTable({ label, fields }) {
  if (!fields?.length) return null
  return (
    <div className="hx-api-fields">
      <strong>{label}</strong>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {fields.map((f, i) => (
            <tr key={i}>
              <td>
                <code>{f.name}</code>
              </td>
              <td className="muted small">{f.type}</td>
              <td>{f.description || ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ExampleBlock({ label, value }) {
  const json = useMemo(() => {
    try {
      return typeof value === 'string' ? value : JSON.stringify(value, null, 2)
    } catch (_) {
      return String(value)
    }
  }, [value])
  return (
    <details className="hx-api-example">
      <summary>{label}</summary>
      <pre className="p5-code-block">{json}</pre>
    </details>
  )
}
