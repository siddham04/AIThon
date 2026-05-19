import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../api/client'
import RequirementTextDiff from './diff/RequirementTextDiff'

/** API returns snapshots newest-first: index 0 newest, larger index older. */
export default function VersionHistory({ projectId, refreshKey = 0 }) {
  const [versions, setVersions] = useState([])
  const [loading, setLoading] = useState(true)
  const [olderIdx, setOlderIdx] = useState(1)
  const [newerIdx, setNewerIdx] = useState(0)

  const load = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    try {
      const { data } = await api.get(`/projects/${projectId}/requirement-versions`)
      setVersions(Array.isArray(data) ? data : [])
    } catch (e) {
      if (e.response?.status !== 503) {
        toast.error('Could not load versions')
      }
      setVersions([])
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    queueMicrotask(() => {
      void load()
    })
  }, [load, refreshKey])

  useEffect(() => {
    const n = versions.length
    if (n < 2) return
    queueMicrotask(() => {
      setOlderIdx((o) => Math.min(Math.max(1, o), n - 1))
      setNewerIdx((y) => Math.min(Math.max(0, y), n - 2))
    })
  }, [versions.length])

  const n = versions.length
  const oi = n > 1 ? Math.min(Math.max(1, olderIdx), n - 1) : 0
  const ni = n > 1 ? Math.min(Math.max(0, newerIdx), oi - 1) : 0

  const textOlder = versions[oi]?.text ?? ''
  const textNewer = versions[ni]?.text ?? ''

  if (loading) {
    return <p className="muted small">Loading version history…</p>
  }

  if (!versions.length) {
    return (
      <div className="version-history empty">
        <h4>Version history</h4>
        <p className="muted small">Edit the working requirement below; each save creates a snapshot in MongoDB.</p>
      </div>
    )
  }

  return (
    <div className="version-history">
      <h4>Version history</h4>
      <p className="muted small">Compare snapshots (green = added, red = removed).</p>
      <div className="version-history-controls">
        {n >= 2 && (
          <>
            <label className="version-select">
              Older
              <select
                value={oi}
                onChange={(e) => {
                  const v = Number(e.target.value)
                  setOlderIdx(v)
                  setNewerIdx((y) => Math.min(y, v - 1))
                }}
              >
                {versions.map((ver, idx) =>
                  idx > 0 ? (
                    <option key={ver.id} value={idx}>
                      {ver.created_at?.replace('T', ' ').slice(0, 19) ?? ver.id}
                    </option>
                  ) : null,
                )}
              </select>
            </label>
            <label className="version-select">
              Newer
              <select value={ni} onChange={(e) => setNewerIdx(Number(e.target.value))}>
                {versions.map((ver, idx) =>
                  idx < oi ? (
                    <option key={`n-${ver.id}`} value={idx}>
                      {ver.created_at?.replace('T', ' ').slice(0, 19) ?? ver.id}
                    </option>
                  ) : null,
                )}
              </select>
            </label>
          </>
        )}
        <button type="button" className="btn ghost small-btn" onClick={() => void load()}>
          Refresh
        </button>
      </div>
      {n < 2 ? (
        <p className="muted small">Save at least two versions to see a diff.</p>
      ) : (
        <RequirementTextDiff oldText={textOlder} newText={textNewer} />
      )}
    </div>
  )
}
