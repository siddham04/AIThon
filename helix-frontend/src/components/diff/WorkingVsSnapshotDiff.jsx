import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../../api/client'
import RequirementTextDiff from './RequirementTextDiff'

/**
 * Diff latest saved Mongo snapshot vs current working requirement (unsaved edits).
 * API: GET /projects/:id/requirement-versions — newest first at index 0.
 */
export default function WorkingVsSnapshotDiff({ projectId, workingText, refreshKey = 0 }) {
  const [snapshotText, setSnapshotText] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    try {
      const { data } = await api.get(`/projects/${projectId}/requirement-versions`)
      const list = Array.isArray(data) ? data : []
      setSnapshotText(list[0]?.text ?? '')
    } catch (e) {
      if (e.response?.status !== 503) {
        toast.error('Could not load snapshot for diff')
      }
      setSnapshotText('')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    queueMicrotask(() => {
      void load()
    })
  }, [load, refreshKey])

  if (loading) {
    return <p className="muted small">Loading working vs snapshot diff…</p>
  }

  if (!snapshotText && !(workingText || '').trim()) {
    return null
  }

  const same = (snapshotText || '') === (workingText || '')

  return (
    <div className="version-history working-snapshot-diff">
      <h4>Working vs latest snapshot</h4>
      <p className="muted small">
        Compare your editor to the newest saved snapshot (green = added in working copy, red = removed vs
        snapshot).
      </p>
      {same ? (
        <p className="muted small">No drift — working copy matches the latest snapshot.</p>
      ) : (
        <RequirementTextDiff oldText={snapshotText} newText={workingText} />
      )}
    </div>
  )
}
