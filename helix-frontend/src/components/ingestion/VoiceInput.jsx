import { useCallback, useEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import toast from 'react-hot-toast'

function pickSR() {
  return window.SpeechRecognition || window.webkitSpeechRecognition
}

export default function VoiceInput({ value, onChange, disabled }) {
  const [recording, setRecording] = useState(false)
  const [supported] = useState(
    () => typeof window !== 'undefined' && !!(window.SpeechRecognition || window.webkitSpeechRecognition),
  )
  const recRef = useRef(null)
  const baseRef = useRef('')
  const finalsRef = useRef('')
  const stopRequestedRef = useRef(false)
  const waveRef = useRef(null)
  const startRef = useRef(() => {})

  useEffect(() => {
    if (!recording) return
    const root = waveRef.current
    if (!root) return
    const bars = root.querySelectorAll('.voice-wave-bar')
    if (!bars.length) return
    const ctx = gsap.context(() => {
      bars.forEach((bar, i) => {
        gsap.fromTo(
          bar,
          { scaleY: 0.35 },
          {
            scaleY: 1.15,
            duration: 0.42 + i * 0.02,
            repeat: -1,
            yoyo: true,
            ease: 'sine.inOut',
            delay: i * 0.07,
          },
        )
      })
    }, root)
    return () => ctx.revert()
  }, [recording])

  const stop = useCallback(() => {
    stopRequestedRef.current = true
    try {
      recRef.current?.stop?.()
    } catch {
      /* noop */
    }
    recRef.current = null
    setRecording(false)
  }, [])

  const start = useCallback(() => {
    const SR = pickSR()
    if (!SR || disabled) return
    stopRequestedRef.current = false
    baseRef.current = value || ''
    finalsRef.current = ''
    const rec = new SR()
    rec.continuous = true
    rec.interimResults = true
    rec.lang = 'en-US'
    rec.onresult = (e) => {
      let interim = ''
      for (let i = e.resultIndex; i < e.results.length; i += 1) {
        const piece = e.results[i][0].transcript
        if (e.results[i].isFinal) finalsRef.current += piece + ' '
        else interim += piece
      }
      const merged = [baseRef.current, finalsRef.current.trim(), interim]
        .filter(Boolean)
        .join(' ')
        .replace(/\s+/g, ' ')
      onChange(merged)
    }
    rec.onerror = (ev) => {
      const code = ev?.error || 'unknown'
      const hints = {
        'not-allowed': 'Microphone blocked — allow mic for this site in the browser lock icon.',
        network: 'Speech service unreachable — check network / try again (Chrome uses Google speech).',
        'no-speech': 'No speech detected — speak closer to the mic or check input device.',
        aborted: 'Recognition stopped.',
        'audio-capture': 'No microphone found — plug in or enable a mic.',
        'service-not-allowed': 'Speech recognition disabled — try Chrome or HTTPS.',
      }
      if (!['no-speech', 'aborted'].includes(code)) {
        toast.error(hints[code] || `Voice error: ${code}`)
      }
      stop()
    }
    rec.onend = () => {
      const didStop = stopRequestedRef.current
      recRef.current = null
      if (didStop) {
        stopRequestedRef.current = false
        setRecording(false)
        return
      }
      // Some browsers stop recognition after silence; restart automatically
      setTimeout(() => {
        if (!stopRequestedRef.current) startRef.current()
      }, 150)
    }
    rec.start()
    recRef.current = rec
    setRecording(true)
  }, [disabled, onChange, stop, value])

  useEffect(() => {
    startRef.current = start
  }, [start])

  useEffect(() => () => stop(), [stop])

  if (!supported) {
    return (
      <p className="muted small voice-input-hint">
        Voice input needs a Chromium-based browser (Web Speech API).
      </p>
    )
  }

  return (
    <div className="voice-input">
      <div className="voice-input-row">
        <button
          type="button"
          className={`btn voice-mic ${recording ? 'recording' : ''}`}
          disabled={disabled}
          onClick={() => (recording ? stop() : start())}
          aria-pressed={recording}
        >
          {recording ? 'Stop' : 'Voice'}
        </button>
        {recording && (
          <div ref={waveRef} className="voice-wave" aria-hidden>
            {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
              <span key={i} className="voice-wave-bar" />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
