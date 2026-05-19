import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import toast from 'react-hot-toast'
import { api } from '../api/client'
import FileDropzone from '../components/ingestion/FileDropzone'
import VoiceInput from '../components/ingestion/VoiceInput'
import { SAMPLE_REQUIREMENT } from '../constants/sampleRequirement'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import KeyboardShortcutsHelp from '../components/ui/KeyboardShortcutsHelp'

const SAMPLE_PREFILL_KEY = 'helix_prefill_sample'

export default function NewProject() {
  const nav = useNavigate()
  const [tab, setTab] = useState('paste')
  const [name, setName] = useState('')
  const [text, setText] = useState('')
  const [url, setUrl] = useState('')
  const [progress, setProgress] = useState(0)
  const [busy, setBusy] = useState(false)
  const [file, setFile] = useState(null)
  const progressWrapRef = useRef(null)
  const progressFillRef = useRef(null)

  useEffect(() => {
    queueMicrotask(() => {
      try {
        if (sessionStorage.getItem(SAMPLE_PREFILL_KEY) === '1') {
          sessionStorage.removeItem(SAMPLE_PREFILL_KEY)
          setText(SAMPLE_REQUIREMENT)
          setName((n) => n || 'Demo — Unified Pay & Identity')
          setTab('paste')
          toast.success('Sample requirement loaded')
        }
      } catch {
        /* noop */
      }
    })
  }, [])

  const wc = text.trim() ? text.trim().split(/\s+/).filter(Boolean).length : 0

  const run = async (fn) => {
    setBusy(true)
    setProgress(12)
    const t = window.setInterval(() => {
      setProgress((p) => Math.min(92, p + 7 + Math.random() * 8))
    }, 220)
    try {
      await fn()
    } finally {
      window.clearInterval(t)
      setProgress(100)
      setTimeout(() => {
        setProgress(0)
        setBusy(false)
      }, 400)
    }
  }

  const submitPaste = () =>
    run(async () => {
      const { data } = await api.post('/ingest/text', {
        text: text.trim(),
        name: name.trim() || undefined,
      })
      const hints = data.sensitive_hints
      if (Array.isArray(hints) && hints.length && data.project_id) {
        try {
          sessionStorage.setItem(
            `helix_ingest_hints_${data.project_id}`,
            JSON.stringify(hints),
          )
        } catch {
          /* noop */
        }
      }
      toast.success('Requirements ingested')
      nav(`/project/${data.project_id}`)
    })

  const submitUrl = () =>
    run(async () => {
      const { data } = await api.post('/ingest/url', {
        url: url.trim(),
        name: name.trim() || undefined,
      })
      const hints = data.sensitive_hints
      if (Array.isArray(hints) && hints.length && data.project_id) {
        try {
          sessionStorage.setItem(
            `helix_ingest_hints_${data.project_id}`,
            JSON.stringify(hints),
          )
        } catch {
          /* noop */
        }
      }
      toast.success('URL imported')
      nav(`/project/${data.project_id}`)
    })

  const submitFile = () =>
    run(async () => {
      if (!file) {
        toast.error('Choose a file first')
        throw new Error('no file')
      }
      const fd = new FormData()
      fd.append('file', file)
      if (name.trim()) fd.append('name', name.trim())
      const { data } = await api.post('/ingest/file', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const hints = data.sensitive_hints
      if (Array.isArray(hints) && hints.length && data.project_id) {
        try {
          sessionStorage.setItem(
            `helix_ingest_hints_${data.project_id}`,
            JSON.stringify(hints),
          )
        } catch {
          /* noop */
        }
      }
      toast.success('File ingested')
      nav(`/project/${data.project_id}`)
    })

  const { helpOpen, setHelpOpen } = useKeyboardShortcuts({
    onSubmit: () => {
      if (tab === 'paste') void submitPaste().catch(() => toast.error('Ingest failed'))
      if (tab === 'url') void submitUrl().catch(() => toast.error('Import failed'))
      if (tab === 'file') void submitFile().catch(() => toast.error('Upload failed'))
    },
    enabled: true,
  })

  useGSAP(
    () => {
      const wrap = progressWrapRef.current
      if (!wrap) return
      if (busy && progress > 0) {
        gsap.fromTo(
          wrap,
          { opacity: 0, height: 0 },
          { opacity: 1, height: 'auto', duration: 0.28, ease: 'power2.out' },
        )
      }
    },
    { dependencies: [busy, progress] },
  )

  useGSAP(
    () => {
      const fill = progressFillRef.current
      if (!fill || !busy) return
      gsap.to(fill, {
        width: `${progress}%`,
        duration: 0.35,
        ease: 'power2.out',
        overwrite: 'auto',
      })
    },
    { dependencies: [progress, busy] },
  )

  return (
    <div className="page new-project">
      <header className="page-head">
        <h1>New project</h1>
        <p className="muted">Ingest requirements — then generate artifacts on the dashboard.</p>
      </header>

      <div className="judge-demo-banner" role="note">
        <strong>Judge-ready (no mic):</strong> open <strong>Paste text</strong> →{' '}
        <strong>Load sample requirement</strong> → <strong>Ingest</strong>. Same pipeline as paste/voice;
        see <code>docs/RUNBOOK.md</code> in the repo.
      </div>

      <div className="tabs">
        {['paste', 'file', 'url'].map((id) => (
          <button
            key={id}
            type="button"
            className={`tab ${tab === id ? 'active' : ''}`}
            onClick={() => setTab(id)}
          >
            {id === 'paste' ? 'Paste text' : id === 'file' ? 'Upload file' : 'URL import'}
          </button>
        ))}
      </div>

      <label className="field">
        Project name (optional)
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Mobile checkout" />
      </label>

      {tab === 'paste' && (
        <label className="field">
          Requirements
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={14}
            placeholder="Paste PRD / BRD / user flows…"
          />
          <div className="ingestion-extras">
            <button
              type="button"
              className={`btn small-btn ${text.trim() ? 'ghost' : 'btn-primary'}`}
              disabled={busy}
              onClick={() => {
                setText(SAMPLE_REQUIREMENT)
                setName((n) => n || 'Demo — Unified Pay & Identity')
                toast.success('Loaded demo requirement')
              }}
            >
              Load sample requirement
            </button>
            <VoiceInput value={text} onChange={setText} disabled={busy} />
          </div>
        </label>
      )}

      {tab === 'file' && <FileDropzone onFile={setFile} disabled={busy} />}

      {tab === 'url' && (
        <label className="field">
          URL
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://…"
          />
        </label>
      )}

      <div className="row spread">
        <span className="badge">{wc} words</span>
        <button
          type="button"
          className="btn btn-primary"
          disabled={busy}
          onClick={() => {
            if (tab === 'paste') void submitPaste().catch(() => toast.error('Ingest failed'))
            if (tab === 'url') void submitUrl().catch(() => toast.error('Import failed'))
            if (tab === 'file') void submitFile().catch(() => toast.error('Upload failed'))
          }}
        >
          Ingest
        </button>
      </div>

      {busy && progress > 0 && (
        <div ref={progressWrapRef} className="upload-progress">
          <div className="upload-bar">
            <div ref={progressFillRef} className="upload-bar-fill" style={{ width: 0 }} />
          </div>
          <span className="muted small">Processing… {Math.round(progress)}%</span>
        </div>
      )}

      <button type="button" className="linkish" onClick={() => setHelpOpen(true)}>
        Keyboard shortcuts (?)
      </button>

      <KeyboardShortcutsHelp open={helpOpen} onClose={() => setHelpOpen(false)} variant="ingest" />
    </div>
  )
}
