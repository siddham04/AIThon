import { useEffect, useRef, useState } from 'react'

/**
 * Counter — animates a number up to its target when scrolled into view.
 *
 * Accepts strings like "95%", "4 hrs → 4 min", "100%", "6+", "1.2K" — it
 * detects the first numeric segment and animates it, leaving prefix/suffix
 * untouched. If no number is found, the raw value is shown verbatim.
 */

const NUM_RX = /([\d]+(?:\.[\d]+)?)/

function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3)
}

export default function Counter({
  value,
  duration = 1400,
  className = '',
  ariaLive = 'polite',
}) {
  const ref = useRef(null)
  const [display, setDisplay] = useState(value)
  const [armed, setArmed] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            setArmed(true)
            obs.disconnect()
          }
        }
      },
      { threshold: 0.4 },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  useEffect(() => {
    if (!armed) return
    const str = String(value)
    const match = str.match(NUM_RX)
    if (!match) {
      setDisplay(str)
      return
    }
    const target = parseFloat(match[1])
    const decimals = match[1].includes('.') ? match[1].split('.')[1].length : 0
    if (Number.isNaN(target)) {
      setDisplay(str)
      return
    }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setDisplay(str)
      return
    }
    let raf = 0
    const start = performance.now()
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration)
      const v = target * easeOutCubic(t)
      const formatted = decimals > 0 ? v.toFixed(decimals) : Math.round(v).toString()
      setDisplay(str.replace(NUM_RX, formatted))
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [armed, value, duration])

  return (
    <span ref={ref} className={`fx-counter ${className}`.trim()} aria-live={ariaLive}>
      {display}
    </span>
  )
}
