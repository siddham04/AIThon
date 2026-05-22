import { useCallback, useEffect, useRef } from 'react'

/**
 * Tilt — pointer-driven 3D tilt + glare for any block element.
 *
 * Lightweight, no dependencies. Skipped on coarse pointers (touch) and
 * when prefers-reduced-motion is set.
 *
 * Props:
 *  - max: maximum rotation in degrees on each axis (default 10)
 *  - scale: hover scale (default 1.02)
 *  - glare: render a moving highlight overlay (default true)
 *  - perspective: CSS perspective in px (default 800)
 */
export default function Tilt({
  as: Tag = 'div',
  max = 10,
  scale = 1.02,
  glare = true,
  perspective = 800,
  className = '',
  children,
  style,
  ...rest
}) {
  const ref = useRef(null)
  const glareRef = useRef(null)
  const rafRef = useRef(0)
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

  const handleMove = useCallback(
    (e) => {
      if (!enabledRef.current) return
      const el = ref.current
      if (!el) return
      const rect = el.getBoundingClientRect()
      const px = (e.clientX - rect.left) / rect.width
      const py = (e.clientY - rect.top) / rect.height
      const rx = (0.5 - py) * max * 2
      const ry = (px - 0.5) * max * 2
      cancelAnimationFrame(rafRef.current)
      rafRef.current = requestAnimationFrame(() => {
        el.style.transform = `perspective(${perspective}px) rotateX(${rx.toFixed(
          2,
        )}deg) rotateY(${ry.toFixed(2)}deg) scale(${scale})`
        if (glareRef.current) {
          glareRef.current.style.background = `radial-gradient(circle at ${(
            px * 100
          ).toFixed(1)}% ${(py * 100).toFixed(1)}%, rgba(255,255,255,0.32), transparent 55%)`
          glareRef.current.style.opacity = '1'
        }
      })
    },
    [max, perspective, scale],
  )

  const handleLeave = useCallback(() => {
    const el = ref.current
    if (!el) return
    cancelAnimationFrame(rafRef.current)
    el.style.transform = ''
    if (glareRef.current) glareRef.current.style.opacity = '0'
  }, [])

  return (
    <Tag
      ref={ref}
      className={`fx-tilt ${className}`.trim()}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      style={style}
      {...rest}
    >
      {children}
      {glare && <span ref={glareRef} aria-hidden className="fx-tilt-glare" />}
    </Tag>
  )
}
