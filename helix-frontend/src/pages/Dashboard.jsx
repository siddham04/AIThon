import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import toast from 'react-hot-toast'
import { api } from '../api/client'
import {
  useArtifactStore,
  useProjectStore,
} from '../store/useStore'
import SummaryCard from '../components/artifacts/SummaryCard'
import KanbanBoard from '../components/artifacts/KanbanBoard'
import TestCaseList from '../components/artifacts/TestCaseList'
import CopilotPanel from '../components/chat/CopilotPanel'
import AmbiguityView from '../components/ambiguity/AmbiguityView'
import ExportHub from '../components/export/ExportHub'
import SensitiveHintsBanner from '../components/trust/SensitiveHintsBanner'
import VersionHistory from '../components/VersionHistory'
import WorkingVsSnapshotDiff from '../components/diff/WorkingVsSnapshotDiff'
import RequirementSinceGenerateDiff from '../components/diff/RequirementSinceGenerateDiff'
import TaskProgressStrip from '../components/dashboard/TaskProgressStrip'
import ReadinessPanel from '../components/dashboard/ReadinessPanel'
import { followTaskProgress } from '../lib/followTaskProgress'
import { DashboardSkeleton } from '../components/ui/Skeleton'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import { buildHelixBundleMarkdown } from '../lib/buildHelixMarkdown'

export default function Dashboard() {
  const { id } = useParams()
  const setCurrent = useProjectStore((s) => s.setCurrentProject)
  const currentProject = useProjectStore((s) => s.currentProject)
  const {
    stories,
    tasks,
    summary,
    testcases,
    ambiguities,
    rawRequirement,
    citationItemRate,
    setBundle,
    setTestcases,
    setAmbiguities,
    setRawRequirement,
    resetBoard,
    loadingArtifacts,
    loadingTests,
    setLoadingArtifacts,
    setLoadingTests,
    setStoryExportApproval,
    setTaskExportApproval,
  } = useArtifactStore()

  const [boot, setBoot] = useState(true)
  const [workingReq, setWorkingReq] = useState('')
  const [sensitiveHints, setSensitiveHints] = useState([])
  const [reqFocusMode, setReqFocusMode] = useState(false)
  const lastPushedRef = useRef('')
  const [snapRefresh, setSnapRefresh] = useState(0)
  const requirementSectionRef = useRef(null)
  const requirementBeforeGenRef = useRef('')
  const artifactWsDisposeRef = useRef(() => {})
  const testWsDisposeRef = useRef(() => {})
  const [artifactProgress, setArtifactProgress] = useState(null)
  const [testProgress, setTestProgress] = useState(null)
  const [lastGenReqDiff, setLastGenReqDiff] = useState(null)

  useEffect(() => {
    return () => {
      artifactWsDisposeRef.current()
      testWsDisposeRef.current()
    }
  }, [])

  useEffect(() => {
    queueMicrotask(() => {
      setWorkingReq(rawRequirement)
      lastPushedRef.current = rawRequirement
    })
  }, [rawRequirement])

  useEffect(() => {
    if (!id || !workingReq.trim()) return
    const t = window.setTimeout(() => {
      if (workingReq === lastPushedRef.current) return
      void api
        .post(`/projects/${id}/requirement-versions`, { text: workingReq })
        .then(() => {
          lastPushedRef.current = workingReq
          setSnapRefresh((k) => k + 1)
        })
        .catch(() => {})
    }, 1600)
    return () => window.clearTimeout(t)
  }, [workingReq, id])

  useEffect(() => {
    const fn = () => {
      requirementSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      requirementSectionRef.current?.querySelector('textarea')?.focus?.()
    }
    window.addEventListener('helix:focus-requirement', fn)
    return () => window.removeEventListener('helix:focus-requirement', fn)
  }, [])

  const copyBundleMarkdown = useCallback(async () => {
    const md = buildHelixBundleMarkdown({
      projectName: currentProject?.name,
      summary,
      stories,
      tasks,
      workingRequirement: workingReq,
      citationItemRate,
    })
    try {
      await navigator.clipboard.writeText(md)
      toast.success('Copied bundle as Markdown')
    } catch {
      toast.error('Clipboard not available')
    }
  }, [currentProject?.name, summary, stories, tasks, workingReq, citationItemRate])

  useEffect(() => {
    if (!id) return
    let ingest = []
    try {
      const k = `helix_ingest_hints_${id}`
      const raw = sessionStorage.getItem(k)
      if (raw) ingest = JSON.parse(raw)
      sessionStorage.removeItem(k)
    } catch {
      ingest = []
    }
    const apiHints =
      currentProject?.id === id ? currentProject.sensitive_hints || [] : []
    queueMicrotask(() => {
      setSensitiveHints([...new Set([...ingest, ...apiHints].map(String))])
    })
  }, [id, currentProject?.id, currentProject?.sensitive_hints])

  const loadArtifacts = useCallback(async () => {
    setLoadingArtifacts(true)
    try {
      const { data } = await api.get(`/artifacts/${id}`)
      setBundle(data)
      resetBoard(data.tasks || [])
      const blob = [
        data.summary?.objective,
        data.summary?.one_liner,
        ...(data.stories || []).map((s) => `${s.title}. ${s.goal}`),
      ]
        .filter(Boolean)
        .join('\n\n')
      setRawRequirement(blob)
      return { requirementBlob: blob }
    } catch {
      toast.error('Could not load artifacts')
      return { requirementBlob: '' }
    } finally {
      setLoadingArtifacts(false)
    }
  }, [id, setBundle, resetBoard, setRawRequirement, setLoadingArtifacts])

  const patchStoryExport = useCallback(
    async (storyId, approved) => {
      if (!id) return
      try {
        await api.patch(`/artifacts/${id}/stories/${storyId}/approval`, {
          approved_for_export: approved,
        })
        setStoryExportApproval(storyId, approved)
      } catch {
        toast.error('Could not update story export approval')
      }
    },
    [id, setStoryExportApproval],
  )

  const patchTaskExport = useCallback(
    async (taskId, approved) => {
      if (!id) return
      try {
        await api.patch(`/artifacts/${id}/tasks/${taskId}/approval`, {
          approved_for_export: approved,
        })
        setTaskExportApproval(taskId, approved)
      } catch {
        toast.error('Could not update task export approval')
      }
    },
    [id, setTaskExportApproval],
  )

  const loadTests = useCallback(async () => {
    setLoadingTests(true)
    try {
      const { data } = await api.get(`/testcases/${id}`)
      setTestcases(data)
    } catch {
      setTestcases([])
    } finally {
      setLoadingTests(false)
    }
  }, [id, setTestcases, setLoadingTests])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setBoot(true)
      try {
        const { data } = await api.get(`/projects/${id}`)
        if (!cancelled) setCurrent(data)
      } catch {
        if (!cancelled) setCurrent(null)
      }
      await Promise.all([loadArtifacts(), loadTests()])
      if (!cancelled) setBoot(false)
    })()
    return () => {
      cancelled = true
    }
  }, [id, loadArtifacts, loadTests, setCurrent])

  const runAmbiguity = async () => {
    try {
      const { data } = await api.post(`/ambiguity/analyze/${id}`)
      setAmbiguities(data)
      toast.success('Ambiguity scan complete')
    } catch {
      toast.error('Ambiguity analysis failed')
    }
  }

  const genArtifacts = async () => {
    if (!id) return
    requirementBeforeGenRef.current = workingReq
    artifactWsDisposeRef.current()
    artifactWsDisposeRef.current = () => {}
    try {
      const { data } = await api.post(`/artifacts/generate/${id}`)
      const taskId = data?.task_id
      if (!taskId) {
        toast.error('Could not start generation')
        return
      }
      setArtifactProgress({ percent: 0, message: 'Queued', status: 'queued' })
      const dispose = followTaskProgress(taskId, {
        onEvent: (m) =>
          setArtifactProgress({
            percent: m.percent ?? 0,
            message: String(m.message ?? ''),
            status: String(m.status ?? ''),
          }),
        onDone: async (m) => {
          setArtifactProgress(null)
          if (m.status === 'done') {
            toast.success('Artifacts ready')
            const { requirementBlob } = (await loadArtifacts()) || {}
            const after = requirementBlob ?? ''
            const before = requirementBeforeGenRef.current
            if (before !== after) setLastGenReqDiff({ before, after })
            else setLastGenReqDiff(null)
          } else {
            toast.error(String(m.message || 'Artifact generation failed'))
          }
        },
      })
      artifactWsDisposeRef.current = dispose
    } catch {
      setArtifactProgress(null)
      toast.error('Could not start generation')
    }
  }

  const genTests = async () => {
    if (!id) return
    testWsDisposeRef.current()
    testWsDisposeRef.current = () => {}
    try {
      const { data } = await api.post(`/testcases/generate/${id}`)
      const taskId = data?.task_id
      if (!taskId) {
        toast.error('Could not start test generation')
        return
      }
      setTestProgress({ percent: 0, message: 'Queued', status: 'queued' })
      const dispose = followTaskProgress(taskId, {
        onEvent: (m) =>
          setTestProgress({
            percent: m.percent ?? 0,
            message: String(m.message ?? ''),
            status: String(m.status ?? ''),
          }),
        onDone: async (m) => {
          setTestProgress(null)
          if (m.status === 'done') {
            toast.success('Tests updated')
            await loadTests()
          } else {
            toast.error(String(m.message || 'Test generation failed'))
          }
        },
      })
      testWsDisposeRef.current = dispose
    } catch {
      setTestProgress(null)
      toast.error('Could not start test generation')
    }
  }

  useKeyboardShortcuts({ enabled: true })

  const reduceMotion = useReducedMotion()
  const stagger = useMemo(
    () =>
      reduceMotion
        ? { delayChildren: 0, staggerChildren: 0 }
        : { delayChildren: 0.06, staggerChildren: 0.055 },
    [reduceMotion],
  )
  const fadeUp = useMemo(
    () =>
      reduceMotion
        ? { hidden: { opacity: 1, y: 0 }, show: { opacity: 1, y: 0 } }
        : {
            hidden: { opacity: 0, y: 18 },
            show: {
              opacity: 1,
              y: 0,
              transition: { type: 'spring', stiffness: 420, damping: 34 },
            },
          },
    [reduceMotion],
  )

  const showSkeleton = useMemo(
    () => boot || (loadingArtifacts && !tasks?.length),
    [boot, loadingArtifacts, tasks],
  )

  if (showSkeleton) return <DashboardSkeleton />

  return (
    <div className={`page dashboard${reqFocusMode ? ' dashboard--req-focus' : ''}`}>
      <SensitiveHintsBanner projectId={id} hints={sensitiveHints} />
      <motion.div
        className="toolbar"
        variants={fadeUp}
        initial="hidden"
        animate="show"
      >
        <button type="button" className="btn" onClick={() => void genArtifacts()}>
          Generate artifacts
        </button>
        <button type="button" className="btn" onClick={() => void genTests()}>
          Generate tests
        </button>
        <button type="button" className="btn ghost" onClick={() => void runAmbiguity()}>
          Analyze ambiguity
        </button>
        <button type="button" className="btn ghost" onClick={() => void loadArtifacts()}>
          Refresh
        </button>
        <button type="button" className="btn ghost" onClick={() => setReqFocusMode((v) => !v)}>
          {reqFocusMode ? 'Exit focus' : 'Focus requirements'}
        </button>
        <button type="button" className="btn ghost" onClick={() => void copyBundleMarkdown()}>
          Copy bundle (Markdown)
        </button>
        <Link to={`/project/${id}/preview`} className="btn ghost">
          Stakeholder view
        </Link>
      </motion.div>

      {artifactProgress ? (
        <TaskProgressStrip
          label="Artifact generation"
          percent={artifactProgress.percent}
          message={artifactProgress.message}
          status={artifactProgress.status}
        />
      ) : null}
      {testProgress ? (
        <TaskProgressStrip
          label="Test generation"
          percent={testProgress.percent}
          message={testProgress.message}
          status={testProgress.status}
        />
      ) : null}

      <motion.div
        className="summary-row"
        variants={{ hidden: {}, show: { transition: stagger } }}
        initial="hidden"
        animate="show"
      >
        <motion.div variants={fadeUp} className="summary-row-card">
          <SummaryCard
            summary={summary}
            stories={stories}
            projectId={id}
            onStoryExportToggle={patchStoryExport}
          />
        </motion.div>
        <motion.div variants={fadeUp} className="summary-row-card">
          <ReadinessPanel
            summary={summary}
            stories={stories}
            tasks={tasks}
            testcases={testcases}
            ambiguities={ambiguities}
            citationItemRate={citationItemRate}
          />
        </motion.div>
        <motion.div variants={fadeUp} className="summary-row-card">
          <ExportHub projectId={id} stories={stories} tasks={tasks} />
        </motion.div>
      </motion.div>

      <motion.div
        className="dashboard-grid"
        variants={{ hidden: {}, show: { transition: stagger } }}
        initial="hidden"
        animate="show"
      >
        <motion.section
          className="panel kanban-wrap panel--motion"
          variants={fadeUp}
          whileHover={reduceMotion ? undefined : { y: -2 }}
          transition={{ type: 'spring', stiffness: 460, damping: 38 }}
        >
          <h3>Tasks</h3>
          <KanbanBoard
            tasks={tasks}
            onGenerateArtifacts={() => void genArtifacts()}
            projectId={id}
            onTaskExportToggle={patchTaskExport}
          />
        </motion.section>

        <motion.section
          className="panel center-stack panel--motion"
          variants={fadeUp}
          whileHover={reduceMotion ? undefined : { y: -2 }}
          transition={{ type: 'spring', stiffness: 460, damping: 38 }}
        >
          <section ref={requirementSectionRef} className="panel requirement-editor-panel">
            <h4>Working requirement</h4>
            <p className="muted small">Edits are snapshotted to MongoDB (debounced) for version history.</p>
            <textarea
              className="requirement-editor"
              rows={8}
              value={workingReq}
              onChange={(e) => setWorkingReq(e.target.value)}
              placeholder="Requirement text for this session…"
            />
          </section>
          <RequirementSinceGenerateDiff
            beforeText={lastGenReqDiff?.before}
            afterText={lastGenReqDiff?.after}
            onDismiss={() => setLastGenReqDiff(null)}
          />
          <WorkingVsSnapshotDiff projectId={id} workingText={workingReq} refreshKey={snapRefresh} />
          <VersionHistory projectId={id} refreshKey={snapRefresh} />
          <AmbiguityView text={workingReq} hits={ambiguities} />
          <TestCaseList
            testcases={testcases}
            onRefresh={() => void loadTests()}
            onGenerateTests={() => void genTests()}
            loadingTests={loadingTests}
          />
        </motion.section>

        <motion.section
          className="panel chat-wrap panel--motion"
          variants={fadeUp}
          whileHover={reduceMotion ? undefined : { y: -2 }}
          transition={{ type: 'spring', stiffness: 460, damping: 38 }}
        >
          <CopilotPanel projectId={id} />
        </motion.section>
      </motion.div>
    </div>
  )
}
