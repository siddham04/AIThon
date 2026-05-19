import { lazy, Suspense, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '../api/client'
import { useAuthStore } from '../store/useStore'

function formatApiError(ex) {
  const d = ex.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    return d
      .map((x) => (typeof x === 'string' ? x : x.msg || JSON.stringify(x)))
      .join('; ')
  }
  if (d && typeof d === 'object') return JSON.stringify(d)
  if (ex.message === 'Network Error') return 'Cannot reach API — is the backend running?'
  return 'Registration failed'
}

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
      const { data } = await api.post('/auth/register', { email: id, password })
      setAuth({ email: id }, data.access_token)
      toast.success('Account created')
      nav('/new', { replace: true })
    } catch (ex) {
      const msg = formatApiError(ex)
      setErr(msg)
      toast.error(msg)
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
