import { useCallback, useEffect, useState } from 'react'
import { api } from '../../api/client'

export default function JiraCsvPreview({ projectId, enabled = true }) {
  const [loading, setLoading] = useState(() => Boolean(projectId && enabled))
  const [headers, setHeaders] = useState([])
  const [rows, setRows] = useState([])
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    if (!projectId || !enabled) return
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get(`/backlog/${projectId}/jira-csv/preview`, {
        params: { limit: 20 },
      })
      setHeaders(data.headers || [])
      setRows(data.rows || [])
    } catch (e) {
      setError(e?.response?.data?.detail || 'Preview unavailable — run pipeline first')
      setHeaders([])
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [projectId, enabled])

  useEffect(() => {
    if (!projectId || !enabled) return undefined
    let cancelled = false
    ;(async () => {
      setError(null)
      try {
        const { data } = await api.get(`/backlog/${projectId}/jira-csv/preview`, {
          params: { limit: 20 },
        })
        if (cancelled) return
        setHeaders(data.headers || [])
        setRows(data.rows || [])
      } catch (e) {
        if (cancelled) return
        setError(e?.response?.data?.detail || 'Preview unavailable — run pipeline first')
        setHeaders([])
        setRows([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [projectId, enabled])

  if (!enabled || !projectId) return null
  if (loading) return <p className="muted small jira-csv-preview">Loading Jira CSV preview…</p>
  if (error) return <p className="muted small jira-csv-preview">{error}</p>
  if (!rows.length) return null

  return (
    <div className="jira-csv-preview panel">
      <div className="jira-csv-preview-head">
        <h3>Jira CSV preview</h3>
        <button type="button" className="btn ghost small" onClick={() => void load()}>
          Refresh
        </button>
      </div>
      <div className="jira-csv-preview-scroll">
        <table className="jira-csv-table">
          <thead>
            <tr>
              {(headers.length ? headers : Object.keys(rows[0])).slice(0, 6).map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={row['Helix ID'] || row['Issue ID'] || i}>
                {(headers.length ? headers : Object.keys(row)).slice(0, 6).map((h) => (
                  <td key={h}>{String(row[h] ?? '').slice(0, 80)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted small">Showing first {rows.length} rows · full file on Approve &amp; Export</p>
    </div>
  )
}
