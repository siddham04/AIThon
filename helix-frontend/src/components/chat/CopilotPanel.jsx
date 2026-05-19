import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'

const COPILOT_CHIPS_KEY = 'helix:copilot-prompt-chips'

const DEFAULT_COPILOT_CHIPS = [
  'List gaps or contradictions in this PRD.',
  'Suggest acceptance criteria for each user story.',
  'What are the top three risks if we ship as written?',
  'Draft test ideas that would catch scope creep.',
  'Summarize this requirement for a non-technical stakeholder.',
  'Which tasks look under-specified and need clarification?',
]

function readStoredChips() {
  try {
    const raw = localStorage.getItem(COPILOT_CHIPS_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return null
    const strings = parsed.filter((x) => typeof x === 'string' && x.trim())
    return strings.length ? strings.slice(0, 8) : null
  } catch {
    return null
  }
}

function ensureChipsInStorage() {
  const existing = readStoredChips()
  if (existing) return existing
  try {
    localStorage.setItem(COPILOT_CHIPS_KEY, JSON.stringify(DEFAULT_COPILOT_CHIPS))
  } catch {
    /* ignore quota */
  }
  return DEFAULT_COPILOT_CHIPS
}

let msgSeq = 0
function nextMsgId(prefix) {
  msgSeq += 1
  return `${prefix}-${msgSeq}`
}

export default function CopilotPanel({ projectId }) {
  const reduceMotion = useReducedMotion()
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [streaming, setStreaming] = useState('')
  const [busy, setBusy] = useState(false)
  const [promptChips] = useState(() => ensureChipsInStorage())
  const bottom = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  useEffect(() => {
    const open = () => inputRef.current?.focus()
    window.addEventListener('helix:open-chat', open)
    return () => window.removeEventListener('helix:open-chat', open)
  }, [])

  const sendMessage = useCallback(
    async (rawText) => {
      const msg = (rawText ?? input).trim()
      if (!msg || !projectId || busy) return
      setInput('')
      setBusy(true)
      setStreaming('')
      const history = messages.flatMap((m) => [{ role: m.role, content: m.text }])
      const userId = nextMsgId('u')
      setMessages((prev) => [...prev, { id: userId, role: 'user', text: msg }])

      const base = import.meta.env.VITE_API_BASE?.replace(/\/$/, '') || '/api'
      const url = `${base.startsWith('http') ? base : window.location.origin + base}/chat/${projectId}`
      const token = localStorage.getItem('helix_token')

      let assistant = ''
      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            message: msg,
            history: history.slice(-16),
          }),
        })
        if (!res.ok || !res.body) throw new Error('Chat failed')
        const reader = res.body.getReader()
        const dec = new TextDecoder()
        let buf = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buf += dec.decode(value, { stream: true })
          const parts = buf.split('\n\n')
          buf = parts.pop() || ''
          for (const block of parts) {
            const lines = block.split('\n')
            for (const line of lines) {
              if (!line.startsWith('data: ')) continue
              const payload = line.slice(6).trim()
              if (!payload || payload === '[DONE]') continue
              try {
                const j = JSON.parse(payload)
                if (j.token) {
                  assistant += j.token
                  setStreaming(assistant)
                }
              } catch {
                /* ignore heartbeats */
              }
            }
          }
        }
        const aid = nextMsgId('a')
        setMessages((prev) => [...prev, { id: aid, role: 'assistant', text: assistant }])
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            id: nextMsgId('e'),
            role: 'assistant',
            text: 'Sorry — could not reach the copilot.',
          },
        ])
      } finally {
        setStreaming('')
        setBusy(false)
      }
    },
    [busy, input, messages, projectId],
  )

  const emptyThread = messages.length === 0 && !streaming && !busy

  const bubbleTransition = reduceMotion
    ? { duration: 0.01 }
    : { type: 'spring', stiffness: 460, damping: 34 }

  return (
    <div className="copilot">
      <h3>Copilot</h3>
      <div className="copilot-thread">
        {emptyThread && (
          <motion.div
            className="copilot-empty-hint muted small"
            initial={reduceMotion ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={bubbleTransition}
          >
            Ask about scope, risks, or tests — or try a quick prompt below.
          </motion.div>
        )}
        <AnimatePresence initial={false}>
          {messages.map((m) => (
            <motion.div
              key={m.id}
              layout={!reduceMotion}
              className={`bubble ${m.role}`}
              initial={reduceMotion ? false : { opacity: 0, y: 12, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={reduceMotion ? { opacity: 1 } : { opacity: 0, scale: 0.96 }}
              transition={bubbleTransition}
            >
              {m.role === 'assistant' ? (
                <ReactMarkdown>{m.text}</ReactMarkdown>
              ) : (
                m.text
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        <AnimatePresence>
          {(streaming || busy) && (
            <motion.div
              key="streaming"
              layout={!reduceMotion}
              className="bubble assistant streaming streaming-bubble"
              initial={reduceMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduceMotion ? { opacity: 1 } : { opacity: 0, y: -4 }}
              transition={bubbleTransition}
            >
              {streaming}
              <span className="cursor-blink" />
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={bottom} />
      </div>
      {emptyThread && promptChips.length > 0 && (
        <motion.div
          className="copilot-chips"
          aria-label="Suggested prompts"
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: reduceMotion ? 0 : 0.12, duration: 0.25 }}
        >
          {promptChips.map((label, i) => (
            <motion.button
              key={label}
              type="button"
              className="copilot-chip"
              disabled={busy}
              onClick={() => void sendMessage(label)}
              initial={reduceMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: reduceMotion ? 0 : 0.08 + i * 0.04,
                type: 'spring',
                stiffness: 400,
                damping: 28,
              }}
              whileHover={reduceMotion ? undefined : { y: -2, borderColor: 'var(--accent)' }}
              whileTap={reduceMotion ? undefined : { scale: 0.97 }}
            >
              {label}
            </motion.button>
          ))}
        </motion.div>
      )}
      <motion.div
        className="copilot-input-row"
        initial={false}
        animate={busy && !reduceMotion ? { opacity: 0.92 } : { opacity: 1 }}
      >
        <textarea
          ref={inputRef}
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about scope, risks, or tests…"
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
              e.preventDefault()
              void sendMessage()
            }
          }}
        />
        <motion.button
          type="button"
          className="btn btn-primary"
          disabled={busy}
          onClick={() => void sendMessage()}
          whileHover={reduceMotion || busy ? undefined : { scale: 1.02 }}
          whileTap={reduceMotion || busy ? undefined : { scale: 0.98 }}
        >
          Send
        </motion.button>
      </motion.div>
    </div>
  )
}
