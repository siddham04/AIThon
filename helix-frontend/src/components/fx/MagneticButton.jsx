import { Children, cloneElement, useEffect, useRef } from 'react'

/**
 * MagneticButton — wraps a button (or any element) and pulls it toward the
 * pointer when hovered. Adds a soft glow that follows the cursor.
 *
 * Usage: <MagneticButton><button>Click me</button></MagneticButton>
 */
export default function MagneticButton({
  children,
  strength = 0.35,
  radius = 90,
  className = '',
}) {
  const wrapRef = useRef(null)
  const innerRef = useRef(null)
  const enabledRef = useRef(true)

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const coarse = window.matchMedia('(pointer: coarse)')
    const update = () => {
      enabledRef.current = !mq.matches && !coarse.matches
    }
    update()
    mq.addEventListener?.('change', update)
    coarse.addEventListener?.('change', update)
    return () => {
      mq.removeEventListener?.('change', update)
      coarse.removeEventListener?.('change', update)
    }
  }, [])

  useEffect(() => {
    const wrap = wrapRef.current
    const inner = innerRef.current
    if (!wrap || !inner) return

    let raf = 0

    const onMove = (e) => {
      if (!enabledRef.current) return
      const rect = wrap.getBoundingClientRect()
      const cx = rect.left + rect.width / 2
      const cy = rect.top + rect.height / 2
      const dx = e.clientX - cx
      const dy = e.clientY - cy
      const dist = Math.hypot(dx, dy)
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        if (dist < radius) {
          const tx = dx * strength
          const ty = dy * strength
          inner.style.transform = `translate(${tx.toFixed(1)}px, ${ty.toFixed(1)}px)`
          wrap.style.setProperty('--fx-mag-x', `${e.clientX - rect.left}px`)
          wrap.style.setProperty('--fx-mag-y', `${e.clientY - rect.top}px`)
          wrap.classList.add('fx-mag-active')
        } else if (dist < radius + 60) {
          const fade = 1 - (dist - radius) / 60
          inner.style.transform = `translate(${(dx * strength * fade).toFixed(
            1,
          )}px, ${(dy * strength * fade).toFixed(1)}px)`
        } else {
          inner.style.transform = ''
          wrap.classList.remove('fx-mag-active')
        }
      })
    }

    const onLeave = () => {
      cancelAnimationFrame(raf)
      inner.style.transform = ''
      wrap.classList.remove('fx-mag-active')
    }

    window.addEventListener('mousemove', onMove)
    wrap.addEventListener('mouseleave', onLeave)
    return () => {
      window.removeEventListener('mousemove', onMove)
      wrap.removeEventListener('mouseleave', onLeave)
      cancelAnimationFrame(raf)
    }
  }, [radius, strength])

  const child = Children.only(children)
  const inner = cloneElement(child, {
    ref: innerRef,
    className: `${child.props.className || ''} fx-mag-inner`.trim(),
  })

  return (
    <span ref={wrapRef} className={`fx-mag ${className}`.trim()}>
      {inner}
    </span>
  )
}
