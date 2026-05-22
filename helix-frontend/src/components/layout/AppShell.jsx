import { lazy, Suspense, useState } from 'react'
import { Outlet, useLocation, useNavigate, useParams } from 'react-router-dom'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import Sidebar from './Sidebar'
import TeamFlowBar from './TeamFlowBar'
import WorkspaceAmbient from './WorkspaceAmbient'
import { isNativeShellPath } from '../../lib/productFlow'
import { hasSeenOnboarding } from '../onboarding/onboardingStorage'

const CommandPalette = lazy(() => import('../command-palette/CommandPalette'))
const OnboardingModal = lazy(() => import('../onboarding/OnboardingModal'))

const SAMPLE_PREFILL_KEY = 'helix_prefill_sample'

function shellModeClass(path) {
  if (path.includes('/judge-demo')) return ' app-main--winning-demo'
  if (path.includes('/mission-control')) return ' app-main--mission'
  if (path.includes('/ai-workspace')) return ' app-main--workspace'
  if (path.includes('/delivery-command')) return ' app-main--delivery-package'
  if (path.includes('/copilot')) return ' app-main--workspace'
  if (path.includes('/settings')) return ' app-main--settings'
  return ''
}

export default function AppShell() {
  const { id } = useParams()
  const location = useLocation()
  const nav = useNavigate()
  const reduceMotion = useReducedMotion()
  const [showOnb, setShowOnb] = useState(() => !hasSeenOnboarding())
  const path = location.pathname

  const showTeamFlow = Boolean(id) && isNativeShellPath(path)

  return (
    <div className="app-shell app-shell--team">
      <WorkspaceAmbient />
      <Sidebar projectId={id} />
      <main className={`app-main app-main--native${shellModeClass(path)}`}>
        <div className="app-main-content">
          {showTeamFlow && <TeamFlowBar />}
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              className="app-outlet-wrap"
              initial={reduceMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduceMotion ? { opacity: 1 } : { opacity: 0, y: -6 }}
              transition={
                reduceMotion
                  ? { duration: 0.01 }
                  : { duration: 0.28, ease: [0.16, 1, 0.3, 1] }
              }
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
      <Suspense fallback={null}>
        <CommandPalette />
      </Suspense>
      {showOnb && (
        <Suspense fallback={null}>
          <OnboardingModal
            onClose={() => setShowOnb(false)}
            onLoadSample={() => {
              try {
                sessionStorage.setItem(SAMPLE_PREFILL_KEY, '1')
              } catch {
                /* noop */
              }
              nav('/mission-control')
            }}
          />
        </Suspense>
      )}
    </div>
  )
}
