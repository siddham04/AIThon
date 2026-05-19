import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import toast from 'react-hot-toast'
import { api } from '../api/client'
import { buildHelixBundleMarkdown } from '../lib/buildHelixMarkdown'

function requirementBlobFromArtifacts(data) {
  return [
    data.summary?.objective,
    data.summary?.one_liner,
    ...(data.stories || []).map((s) => `${s.title}. ${s.goal}`),
  ]
    .filter(Boolean)
    .join('\n\n')
}

export default function StakeholderPreview() {
  const { id } = useParams()
  const [projectName, setProjectName] = useState('')
  const [markdown, setMarkdown] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setLoadError(null)
    try {
      const [{ data: proj }, { data: art }] = await Promise.all([
        api.get(`/projects/${id}`),
        api.get(`/artifacts/${id}`),
      ])
      setProjectName(proj?.name || 'Helix project')
      const workingRequirement = requirementBlobFromArtifacts(art || {})
      const md = buildHelixBundleMarkdown({
        projectName: proj?.name,
        summary: art?.summary,
        stories: art?.stories,
        tasks: art?.tasks,
        workingRequirement,
        citationItemRate: art?.citation_item_rate,
      })
      setMarkdown(md)
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Could not load preview'
      setLoadError(String(msg))
      toast.error('Could not load preview')
      setMarkdown('')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    queueMicrotask(() => {
      void load()
    })
  }, [load])

  const shareUrl = useMemo(() => {
    if (typeof window === 'undefined' || !id) return ''
    return `${window.location.origin}/project/${id}/preview`
  }, [id])

  const copyMd = async () => {
    try {
      await navigator.clipboard.writeText(markdown)
      toast.success('Markdown copied')
    } catch {
      toast.error('Clipboard not available')
    }
  }

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      toast.success('Read-only link copied')
    } catch {
      toast.error('Clipboard not available')
    }
  }

  return (
    <div className="page stakeholder-preview">
      <header className="stakeholder-preview-header">
        <div>
          <p className="muted small">Read-only handoff</p>
          <h1>{projectName || 'Project'}</h1>
        </div>
        <div className="stakeholder-preview-actions">
          <button type="button" className="btn ghost" disabled={loading} onClick={() => void load()}>
            {loading ? 'Loading…' : 'Reload'}
          </button>
          <button type="button" className="btn ghost" disabled={loading || !markdown} onClick={() => void copyMd()}>
            Copy Markdown
          </button>
          <button type="button" className="btn ghost" disabled={!shareUrl} onClick={() => void copyLink()}>
            Copy link
          </button>
          <Link to={`/project/${id}`} className="btn btn-primary">
            Open workspace
          </Link>
        </div>
      </header>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : loadError ? (
        <div className="panel stakeholder-preview-error" role="alert">
          <p className="muted">{loadError}</p>
          <button type="button" className="btn btn-primary" onClick={() => void load()}>
            Retry
          </button>
        </div>
      ) : (
        <article className="stakeholder-preview-body markdown-body">
          <ReactMarkdown>{markdown || '_No artifact content yet._'}</ReactMarkdown>
        </article>
      )}
    </div>
  )
}
