import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import ProtectedRoute from './components/auth/ProtectedRoute'
import {
  LEGACY_GLOBAL_REDIRECTS,
  LEGACY_PROJECT_REDIRECTS,
} from './lib/productFlow'

const Landing = lazy(() => import('./pages/Landing'))
const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))
const AppShell = lazy(() => import('./components/layout/AppShell'))
const ScrollProgress = lazy(() => import('./components/fx/ScrollProgress'))
const GlobalRipple = lazy(() => import('./components/fx/GlobalRipple'))

const MissionControl = lazy(() => import('./pages/MissionControl'))
const AiWorkspace = lazy(() => import('./pages/AiWorkspace'))
const DeliveryCommandCenter = lazy(() => import('./pages/DeliveryCommandCenter'))
const CopilotChat = lazy(() => import('./pages/CopilotChat'))
const Settings = lazy(() => import('./pages/Settings'))
const WinningDemoScreen = lazy(() => import('./pages/WinningDemoScreen'))

function RouteFallback() {
  return (
    <div className="p5-page p5-empty" style={{ minHeight: '40vh' }}>
      <p className="muted">Loading…</p>
    </div>
  )
}

function legacyProjectRedirects() {
  return Object.entries(LEGACY_PROJECT_REDIRECTS).map(([segment, target]) => (
    <Route
      key={`legacy-p-${segment}`}
      path={`/project/:id/${segment}`}
      element={<Navigate to={`../${target}`} replace />}
    />
  ))
}

function legacyGlobalRedirects() {
  return Object.entries(LEGACY_GLOBAL_REDIRECTS).map(([segment, target]) => (
    <Route
      key={`legacy-g-${segment}`}
      path={`/${segment}`}
      element={<Navigate to={target} replace />}
    />
  ))
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={null}>
        <ScrollProgress />
        <GlobalRipple />
      </Suspense>
      <Toaster
        position="top-center"
        toastOptions={{
          duration: 3500,
          style: {
            borderRadius: '12px',
            boxShadow: '0 14px 36px rgba(0, 0, 0, 0.35)',
            background: 'rgba(12, 12, 18, 0.92)',
            color: '#f4f4f5',
          },
        }}
      />
      <Routes>
        <Route
          path="/"
          element={
            <Suspense fallback={<RouteFallback />}>
              <Landing />
            </Suspense>
          }
        />
        <Route
          path="/login"
          element={
            <Suspense fallback={<RouteFallback />}>
              <Login />
            </Suspense>
          }
        />
        <Route
          path="/register"
          element={
            <Suspense fallback={<RouteFallback />}>
              <Register />
            </Suspense>
          }
        />
        <Route element={<ProtectedRoute />}>
          <Route
            element={
              <Suspense fallback={<RouteFallback />}>
                <AppShell />
              </Suspense>
            }
          >
            <Route
              path="/mission-control"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <MissionControl />
                </Suspense>
              }
            />
            <Route
              path="/judge-demo"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <WinningDemoScreen />
                </Suspense>
              }
            />
            <Route
              path="/ai-workspace"
              element={
                <Navigate to="/project/proj_demo_seed01/ai-workspace" replace />
              }
            />
            <Route
              path="/delivery-package"
              element={<Navigate to="/project/proj_demo_seed01/ai-workspace" replace />}
            />
            <Route
              path="/delivery-command"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <DeliveryCommandCenter />
                </Suspense>
              }
            />
            <Route
              path="/copilot"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <CopilotChat />
                </Suspense>
              }
            />
            <Route
              path="/settings"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <Settings />
                </Suspense>
              }
            />

            <Route path="/project/:id" element={<Navigate to="mission-control" replace />} />
            <Route
              path="/project/:id/mission-control"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <MissionControl />
                </Suspense>
              }
            />
            <Route
              path="/project/:id/ai-workspace"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <AiWorkspace />
                </Suspense>
              }
            />
            <Route
              path="/project/:id/delivery-command"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <DeliveryCommandCenter />
                </Suspense>
              }
            />
            <Route
              path="/project/:id/copilot"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <CopilotChat />
                </Suspense>
              }
            />

            <Route path="/workspace" element={<Navigate to="/copilot" replace />} />
            <Route path="/project/:id/workspace" element={<Navigate to="../copilot" replace />} />
            <Route
              path="/project/:id/delivery-package"
              element={<Navigate to="../ai-workspace" replace />}
            />
            <Route
              path="/project/:id/judge-demo"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <WinningDemoScreen />
                </Suspense>
              }
            />

            {legacyProjectRedirects()}
            {legacyGlobalRedirects()}
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
