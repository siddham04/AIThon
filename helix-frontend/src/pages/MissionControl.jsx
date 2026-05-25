import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import AutonomousPipelineStrip from '../components/pipeline/AutonomousPipelineStrip'
import { pipelineIdForDemoStep } from '../lib/autonomousPipeline'
import { Link, useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '../api/client'
import MissionAgentExecution from '../components/mission/MissionAgentExecution'
import VoiceInput from '../components/ingestion/VoiceInput'
import { SAMPLE_REQUIREMENT } from '../constants/sampleRequirement'
import { useProjectStore } from '../store/useStore'
import { resolveDemoUseAi } from '../lib/demoConfig'
import { demoStreamUrl } from '../lib/winningDemoFlow'
import {
  applyDemoEvent,
  createInitialExecution,
  seedLaunchLogs,
} from '../lib/missionAgents'
import { buildConfigPreamble } from '../lib/missionConfig'
import { loadHumanSettings, settingsToMissionConfig } from '../lib/helixSettings'
import McLiveNarration from '../components/mission/McLiveNarration'
import { readAuthToken } from '../lib/authTokenStorage'

const SAMPLE_PREFILL_KEY = 'helix_prefill_sample'

function readSamplePrefill() {
  let applied = false
  try {
    if (sessionStorage.getItem(SAMPLE_PREFILL_KEY) === '1') {
      sessionStorage.removeItem(SAMPLE_PREFILL_KEY)
      applied = true
    }
  } catch {
    /* noop */
  }
  return {
    applied,
    text: applied ? SAMPLE_REQUIREMENT : '',
    name: applied ? 'Demo — Unified Pay & Identity' : '',
    inputMode: 'text',
  }
}

const INPUT_MODES = [
  { id: 'text', label: 'Paste', hint: 'PRD or messy requirements' },
  { id: 'pdf', label: 'PDF', hint: '.pdf', accept: '.pdf' },
  { id: 'docx', label: 'DOCX', hint: '.docx', accept: '.doc,.docx' },
]

const ADVANCED_MODES = [
  { id: 'jira', label: 'Jira', hint: 'Ticket export' },
  { id: 'meeting', label: 'Meeting', hint: 'Transcript' },
  { id: 'voice', label: 'Voice', hint: 'Chrome/Edge' },
]

function executionReducer(state, action) {
  switch (action.type) {
    case 'reset':
      return { ...createInitialExecution(), logs: seedLaunchLogs() }
    case 'event':
      return applyDemoEvent(state, action.payload)
    default:
      return state
  }
}

export default function MissionControl() {
  const { id: routeId } = useParams()
  const navigate = useNavigate()
  const setProjects = useProjectStore((s) => s.setProjects)

  const [samplePrefill] = useState(readSamplePrefill)
  const [localProjectId, setLocalProjectId] = useState(null)
  const projectId = routeId ?? localProjectId
  const [project, setProject] = useState(null)
  const [inputMode, setInputMode] = useState(samplePrefill.inputMode)
  const [name, setName] = useState(samplePrefill.name)
  const [text, setText] = useState(samplePrefill.text)
  const [file, setFile] = useState(null)
  const [fileLabel, setFileLabel] = useState('')
  const [status, setStatus] = useState({
    processing: false,
    readiness: null,
    forecast: null,
    risks: [],
  })
  const [launching, setLaunching] = useState(false)
  const [pipelineRunning, setPipelineRunning] = useState(false)
  const [pipelineErrors, setPipelineErrors] = useState([])
  const [liveHeadline, setLiveHeadline] = useState('')
  const [liveDetail, setLiveDetail] = useState('')
  const [showAdvancedInput, setShowAdvancedInput] = useState(false)
  const [demoComplete, setDemoComplete] = useState(false)
  const [execution, dispatchExecution] = useReducer(executionReducer, null, () =>
    createInitialExecution(),
  )
  const abortRef = useRef(null)
  const fileInputRef = useRef(null)
  const completedRef = useRef(false)

  useEffect(() => {
    if (samplePrefill.applied) toast.success('Sample requirement loaded')
  }, [samplePrefill.applied])

  const refreshStatus = useCallback(async (pid) => {
    if (!pid) return
    try {
      const [ready, pm, arts] = await Promise.all([
        api.get(`/readiness-center/${pid}`).catch(() => ({ data: null })),
        api.get(`/delivery/pm/${pid}`).catch(() => ({ data: null })),
        api.get(`/artifacts/${pid}`).catch(() => ({ data: null })),
      ])
      const risks = [
        ...(arts.data?.risks?.map((r) => r.title) || []),
        ...(ready.data?.blocking_items || []),
      ].slice(0, 6)
      setStatus((s) => ({
        ...s,
        readiness: ready.data?.readiness ?? ready.data?.overall_score ?? null,
        forecast: pm.data?.release_risk || pm.data?.timeline?.[0]?.label || null,
        risks,
      }))
    } catch {
      /* noop */
    }
  }, [])

  useEffect(() => {
    if (!projectId) return undefined
    let cancelled = false
    api
      .get(`/projects/${projectId}`)
      .then(({ data }) => {
        if (!cancelled) {
          setProject(data)
          if (!text.trim() && data.raw_input) setText(data.raw_input)
        }
      })
      .catch(() => {
        if (!cancelled) toast.error('Could not load project')
      })
    return () => {
      cancelled = true
    }
  }, [projectId, text])

  const handleDemoEvent = useCallback((j) => {
    dispatchExecution({ type: 'event', payload: j })
    if (j.headline) setLiveHeadline(j.headline)
    if (j.detail) setLiveDetail(j.detail)
    if (j.status === 'error' && j.step) {
      setPipelineErrors((prev) => {
        const next = prev.filter((e) => e.step !== j.step)
        return [
          ...next,
          {
            step: j.step,
            detail: j.detail || j.headline || 'Step failed',
          },
        ]
      })
      toast.error(`${j.step}: ${j.detail || j.headline || 'failed'}`)
    }
    if (j.step === 'complete' && j.status === 'done') {
      completedRef.current = true
      setDemoComplete(true)
      toast.success('AI team finished — review checklist & Approve & Export')
    }
  }, [])

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
      abortRef.current = null
      setPipelineRunning(false)
      setLaunching(false)
    }
  }, [])

  const runPipeline = useCallback(
    async (pid) => {
      const ctrl = new AbortController()
      abortRef.current = ctrl
      const token = readAuthToken()
      const res = await fetch(demoStreamUrl(pid), {
        method: 'POST',
        signal: ctrl.signal,
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ use_ai: resolveDemoUseAi(true) }),
      })
      if (!res.ok || !res.body) throw new Error(`Pipeline failed (${res.status})`)

      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        const blocks = buf.split('\n\n')
        buf = blocks.pop() || ''
        for (const block of blocks) {
          for (const line of block.split('\n')) {
            if (!line.startsWith('data: ')) continue
            try {
              handleDemoEvent(JSON.parse(line.slice(6)))
            } catch {
              /* ignore */
            }
          }
        }
      }
    },
    [handleDemoEvent],
  )

  const resolveRequirementBody = useCallback(async () => {
    const preamble = buildConfigPreamble(settingsToMissionConfig(loadHumanSettings()))
    if (inputMode === 'text' || inputMode === 'jira' || inputMode === 'meeting') {
      const body = text.trim()
      if (!body) return null
      return preamble + body
    }
    if ((inputMode === 'pdf' || inputMode === 'docx') && file) {
      const fd = new FormData()
      fd.append('file', file)
      if (name.trim()) fd.append('name', name.trim())
      // Let axios derive the multipart boundary; don't force Content-Type or boundary will be missing.
      const { data } = await api.post('/ingest/file', fd, {
        headers: { 'Content-Type': undefined },
      })
      const pid = data.project_id
      const { data: proj } = await api.get(`/projects/${pid}`)
      const fullText = preamble + (proj.raw_input || '')
      await api.post('/ingest/text', { project_id: pid, text: fullText }).catch(() => null)
      return { projectId: pid, alreadyIngested: true }
    }
    return null
  }, [inputMode, text, file, name])

  const launchAiTeam = useCallback(async () => {
    if (launching || pipelineRunning) return

    const needsFile = inputMode === 'pdf' || inputMode === 'docx'
    const needsText = inputMode === 'text' || inputMode === 'jira' || inputMode === 'meeting'
    if (needsFile && !file) {
      toast.error(`Choose a file — ${INPUT_MODES.find((m) => m.id === inputMode)?.label}`)
      fileInputRef.current?.click()
      return
    }
    if (needsText && !text.trim()) {
      toast.error('Paste or type requirements first')
      return
    }

    setLaunching(true)
    setPipelineRunning(true)
    completedRef.current = false
    setDemoComplete(false)
    setPipelineErrors([])
    setLiveHeadline('')
    setLiveDetail('')
    dispatchExecution({ type: 'reset' })

    try {
      let pid = projectId
      const resolved = await resolveRequirementBody()

      if (resolved && typeof resolved === 'object' && resolved.alreadyIngested) {
        pid = resolved.projectId
      } else if (typeof resolved === 'string') {
        if (pid) {
          await api.post('/ingest/text', { project_id: pid, text: resolved }).catch(() => null)
        } else {
          const { data } = await api.post('/ingest/text', {
            text: resolved,
            name: name.trim() || undefined,
          })
          pid = data.project_id
        }
      }

      if (!pid) {
        toast.error('Could not create project')
        return
      }

      setLocalProjectId(pid)
      navigate(`/project/${pid}/mission-control`, { replace: true })
      const { data: list } = await api.get('/projects')
      setProjects(list)

      setStatus((s) => ({ ...s, processing: true }))
      await runPipeline(pid)
      await refreshStatus(pid)
      setStatus((s) => ({ ...s, processing: false }))

      if (completedRef.current) {
        setTimeout(() => navigate(`/project/${pid}/ai-workspace`, { replace: true }), 450)
      }
    } catch (e) {
      if (e?.name !== 'AbortError') {
        toast.error(e?.message || 'Launch failed')
      }
    } finally {
      setLaunching(false)
      setPipelineRunning(false)
      abortRef.current = null
    }
  }, [
    launching,
    pipelineRunning,
    inputMode,
    file,
    text,
    projectId,
    name,
    navigate,
    setProjects,
    resolveRequirementBody,
    runPipeline,
    refreshStatus,
  ])

  const onPickFile = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    setFileLabel(f.name)
    e.target.value = ''
  }

  const activeAccept =
    INPUT_MODES.find((m) => m.id === inputMode)?.accept || '.txt,.md,.pdf,.doc,.docx'

  const showRunning = pipelineRunning || launching
  const globalPercent = execution.globalPercent

  const pipelineCompleted = useMemo(() => {
    const done = new Set(['upload'])
    if (showRunning) done.add('launch')
    for (const step of execution.completedSteps) {
      const pid = pipelineIdForDemoStep(step)
      if (pid) done.add(pid)
    }
    if (demoComplete) {
      done.add('package')
    }
    return done
  }, [execution.completedSteps, showRunning, demoComplete])

  const pipelineActive = useMemo(() => {
    if (execution.currentStep) return pipelineIdForDemoStep(execution.currentStep)
    if (launching) return 'launch'
    if (pipelineRunning) return 'launch'
    return null
  }, [execution.currentStep, launching, pipelineRunning])

  return (
    <div className={`mc-landing${showRunning ? ' mc-landing--running' : ''}`}>
      <div className="mc-hero">
        <div className="mc-hero-glow" aria-hidden />
        <p className="mc-hero-brand">HELIX</p>
        <h1 className="mc-hero-title">Mission Control</h1>
        <p className="mc-hero-sub">
          Upload your own requirement here.{' '}
          <strong>Judges:</strong> use{' '}
          <Link to="/judge-demo" className="mc-judge-link">
            Judge Demo
          </Link>{' '}
          for the 5-minute autonomous path — no input choices needed.
        </p>
      </div>

      {pipelineErrors.length > 0 && (
        <section className="mc-pipeline-errors" role="alert" aria-live="polite">
          <h2 className="mc-card-label">Pipeline warnings</h2>
          <ul>
            {pipelineErrors.map((e) => (
              <li key={e.step}>
                <strong>{e.step}</strong>: {e.detail}
              </li>
            ))}
          </ul>
        </section>
      )}

      {(showRunning || status.readiness != null) && (
        <div className="p5-grid-2 mc-status-strip mc-status-strip--scroll">
          <div className="p5-stat">
            <p className="p5-stat-label">Processing</p>
            <p className="p5-stat-value">{showRunning ? `${Math.round(globalPercent)}%` : 'Done'}</p>
          </div>
          <div className="p5-stat">
            <p className="p5-stat-label">Readiness</p>
            <p className="p5-stat-value">{status.readiness != null ? `${status.readiness}%` : '—'}</p>
          </div>
          <div className="p5-stat">
            <p className="p5-stat-label">Delivery forecast</p>
            <p className="p5-stat-value" style={{ fontSize: '1rem' }}>
              {status.forecast || '—'}
            </p>
          </div>
          <div className="p5-stat">
            <p className="p5-stat-label">Risks</p>
            <p className="p5-stat-value" style={{ fontSize: '1rem' }}>
              {status.risks.length ? `${status.risks.length} flagged` : '—'}
            </p>
          </div>
        </div>
      )}

      {!showRunning && <AutonomousPipelineStrip showExport={false} />}

      <section className="mc-card mc-input-card">
        <h2 className="mc-card-label">Upload requirement</h2>
        <p className="muted small mc-input-hint">
          Default: paste text. File upload is one click — no need to pick four modes for the demo.
        </p>
        <div className="mc-input-tiles" role="tablist" aria-label="Input type">
          {INPUT_MODES.map((mode) => (
            <button
              key={mode.id}
              type="button"
              role="tab"
              aria-selected={inputMode === mode.id}
              className={`mc-input-tile${inputMode === mode.id ? ' is-active' : ''}`}
              onClick={() => {
                setInputMode(mode.id)
                if (mode.id === 'pdf' || mode.id === 'docx') {
                  setTimeout(() => fileInputRef.current?.click(), 0)
                }
              }}
            >
              <span className="mc-input-tile-label">{mode.label}</span>
              <span className="mc-input-tile-hint">{mode.hint}</span>
            </button>
          ))}
          <button
            type="button"
            className="mc-input-tile mc-input-tile--more"
            aria-expanded={showAdvancedInput}
            onClick={() => setShowAdvancedInput((v) => !v)}
          >
            <span className="mc-input-tile-label">More</span>
            <span className="mc-input-tile-hint">Jira · meeting · voice</span>
          </button>
        </div>
        {showAdvancedInput && (
          <div className="mc-input-tiles mc-input-tiles--advanced" role="tablist">
            {ADVANCED_MODES.map((mode) => (
              <button
                key={mode.id}
                type="button"
                role="tab"
                aria-selected={inputMode === mode.id}
                className={`mc-input-tile${inputMode === mode.id ? ' is-active' : ''}`}
                onClick={() => setInputMode(mode.id)}
              >
                <span className="mc-input-tile-label">{mode.label}</span>
                <span className="mc-input-tile-hint">{mode.hint}</span>
              </button>
            ))}
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          className="mc-file-input"
          accept={activeAccept}
          onChange={onPickFile}
          tabIndex={-1}
          aria-hidden
        />

        {inputMode === 'voice' && (
          <div className="mc-text-wrap mc-voice-wrap">
            <VoiceInput value={text} onChange={setText} disabled={showRunning} />
            <p className="muted small">
              Voice stays in the browser until you launch — nothing is sent until the pipeline runs.
            </p>
          </div>
        )}

        {(inputMode === 'text' || inputMode === 'jira' || inputMode === 'meeting') && (
          <div className="mc-text-wrap">
            <textarea
              className="mc-textarea"
              rows={inputMode === 'meeting' ? 10 : 8}
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={showRunning}
              placeholder={
                inputMode === 'meeting'
                  ? 'Paste meeting transcript or standup notes…'
                  : inputMode === 'jira'
                    ? 'Paste Jira ticket description, acceptance criteria, comments…'
                    : 'Paste PRD, email, or messy requirements…'
              }
            />
            <div className="mc-text-meta">
              <button
                type="button"
                className="btn ghost small"
                disabled={showRunning}
                onClick={() => {
                  setText(SAMPLE_REQUIREMENT)
                  setName((n) => n || 'Demo — Unified Pay & Identity')
                }}
              >
                Load demo PRD
              </button>
              <span className="muted small">
                {text.trim() ? `${text.trim().split(/\s+/).length} words` : 'No text yet'}
              </span>
            </div>
          </div>
        )}

        {(inputMode === 'pdf' || inputMode === 'docx') && (
          <div className="mc-file-zone">
            <button
              type="button"
              className="mc-file-pick"
              disabled={showRunning}
              onClick={() => fileInputRef.current?.click()}
            >
              {fileLabel ? (
                <>
                  <strong>{fileLabel}</strong>
                  <span className="muted small">Click to replace</span>
                </>
              ) : (
                <>
                  <strong>Drop or browse</strong>
                  <span className="muted small">{activeAccept}</span>
                </>
              )}
            </button>
          </div>
        )}

        <label className="mc-name-field">
          <span className="muted small">Mission name (optional)</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={project?.name || 'e.g. OTP login rollout'}
            disabled={showRunning}
          />
        </label>
      </section>

      <p className="muted small" style={{ marginBottom: '1rem' }}>
        Team size, velocity, and credentials are in <a href="/settings">Settings</a>.
      </p>

      <div className="mc-cta-wrap">
        <button
          type="button"
          className="mc-launch-cta"
          disabled={showRunning}
          onClick={() => void launchAiTeam()}
        >
          <span className="mc-launch-cta-text">
            {showRunning ? 'AI team running…' : 'Launch AI team'}
          </span>
          {!showRunning && <span className="mc-launch-cta-sub">Full SDLC pipeline · ~2 min</span>}
        </button>
        {showRunning && (
          <p className="muted small mc-cta-status">
            Pipeline {Math.round(globalPercent)}% — agents executing below
          </p>
        )}
        {projectId && !showRunning && (
          <button
            type="button"
            className="btn ghost small mc-secondary-link"
            onClick={() => navigate(`/project/${projectId}/ai-workspace`)}
          >
            AI Workspace →
          </button>
        )}
      </div>

      {showRunning && (
        <McLiveNarration
          headline={liveHeadline}
          detail={liveDetail}
          percent={globalPercent}
        />
      )}

      {showRunning && (
        <>
          <AutonomousPipelineStrip
            compact
            showExport={false}
            activeStepId={pipelineActive}
            completedStepIds={pipelineCompleted}
          />
          <MissionAgentExecution
          execution={execution}
          globalPercent={globalPercent}
          running={pipelineRunning}
          onStop={() => {
            abortRef.current?.abort()
            abortRef.current = null
            setPipelineRunning(false)
            setLaunching(false)
            toast('Pipeline stopped')
          }}
        />
        </>
      )}
    </div>
  )
}
