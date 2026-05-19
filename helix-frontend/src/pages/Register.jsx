import { lazy, Suspense, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuthStore } from '../store/useStore'

const WorkspaceAmbient = lazy(() => import('../components/layout/WorkspaceAmbient'))

export default function Register() {
  const nav = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setErr('')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/register', { email, password })
      setAuth({ email }, data.access_token)
      nav('/new', { replace: true })
    } catch (ex) {
      const d = ex.response?.data?.detail
      const msg = Array.isArray(d)
        ? d.map((x) => x.msg || JSON.stringify(x)).join(', ')
        : d || 'Registration failed'
      setErr(String(msg))
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
          <h1>Create account</h1>
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
              Password (min 6)
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                autoComplete="new-password"
              />
            </label>
            {err && <p className="auth-err">{err}</p>}
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Creating…' : 'Register'}
            </button>
          </form>
          <p className="auth-switch">
            Have an account? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
