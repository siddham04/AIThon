import { lazy, Suspense, useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { api } from '../api/client'
import { useAuthStore } from '../store/useStore'

function formatLoginError(ex) {
  const ct = ex.response?.headers?.['content-type'] || ex.response?.headers?.['Content-Type']
  if (typeof ct === 'string' && ct.includes('text/html')) {
    return 'Received HTML instead of API JSON — on Vercel set HELIX_BACKEND_ORIGIN or VITE_API_BASE (see docs/VERCEL.md).'
  }
  if (ex.response?.status === 401) return 'Invalid credentials'
  const d = ex.response?.data?.detail
  if (typeof d === 'string') return d
  if (ex.message === 'Network Error') return 'Cannot reach API — is the backend running?'
  return 'Sign in failed'
}

const WorkspaceAmbient = lazy(() => import('../components/layout/WorkspaceAmbient'))

export default function Login() {
  const nav = useNavigate()
  const loc = useLocation()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  const from = loc.state?.from || '/new'

  async function onSubmit(e) {
    e.preventDefault()
    setErr('')
    const id = email.trim()
    if (!id) {
      setErr('Enter a username or email.')
      return
    }
    if (!password) {
      setErr('Enter a password.')
      return
    }
    setLoading(true)
    try {
      const { data } = await api.post('/auth/login', { email: id, password })
      setAuth({ email: id }, data.access_token)
      nav(from, { replace: true })
    } catch (ex) {
      const msg = formatLoginError(ex)
      setErr(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-page-ambient">
        <Suspense fallback={<div className="workspace-ambient" aria-hidden />}>
          <WorkspaceAmbient />
        </Suspense>
      </div>
      <div className="auth-page-inner">
        <div className="auth-card">
          <h1>Sign in</h1>
          <form onSubmit={onSubmit}>
            <label>
              Email or username
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                minLength={1}
                maxLength={255}
                autoComplete="username"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={1}
                maxLength={128}
                autoComplete="current-password"
              />
            </label>
            {err && <p className="auth-err">{err}</p>}
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
          <p className="auth-switch">
            No account? <Link to="/register">Register</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
