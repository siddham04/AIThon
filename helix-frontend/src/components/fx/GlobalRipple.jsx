import { useEffect } from 'react'

/**
 * GlobalRipple — listens at the document level and paints a Material-style
 * click ripple on any clickable element matching `.btn`, `.lp-btn`,
 * `.icon-btn`, or `[data-fx-ripple]`. Buttons opt-out with
 * `data-fx-ripple="off"`.
 *
 * Render once near the root of the app. Honors prefers-reduced-motion.
 */
const SELECTOR = '.btn, .lp-btn, .icon-btn, [data-fx-ripple]'

export default function GlobalRipple() {
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const onPointerDown = (e) => {
      if (e.button !== undefined && e.button !== 0) return
      const el = e.target.closest?.(SELECTOR)
      if (!el) return
      if (el.dataset?.fxRipple === 'off') return
      if (el.disabled) return

      const rect = el.getBoundingClientRect()
      // The ripple host needs to be positioned and clip its overflow.
      const computed = getComputedStyle(el)
      if (computed.position === 'static') el.style.position = 'relative'
      if (computed.overflow === 'visible') el.style.overflow = 'hidden'

      const size = Math.max(rect.width, rect.height) * 1.6
      const ink = document.createElement('span')
      ink.className = 'fx-ripple-ink'
      ink.style.width = `${size}px`
      ink.style.height = `${size}px`
      ink.style.left = `${e.clientX - rect.left - size / 2}px`
      ink.style.top = `${e.clientY - rect.top - size / 2}px`
      el.appendChild(ink)
      const cleanup = () => ink.remove()
      ink.addEventListener('animationend', cleanup, { once: true })
      window.setTimeout(cleanup, 900)
    }

    document.addEventListener('pointerdown', onPointerDown, { passive: true })
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [])

  return null
}
