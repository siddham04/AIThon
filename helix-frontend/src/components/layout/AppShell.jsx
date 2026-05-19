import { lazy, Suspense, useState } from 'react'
import { Outlet, useLocation, useNavigate, useParams } from 'react-router-dom'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import Sidebar from './Sidebar'

const WorkspaceAmbient = lazy(() => import('./WorkspaceAmbient'))
import CommandPalette from '../command-palette/CommandPalette'
import OnboardingModal from '../onboarding/OnboardingModal'
import { hasSeenOnboarding } from '../onboarding/onboardingStorage'

const SAMPLE_PREFILL_KEY = 'helix_prefill_sample'

export default function AppShell() {
  const { id } = useParams()
  const location = useLocation()
  const nav = useNavigate()
  const reduceMotion = useReducedMotion()
  const [showOnb, setShowOnb] = useState(() => !hasSeenOnboarding())

  return (
    <div className="app-shell">
      <Sidebar projectId={id} />
      <main className="app-main">
        <Suspense fallback={<div className="workspace-ambient" aria-hidden />}>
          <WorkspaceAmbient />
        </Suspense>
        <div className="app-main-content">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              className="app-outlet-wrap"
              initial={reduceMotion ? false : { opacity: 0, y: 14, filter: 'blur(6px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={
                reduceMotion
                  ? { opacity: 1 }
                  : { opacity: 0, y: -10, filter: 'blur(4px)' }
              }
              transition={
                reduceMotion
                  ? { duration: 0.01 }
                  : { duration: 0.32, ease: [0.22, 1, 0.36, 1] }
              }
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
      <CommandPalette />
      {showOnb && (
        <OnboardingModal
          onClose={() => setShowOnb(false)}
          onLoadSample={() => {
            try {
              sessionStorage.setItem(SAMPLE_PREFILL_KEY, '1')
            } catch {
              /* noop */
            }
            nav('/new')
          }}
        />
      )}
    </div>
  )
}
