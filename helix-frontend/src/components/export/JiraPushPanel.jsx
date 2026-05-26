import { useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../../api/client'

export default function JiraPushPanel({ projectId, disabled }) {
  const [pushing, setPushing] = useState(false)
  const [lastResult, setLastResult] = useState(null)

  const pushToJira = async () => {
    if (!projectId || disabled) return
    setPushing(true)
    try {
      const { data } = await api.post(`/backlog/${projectId}/jira-push`)
      setLastResult(data)
      if (data?.ok || data?.created_count > 0) {
        toast.success(data?.message || 'Jira push completed')
      } else if (data?.dry_run || data?.reason === 'missing_config' || data?.reason === 'missing_email') {
        // Backend returns ok:false reason:missing_config when JIRA_* env is
        // unset — that's a normal dry-run path for the hackathon demo, not
        // an error. Show a friendly success toast and the preview payload.
        toast.success('Dry run — configure JIRA_* env on the API host for a live push')
      } else {
        toast.error(data?.message || data?.detail || 'Jira push returned no issues')
      }
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || 'Jira push failed'
      toast.error(msg)
      setLastResult({ ok: false, message: msg })
    } finally {
      setPushing(false)
    }
  }

  if (!projectId) return null

  return (
    <div className="jira-push-panel panel">
      <div className="jira-push-head">
        <h3>Live Jira push</h3>
        <button
          type="button"
          className="btn btn-primary small"
          disabled={disabled || pushing}
          onClick={() => void pushToJira()}
        >
          {pushing ? 'Pushing…' : 'Push to Jira REST'}
        </button>
      </div>
      <p className="muted small">
        Requires <code>JIRA_BASE_URL</code>, <code>JIRA_EMAIL</code>, <code>JIRA_TOKEN</code>,{' '}
        <code>JIRA_PROJECT_KEY</code> on the API host. Without config, returns a dry-run summary.
      </p>
      {lastResult && (
        <pre className="jira-push-result muted small">
          {JSON.stringify(lastResult, null, 2)}
        </pre>
      )}
    </div>
  )
}
