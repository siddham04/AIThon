import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '../api/client'
import { useAuthStore } from '../store/useStore'
import { formatApiError } from '../lib/formatApiError'
import {
  IconArrowRight,
  IconCheck,
  IconLogo,
  IconLayers,
  IconBeaker,
  IconGraph,
} from '../components/landing/LandingIcons'

export default function Register() {
  const nav = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const [guestLoading, setGuestLoading] = useState(false)

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
      nav('/mission-control', { replace: true })
    } catch (regEx) {
      // Same password on an existing handle already returns a token from /register.
      // If the handle exists with a *different* password, try /login once so judges
      // who click "Create" instead of "Sign in" still get a clear outcome.
      if (regEx.response?.status === 400) {
        try {
          const { data } = await api.post('/auth/login', { email: id, password })
          setAuth({ email: id }, data.access_token)
          toast.success('Signed in — that handle was already registered.')
          nav('/mission-control', { replace: true })
          return
        } catch (loginEx) {
          const msg =
            loginEx.response?.status === 401
              ? 'That handle is taken with a different password. Pick another handle or use Continue as guest / demo.'
              : formatApiError(loginEx)
          setErr(msg)
          toast.error(msg)
          return
        }
      }
      const msg = formatApiError(regEx)
      setErr(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  async function onGuest() {
    if (guestLoading) return
    setGuestLoading(true)
    setErr('')
    try {
      const { data } = await api.post('/auth/guest')
      setAuth({ email: 'Guest', guest: true }, data.access_token)
      toast.success('Welcome — workspace is ready.')
      nav('/mission-control', { replace: true })
    } catch {
      try {
        const { data } = await api.post('/auth/login', {
          email: 'demo@demo.com',
          password: 'demo123',
        })
        setAuth({ email: 'demo@demo.com' }, data.access_token)
        toast.success('Signed in as the demo account.')
        nav('/mission-control', { replace: true })
      } catch (ex) {
        setErr(formatApiError(ex))
      }
    } finally {
      setGuestLoading(false)
    }
  }

  return (
    <div className="lp-auth-shell">
      <aside className="lp-auth-aside">
        <div className="lp-auth-aside-inner">
          <Link to="/" className="lp-auth-aside-brand">
            <IconLogo />
            <span>Helix</span>
          </Link>
          <h2>Create your workspace in 5 seconds.</h2>
          <p>
            Sign up to keep your projects between sessions. Need to look around first?
            Skip straight to a guest workspace.
          </p>
          <ul className="lp-auth-aside-points">
            <li>
              <IconLayers /> Stories, tasks, and acceptance criteria — auto-generated
            </li>
            <li>
              <IconBeaker /> Test scenarios per story (positive / negative / edge)
            </li>
            <li>
              <IconGraph /> Full traceability graph from clause to test case
            </li>
          </ul>
        </div>
        <p className="lp-auth-aside-footer">
          No credit card. No email verification. No corporate dance.
        </p>
      </aside>

      <main className="lp-auth-pane">
        <div className="lp-auth-card">
          <Link to="/" className="lp-auth-back">
            ← Back to home
          </Link>
          <h1 className="lp-auth-title">Create your account</h1>
          <p className="lp-auth-sub">
            Pick any handle and password — no verification email. If the handle already
            exists, we try to sign you in with the same password so you never hit a dead end.
          </p>

          <form className="lp-auth-form" onSubmit={onSubmit}>
            <div className="lp-auth-field">
              <label htmlFor="lp-reg-email">Email or username</label>
              <input
                id="lp-reg-email"
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                minLength={1}
                maxLength={255}
                autoComplete="username"
                placeholder="you@team.com"
              />
            </div>
            <div className="lp-auth-field">
              <label htmlFor="lp-reg-password">Password</label>
              <input
                id="lp-reg-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={1}
                maxLength={128}
                autoComplete="new-password"
                placeholder="At least 1 character — yes, really"
              />
            </div>
            {err && <p className="lp-auth-err">{err}</p>}
            <button
              type="submit"
              className="lp-btn lp-btn-primary lp-btn-lg lp-auth-submit"
              disabled={loading}
            >
              {loading ? 'Creating…' : 'Create account'}
              {!loading && <IconArrowRight />}
            </button>
          </form>

          <div className="lp-auth-divider">or</div>
          <div className="lp-auth-alt-btns">
            <button
              type="button"
              className="lp-btn lp-btn-outline lp-btn-lg"
              onClick={onGuest}
              disabled={guestLoading}
            >
              <IconCheck />
              {guestLoading ? 'Spinning up guest…' : 'Skip — try as a guest'}
            </button>
          </div>

          <p className="lp-auth-switch">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
          <p className="lp-auth-hint">
            Or use <code>demo@demo.com</code> / <code>demo123</code> — seeded on API startup when defaults apply.
          </p>
        </div>
      </main>
    </div>
  )
}
