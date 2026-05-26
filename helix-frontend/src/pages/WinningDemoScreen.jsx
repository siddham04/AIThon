import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { api } from '../api/client'
import { useProjectStore } from '../store/useStore'
import JudgeDemoPipeline from '../components/demo/JudgeDemoPipeline'
import JudgeDemoLiveTicker from '../components/demo/JudgeDemoLiveTicker'
import ReadinessScoreRing from '../components/readiness/ReadinessScoreRing'
import { AUTONOMOUS_PIPELINE } from '../lib/autonomousPipeline'
import {
  HELIX_AUTO_DEMO_KEY,
  getDemoConfigSync,
  loadDemoConfig,
  resolveDemoUseAi,
} from '../lib/demoConfig'
import {
  MESSY_DEMO_REQUIREMENT,
  beatForDemoStep,
  delay,
  demoStreamUrl,
  ensureDemoProject,
} from '../lib/winningDemoFlow'
import { readAuthToken } from '../lib/authTokenStorage'
import { checkApiHealth } from '../lib/apiHealth'

const PIPELINE_STEPS = AUTONOMOUS_PIPELINE.filter((s) => s.id !== 'export')

function beatsBefore(beatId) {
  const idx = PIPELINE_STEPS.findIndex((b) => b.id === beatId)
  return PIPELINE_STEPS.slice(0, idx).map((b) => b.id)
}

export default function WinningDemoScreen() {
  const { id: routeId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const setProjects = useProjectStore((s) => s.setProjects)

  const [localProjectId, setLocalProjectId] = useState(null)
  const projectId = routeId ?? localProjectId
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [activeBeat, setActiveBeat] = useState(null)
  const [completedBeats, setCompletedBeats] = useState(() => new Set())
  const [demoDone, setDemoDone] = useState(false)
  const [showReq, setShowReq] = useState(false)
  const [liveHeadline, setLiveHeadline] = useState('')
  const [liveDetail, setLiveDetail] = useState('')
  const [liveArtifact, setLiveArtifact] = useState(null)
  const [readinessScore, setReadinessScore] = useState(null)
  const abortRef = useRef(null)
  const projectIdRef = useRef(null)
  const completedRef = useRef(false)
  const autoStartedRef = useRef(false)

  useEffect(() => {
    void loadDemoConfig(api)
  }, [])

  useEffect(() => {
    projectIdRef.current = projectId
  }, [projectId])

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
      abortRef.current = null
    }
  }, [])

  const markBeat = useCallback((beatId, { completePrior = true } = {}) => {
    if (!beatId) return
    setActiveBeat(beatId)
    setCompletedBeats((prev) => {
      const next = new Set(prev)
      if (completePrior) {
        for (const id of beatsBefore(beatId)) next.add(id)
      }
      return next
    })
  }, [])

  const completeBeat = useCallback((beatId) => {
    if (!beatId) return
    setCompletedBeats((prev) => new Set([...prev, beatId]))
  }, [])

  const finishDemo = useCallback(
    (pid) => {
      if (completedRef.current) return
      const id = pid || projectIdRef.current || projectId
      setProgress(100)
      for (const b of PIPELINE_STEPS) completeBeat(b.id)
      setActiveBeat('package')
      completedRef.current = true
      setDemoDone(true)
      toast.success('Project Ready — delivery package ready')
      if (id) {
        setTimeout(() => {
          navigate(`/project/${id}/ai-workspace`, { replace: true })
        }, 450)
      }
    },
    [completeBeat, navigate, projectId],
  )

  const handleDemoEvent = useCallback(
    (j) => {
      if (Number.isFinite(+j.percent)) setProgress(+j.percent)
      if (j.headline) setLiveHeadline(j.headline)
      if (j.detail) setLiveDetail(j.detail)
      if (j.artifact) setLiveArtifact(j.artifact)

      const step = j.step
      if (step === 'readiness' && j.status === 'done') {
        const score = j.artifact?.readiness ?? j.percent
        if (Number.isFinite(+score)) setReadinessScore(Math.round(+score))
      }
      if (!step || step === 'boot' || step === 'persist') return

      if (step === 'complete' && j.status === 'done') {
        finishDemo(projectIdRef.current || projectId)
        return
      }

      const beat = beatForDemoStep(step)
      if (!beat) return

      if (j.status === 'running') {
        markBeat(beat.id)
      }
      if (j.status === 'done') {
        completeBeat(beat.id)
        const idx = PIPELINE_STEPS.findIndex((b) => b.id === beat.id)
        const next = PIPELINE_STEPS[idx + 1]
        if (next) setActiveBeat(next.id)
        // Finale only when backend emits complete — not on readiness (avoids ~90% early exit)
      }
      if (j.status === 'error') {
        toast.error(j.detail || `${step} failed`)
      }
    },
    [markBeat, completeBeat, finishDemo, projectId],
  )

  const runBackendDemo = useCallback(
    async (pid) => {
      const url = demoStreamUrl(pid)
      const token = readAuthToken()
      const ctrl = new AbortController()
      abortRef.current = ctrl

      const res = await fetch(url, {
        method: 'POST',
        signal: ctrl.signal,
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ use_ai: resolveDemoUseAi(true) }),
      })
      if (!res.ok || !res.body) throw new Error(`Demo failed (${res.status})`)

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
      if (!completedRef.current) finishDemo(pid)
    },
    [handleDemoEvent, finishDemo],
  )

  const startDemo = useCallback(async () => {
    if (running) return

    const health = await checkApiHealth(api)
    if (!health.ok) {
      toast.error(health.message)
      return
    }

    setRunning(true)
    setDemoDone(false)
    completedRef.current = false
    setProgress(4)
    setCompletedBeats(new Set())
    setActiveBeat('upload')
    setLiveHeadline('Extracting requirements…')
    setLiveDetail('')
    setLiveArtifact(null)
    setReadinessScore(null)
    markBeat('upload', { completePrior: false })

    try {
      let pid = projectId
      if (!pid) {
        pid = await ensureDemoProject(api, { rawText: MESSY_DEMO_REQUIREMENT })
        setLocalProjectId(pid)
        projectIdRef.current = pid
        navigate(`/project/${pid}/judge-demo`, { replace: true })
        const { data: list } = await api.get('/projects')
        setProjects(list)
      } else {
        await api
          .post('/ingest/text', { project_id: pid, text: MESSY_DEMO_REQUIREMENT })
          .catch(() => null)
      }

      completeBeat('upload')
      await delay(400)
      await runBackendDemo(pid)
    } catch (e) {
      if (e?.name !== 'AbortError') {
        toast.error(e?.message || 'Demo run failed')
        const backup = getDemoConfigSync().showcaseProjectId
        toast(
          (t) => (
            <span>
              Open pre-baked package{' '}
              <button
                type="button"
                className="btn ghost small"
                onClick={() => {
                  navigate(`/project/${backup}/ai-workspace`)
                  toast.dismiss(t.id)
                }}
              >
                {backup}
              </button>
            </span>
          ),
          { duration: 8000 },
        )
      }
    } finally {
      setRunning(false)
      abortRef.current = null
    }
  }, [running, projectId, navigate, setProjects, markBeat, completeBeat, runBackendDemo])

  useEffect(() => {
    const auto =
      location.state?.autoStart ||
      sessionStorage.getItem(HELIX_AUTO_DEMO_KEY) === '1'
    if (!auto || autoStartedRef.current) return
    autoStartedRef.current = true
    sessionStorage.removeItem(HELIX_AUTO_DEMO_KEY)
    void startDemo()
  }, [location.state?.autoStart, startDemo])

  const stopDemo = () => {
    abortRef.current?.abort()
    setRunning(false)
  }

  const showcaseId = getDemoConfigSync().showcaseProjectId
  const demoFast = getDemoConfigSync().demoFast

  const backupUrl = showcaseId
    ? `/project/${showcaseId}/ai-workspace`
    : null

  return (
    <div className="jd-page">
      {backupUrl && (
        <p className="jd-bookmark muted small">
          <strong>Backup bookmark</strong> (if SSE stalls):{' '}
          <Link to={backupUrl}>Delivery Package · {showcaseId}</Link>
        </p>
      )}
      <header className="jd-hero">
        <div className="jd-hero-copy">
          <span className="jd-eyebrow">Hackathon · Judge Demo Mode</span>
          <h1>Messy requirement → release-ready package. Under 10 minutes.</h1>
          <p className="jd-tagline">
            Upload → launch the AI team → get a release-ready Delivery Package with full
            traceability. <strong>No dashboard tour. No page switching.</strong>
          </p>
          <p className="jd-pitch muted small">
            Say: &ldquo;Helix is an autonomous SDLC team — not another requirements tool.&rdquo;
            {demoFast && (
              <>
                {' '}
                <em>(Fast demo — heuristic agents)</em>
              </>
            )}
          </p>
        </div>

        <div className="jd-hero-cta">
          {!running && !demoDone && (
            <button
              type="button"
              className="btn btn-primary btn-xl jd-start-btn"
              onClick={() => void startDemo()}
            >
              Start Autonomous SDLC Demo
            </button>
          )}
          {running && (
            <button type="button" className="btn ghost jd-stop-btn" onClick={stopDemo}>
              Stop demo
            </button>
          )}
          {!running && (
            <button
              type="button"
              className="btn ghost small jd-req-toggle"
              onClick={() => setShowReq((s) => !s)}
            >
              {showReq ? 'Hide' : 'View'} sample requirement
            </button>
          )}
          {!running && showcaseId && (
            <Link
              to={`/project/${showcaseId}/ai-workspace`}
              className="btn ghost small"
              title="Pre-baked backup if live pipeline stalls"
            >
              Open backup package ({showcaseId})
            </Link>
          )}
        </div>
      </header>

      {showReq && !running && (
        <motion.pre
          className="jd-req-preview panel"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
        >
          {MESSY_DEMO_REQUIREMENT}
        </motion.pre>
      )}

      {running && (
        <JudgeDemoLiveTicker
          headline={liveHeadline}
          detail={liveDetail}
          artifact={liveArtifact}
        />
      )}

      <div className={`jd-stage${demoDone ? ' jd-stage--finale' : ''}`}>
        <JudgeDemoPipeline
          activeBeat={activeBeat}
          completedBeats={completedBeats}
          running={running}
          progress={progress}
          liveHeadline={liveHeadline}
          liveDetail={liveDetail}
        />

        <AnimatePresence>
          {demoDone && (
            <motion.aside
              className="jd-finale panel"
              initial={{ opacity: 0, scale: 0.92, y: 24 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
            >
              <p className="jd-finale-eyebrow">End state</p>
              <h2>Delivery Readiness</h2>
              {readinessScore != null ? (
                <div className="jd-finale-ring">
                  <ReadinessScoreRing
                    score={readinessScore}
                    statusLabel={readinessScore >= 60 ? 'PROJECT READY' : 'NEEDS REVIEW'}
                  />
                </div>
              ) : (
                <div className="jd-finale-ring jd-finale-ring--pending">
                  <p className="muted small">Awaiting final readiness from delivery gate…</p>
                </div>
              )}
              <p className="jd-finale-copy muted">
                Opening delivery package automatically… stories, architecture, tests, sprint plan,
                and exports.
              </p>
              {readinessScore != null && (
                <p className="jd-finale-honest muted small">
                  Readiness {readinessScore}% from live delivery gates after this run — not a
                  static placeholder. Tasks are generated per story for Jira export.
                </p>
              )}
              {projectId && (
                <div className="jd-finale-actions">
                  <Link
                    to={`/project/${projectId}/ai-workspace`}
                    className="btn ghost small"
                  >
                    Open package now (skip wait)
                  </Link>
                </div>
              )}
            </motion.aside>
          )}
        </AnimatePresence>
      </div>

      {!demoDone && !running && (
        <p className="jd-foot muted small">
          Press <strong>Start Autonomous SDLC Demo</strong> — progress is driven only by live SSE
          (no fake timers).
        </p>
      )}
    </div>
  )
}
