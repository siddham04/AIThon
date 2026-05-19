import { lazy, Suspense, useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { api } from '../api/client'
import { useAuthStore } from '../store/useStore'

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
    setLoading(true)
    try {
      const { data } = await api.post('/auth/login', { email, password })
      setAuth({ email }, data.access_token)
      nav(from, { replace: true })
    } catch {
      setErr('Invalid credentials')
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
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
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
