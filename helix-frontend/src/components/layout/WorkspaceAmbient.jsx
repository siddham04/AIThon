import { lazy, Suspense } from 'react'
import { useLocation } from 'react-router-dom'
import { isWorkspaceAmbientEnabled } from '../../lib/helixVisualSettings'

/**
 * Three.js ambient net — on by default (see helixVisualSettings).
 * Lazy-loaded so the main bundle stays smaller until the shell mounts.
 */
const WorkspaceAmbientCanvas = lazy(() => import('./WorkspaceAmbientCanvas'))

export default function WorkspaceAmbient() {
  const { pathname } = useLocation()
  if (!isWorkspaceAmbientEnabled(pathname)) return null

  return (
    <div className="workspace-ambient" aria-hidden>
      <Suspense fallback={null}>
        <WorkspaceAmbientCanvas />
      </Suspense>
    </div>
  )
}
