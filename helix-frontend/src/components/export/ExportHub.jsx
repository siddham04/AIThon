import { useEffect, useRef, useState } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import toast from 'react-hot-toast'
import { api } from '../../api/client'
import { buildExportAuditFooter } from '../../lib/exportAuditLine'
import { sliceApprovedForExport } from '../../lib/sliceApprovedExport'

const EXPORT_SECTION_HELP =
  'Exports can carry confidential scope. Use “Approved only” after reviewers mark stories and tasks so nothing leaves Helix until it is explicitly cleared.'

function ExportRow({ label, onClick, status }) {
  const btnRef = useRef(null)

  const press = (down) => {
    const el = btnRef.current
    if (!el) return
    gsap.to(el, {
      scale: down ? 0.97 : 1,
      duration: down ? 0.1 : 0.2,
      ease: down ? 'power2.out' : 'back.out(2)',
    })
  }

  return (
    <button
      ref={btnRef}
      type="button"
      className="export-btn"
      onPointerDown={() => press(true)}
      onPointerUp={() => press(false)}
      onPointerCancel={() => press(false)}
      onPointerLeave={() => press(false)}
      onClick={onClick}
    >
      <span>{label}</span>
      {status?.ok && (
        <ExportCheck key={`${label}-${status.count ?? 0}`} count={status.count} />
      )}
    </button>
  )
}

function ExportCheck({ count }) {
  const ref = useRef(null)
  useGSAP(() => {
    if (!ref.current) return
    gsap.from(ref.current, {
      scale: 0,
      opacity: 0,
      duration: 0.28,
      ease: 'back.out(2)',
    })
  })
  return (
    <span ref={ref} className="export-check">
      ✓ {count ? `${count} items` : ''}
    </span>
  )
}

export default function ExportHub({ projectId, stories = [], tasks = [] }) {
  const [status, setStatus] = useState({})
  const [approvedOnly, setApprovedOnly] = useState(false)

  useEffect(() => {
    const fn = () =>
      document.getElementById('export-hub')?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      })
    window.addEventListener('helix:open-export', fn)
    return () => window.removeEventListener('helix:open-export', fn)
  }, [])

  const setOk = (key, count) => {
    setStatus((s) => ({ ...s, [key]: { ok: true, count } }))
    window.setTimeout(
      () => setStatus((s) => ({ ...s, [key]: { ...s[key], ok: false } })),
      2400,
    )
  }

  const exportParams = { approved_only: approvedOnly }

  const jira = async () => {
    try {
      const { data } = await api.post(`/export/jira/${projectId}`, null, {
        params: exportParams,
      })
      if (data.mode === 'rest') {
        const n = (data.created_keys || []).length
        if (data.delivered) {
          toast.success(`JIRA: created ${n} issue(s)${data.epic_key ? ` (epic ${data.epic_key})` : ''}`)
          setOk('jira', n)
        } else {
          toast.error(data.errors?.[0] || 'JIRA REST export failed — check JIRA_* env and issue types')
        }
        return
      }
      const count = data.delivered
        ? Math.max(1, Math.round((data.csv_bytes || 0) / 800))
        : 0
      toast.success(
        data.delivered ? 'Posted to JIRA webhook' : 'JIRA webhook not configured',
      )
      setOk('jira', count)
    } catch {
      toast.error('JIRA export failed')
    }
  }

  const githubApi = async () => {
    try {
      const { data } = await api.post(`/export/github/${projectId}`, null, {
        params: exportParams,
      })
      const n = (data.issue_urls || []).length
      if (data.ok && n) {
        toast.success(`GitHub: opened ${n} issue(s)`)
        setOk('github', n)
      } else {
        toast.error(data.detail || data.errors?.[0] || 'GitHub export failed')
      }
    } catch (e) {
      const msg = e.response?.data?.detail || e.response?.statusText
      toast.error(msg ? String(msg) : 'GitHub export failed')
    }
  }

  const download = async (kind) => {
    try {
      const path = kind === 'csv' ? `/export/csv/${projectId}` : `/export/json/${projectId}`
      const { data } = await api.get(path, {
        responseType: 'blob',
        params: exportParams,
      })
      const blob = new Blob([data], {
        type: kind === 'csv' ? 'text/csv' : 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = kind === 'csv' ? 'helix-export.csv' : 'helix-export.json'
      a.click()
      URL.revokeObjectURL(url)
      const { stories: ss, tasks: tt } = approvedOnly
        ? sliceApprovedForExport(stories, tasks)
        : { stories: stories || [], tasks: tasks || [] }
      setOk(kind, (tt?.length || 0) + (ss?.length || 0))
      toast.success(`${kind.toUpperCase()} downloaded`)
    } catch {
      toast.error('Download failed')
    }
  }

  const downloadServerMarkdown = async () => {
    try {
      const { data } = await api.get(`/export/markdown/${projectId}`, {
        responseType: 'blob',
        params: exportParams,
      })
      const blob = new Blob([data], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'helix-export.md'
      a.click()
      URL.revokeObjectURL(url)
      const { stories: ss, tasks: tt } = approvedOnly
        ? sliceApprovedForExport(stories, tasks)
        : { stories: stories || [], tasks: tasks || [] }
      setOk('md', (tt?.length || 0) + (ss?.length || 0))
      toast.success('Markdown downloaded')
    } catch {
      toast.error('Markdown download failed')
    }
  }

  const githubMd = () => {
    const { stories: ss, tasks: tt } = approvedOnly
      ? sliceApprovedForExport(stories, tasks)
      : { stories: stories || [], tasks: tasks || [] }
    const lines = ['# Helix export — GitHub issues draft', '']
    for (const s of ss) {
      lines.push(`## Story: ${s.title}`, s.goal || '', '')
    }
    for (const t of tt) {
      lines.push(`### Task: ${t.title}`, `- ${t.description || ''}`, '')
    }
    let body = lines.join('\n')
    body += buildExportAuditFooter()
    const blob = new Blob([body], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'helix-github-issues.md'
    a.click()
    URL.revokeObjectURL(url)
    setOk('githubMd', lines.length)
    toast.success('GitHub-flavored bundle saved')
  }

  return (
    <div className="export-hub" id="export-hub">
      <div className="export-hub-title-row">
        <h4>Export</h4>
        <span
          className="export-gate-tip"
          title={EXPORT_SECTION_HELP}
          aria-label={EXPORT_SECTION_HELP}
        >
          ⓘ
        </span>
      </div>
      <label
        className="export-approved-only"
        title="When checked, JIRA, GitHub, CSV, JSON, server Markdown, and the GitHub .md draft only include stories and tasks marked Export OK (parent story must be approved for linked tasks)."
      >
        <input
          type="checkbox"
          checked={approvedOnly}
          onChange={(e) => setApprovedOnly(e.target.checked)}
        />
        <span>Approved only</span>
      </label>
      <div className="export-row">
        <ExportRow label="JIRA" status={status.jira} onClick={() => void jira()} />
        <ExportRow label="GitHub API" status={status.github} onClick={() => void githubApi()} />
        <ExportRow label="GitHub .md" status={status.githubMd} onClick={githubMd} />
        <ExportRow label="Markdown (server)" status={status.md} onClick={() => void downloadServerMarkdown()} />
        <ExportRow label="CSV" status={status.csv} onClick={() => void download('csv')} />
        <ExportRow label="JSON" status={status.json} onClick={() => void download('json')} />
      </div>
    </div>
  )
}
