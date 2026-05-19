import { useEffect, useState } from 'react'

function isMod(e) {
  return e.metaKey || e.ctrlKey
}

export function useKeyboardShortcuts({ onSubmit, enabled = true } = {}) {
  const [helpOpen, setHelpOpen] = useState(false)

  useEffect(() => {
    if (!enabled) return

    const onKey = (e) => {
      if (e.key === '?' && !isMod(e) && !e.altKey) {
        const tag = document.activeElement?.tagName
        if (tag === 'INPUT' || tag === 'TEXTAREA') return
        e.preventDefault()
        setHelpOpen((o) => !o)
        return
      }
      if (e.key === 'k' && isMod(e)) {
        e.preventDefault()
        window.dispatchEvent(new CustomEvent('helix:open-chat'))
        return
      }
      if (e.key === 'e' && isMod(e)) {
        e.preventDefault()
        window.dispatchEvent(new CustomEvent('helix:open-export'))
        return
      }
      if (e.key === 'Enter' && isMod(e) && onSubmit) {
        const tag = document.activeElement?.tagName
        if (tag === 'TEXTAREA' || tag === 'INPUT') {
          e.preventDefault()
          onSubmit()
        }
      }
    }

    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [enabled, onSubmit])

  return { helpOpen, setHelpOpen }
}
