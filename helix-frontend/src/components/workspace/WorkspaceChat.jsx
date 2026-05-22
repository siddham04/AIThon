import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { useProjectStore } from '../../store/useStore'
import WorkspaceArtifact, { MarkdownAnswer } from './WorkspaceArtifact'
import {
  WORKSPACE_STARTERS,
  askWorkspaceChat,
  classifyWorkspaceIntent,
  runWorkspaceAction,
} from '../../lib/workspaceActions'
import { PRODUCT_AI_AGENTS } from '../../lib/sdlcAgents'
import { api } from '../../api/client'

function CitationChip({ c }) {
  const t = (c.artifact_type || '').toLowerCase()
  return (
    <span className={`ws-cite ws-cite--${t}`} title={c.snippet}>
      {c.label || c.artifact_id}
    </span>
  )
}

export default function WorkspaceChat({
  projectId: projectIdProp,
  examplePrompts,
  variant = 'workspace',
  loadSuggestedFromApi = false,
}) {
  const { id: routeId } = useParams()
  const projectId = projectIdProp ?? routeId
  const navigate = useNavigate()
  const projects = useProjectStore((s) => s.projects)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [apiStarters, setApiStarters] = useState(null)
  const scrollRef = useRef(null)
  const inputRef = useRef(null)

  const projectName = projects.find((x) => x.id === projectId)?.name ?? ''
  const starters = apiStarters ?? examplePrompts ?? WORKSPACE_STARTERS

  useEffect(() => {
    if (!loadSuggestedFromApi || !projectId || variant !== 'copilot') return undefined
    let cancelled = false
    void api
      .get(`/assistant/${projectId}/suggested`)
      .then(({ data }) => {
        if (cancelled || !data?.suggestions?.length) return
        setApiStarters(data.suggestions.slice(0, 6))
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [loadSuggestedFromApi, projectId, variant])

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages.length, loading])

  const send = useCallback(
    async (text) => {
      const q = (text ?? input).trim()
      if (!q || loading) return
      if (!projectId) {
        toast.error('Select a project first')
        return
      }

      setInput('')
      setLoading(true)
      const userMsg = { id: `u-${Date.now()}`, role: 'user', text: q }
      setMessages((prev) => [...prev, userMsg])

      try {
        const intent = classifyWorkspaceIntent(q)

        if (intent.mode === 'action' && intent.action) {
          const working = {
            id: `w-${Date.now()}`,
            role: 'assistant',
            working: true,
            actionLabel: intent.label,
          }
          setMessages((prev) => [...prev, working])

          const result = await runWorkspaceAction(projectId, intent.action, q)
          setMessages((prev) => {
            const without = prev.filter((m) => !m.working)
            return [
              ...without,
              {
                id: `a-${Date.now()}`,
                role: 'assistant',
                answer: result.answer,
                artifact: result.artifact,
                citations: result.citations,
                followups: result.suggested_followups,
                action: intent.action,
              },
            ]
          })
        } else {
          const turn = await askWorkspaceChat(projectId, q)
          setMessages((prev) => [
            ...prev,
            {
              id: `a-${Date.now()}`,
              role: 'assistant',
              answer: turn.answer,
              citations: turn.citations,
              followups: turn.suggested_followups,
            },
          ])
        }
      } catch (e) {
        toast.error(e?.response?.data?.detail || e?.message || 'Request failed')
        setMessages((prev) => [
          ...prev.filter((m) => !m.working),
          {
            id: `e-${Date.now()}`,
            role: 'assistant',
            answer: 'Something went wrong — try again or rephrase your question.',
          },
        ])
      } finally {
        setLoading(false)
        inputRef.current?.focus()
      }
    },
    [input, loading, projectId],
  )

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void send()
    }
  }

  if (!projectId) {
    return (
      <div className="ws-shell ws-shell--pick">
        <div className="ws-pick">
          <h1>{variant === 'copilot' ? 'SDLC Copilot' : 'Workspace'}</h1>
          <p className="muted">
            {variant === 'copilot'
              ? 'Trained on your project artifacts — pick a project to start.'
              : 'Pick a project to chat with your AI team.'}
          </p>
          {projects.length === 0 ? (
            <p>
              <Link to="/mission-control">Mission Control</Link> first.
            </p>
          ) : (
            <ul className="ws-pick-list">
              {projects.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    className="ws-pick-btn"
                    onClick={() => navigate(`/project/${p.id}/copilot`)}
                  >
                    {p.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="ws-shell">
      <header className="ws-topbar">
        <div className="ws-topbar-title">
          <span className="ws-topbar-eyebrow">
            {variant === 'copilot' ? 'SDLC Copilot · trained on project' : 'Talk to your team'}
          </span>
          <h1>{projectName || 'Project'}</h1>
        </div>
        <div className="ws-topbar-actions">
          <button type="button" className="btn ghost small" onClick={() => setMessages([])}>
            New chat
          </button>
          <Link to={`/project/${projectId}/ai-workspace`} className="btn ghost small">
            AI output
          </Link>
        </div>
      </header>

      <div className="ws-thread" ref={scrollRef}>
        <AnimatePresence initial={false}>
          {messages.length === 0 && (
            <motion.div
              className="ws-empty"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="ws-empty-icon" aria-hidden>
                ✦
              </div>
              <h2>{variant === 'copilot' ? 'SDLC Copilot' : 'Ask your AI SDLC team'}</h2>
              <p className="muted">
                {variant === 'copilot'
                  ? 'Grounded on stories, APIs, tests, risks, and sprint data from this project. Ask in plain English — citations included.'
                  : 'Ask for architecture, sprint plans, risks, or tests and the agents produce them inline.'}
              </p>
              {variant === 'copilot' && (
                <div className="ws-agent-row" aria-label="AI agents">
                  {PRODUCT_AI_AGENTS.map((a) => (
                    <span key={a.id} className="ws-agent-chip" title={a.label}>
                      <span aria-hidden>{a.glyph}</span> {a.short || a.label}
                    </span>
                  ))}
                </div>
              )}
              <div className="ws-starters">
                {starters.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className="ws-starter"
                    onClick={() => void send(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {messages.map((m) => (
            <motion.div
              key={m.id}
              className={`ws-msg ws-msg--${m.role}${m.working ? ' ws-msg--working' : ''}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22 }}
            >
              {m.role === 'user' && (
                <div className="ws-bubble ws-bubble--user">
                  <p>{m.text}</p>
                </div>
              )}
              {m.role === 'assistant' && (
                <div className="ws-bubble ws-bubble--ai">
                  {m.working && (
                    <div className="ws-working">
                      <span className="ws-working-dot" />
                      <span>
                        {m.actionLabel ? `${m.actionLabel}…` : 'Thinking…'}
                      </span>
                    </div>
                  )}
                  {!m.working && (
                    <>
                      {m.answer && <MarkdownAnswer text={m.answer} />}
                      {m.artifact && <WorkspaceArtifact artifact={m.artifact} />}
                      {m.citations?.length > 0 && (
                        <div className="ws-cites">
                          {m.citations.slice(0, 6).map((c, i) => (
                            <CitationChip key={i} c={c} />
                          ))}
                        </div>
                      )}
                      {m.followups?.length > 0 && (
                        <div className="ws-followups">
                          {m.followups.slice(0, 4).map((f) => (
                            <button
                              key={f}
                              type="button"
                              className="ws-followup"
                              onClick={() => void send(f)}
                            >
                              {f}
                            </button>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </motion.div>
          ))}

          {loading && !messages.some((m) => m.working) && (
            <motion.div className="ws-msg ws-msg--assistant" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <div className="ws-bubble ws-bubble--ai">
                <div className="ws-thinking">
                  <span /><span /><span />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <footer className="ws-composer">
        <div className="ws-composer-inner">
          <textarea
            ref={inputRef}
            className="ws-input"
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={
              variant === 'copilot'
                ? 'Which requirements are ambiguous? · What APIs need changes?…'
                : 'Generate architecture · Show sprint plan · What are the risks?…'
            }
            disabled={loading}
          />
          <button
            type="button"
            className="ws-send"
            disabled={loading || !input.trim()}
            onClick={() => void send()}
            aria-label="Send"
          >
            ↑
          </button>
        </div>
        <p className="ws-composer-hint muted small">
          {variant === 'copilot'
            ? 'SDLC Copilot uses /api/assistant — grounded answers with citations'
            : 'Enter to send · Shift+Enter for newline · Answers stay in this thread'}
        </p>
      </footer>
    </div>
  )
}
