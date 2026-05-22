import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'helix_theme'

export function useDarkMode() {
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'dark' || saved === 'light') return saved === 'dark'
    return true
  })

  useEffect(() => {
    const root = document.documentElement
    if (dark) {
      root.classList.add('dark')
      root.classList.remove('light-forced')
      localStorage.setItem(STORAGE_KEY, 'dark')
    } else {
      root.classList.remove('dark')
      root.classList.add('light-forced')
      localStorage.setItem(STORAGE_KEY, 'light')
    }
  }, [dark])

  const toggle = useCallback(() => setDark((d) => !d), [])

  return { dark, toggle, setDark }
}
