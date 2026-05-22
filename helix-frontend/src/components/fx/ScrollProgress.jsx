import { useEffect, useRef } from 'react'

/**
 * ScrollProgress — slim gradient bar pinned to the top of the viewport that
 * tracks page scroll position. Pure CSS variable, ~zero JS cost per frame.
 */
export default function ScrollProgress() {
  const ref = useRef(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    let raf = 0
    const update = () => {
      const doc = document.documentElement
      const max = (doc.scrollHeight || 1) - (doc.clientHeight || 0)
      const pct = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0
      el.style.transform = `scaleX(${pct.toFixed(4)})`
    }
    const onScroll = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(update)
    }
    update()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      cancelAnimationFrame(raf)
    }
  }, [])

  return <div ref={ref} className="fx-scroll-progress" aria-hidden />
}
