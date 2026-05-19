import { useCallback, useEffect, useRef, useState } from 'react'
import gsap from 'gsap'

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
  const waveRef = useRef(null)

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
    rec.onerror = () => stop()
    rec.onend = () => setRecording(false)
    rec.start()
    recRef.current = rec
    setRecording(true)
  }, [disabled, onChange, stop, value])

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
