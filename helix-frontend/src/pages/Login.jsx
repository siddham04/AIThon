import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '../api/client'
import { useAuthStore } from '../store/useStore'
import { formatApiError } from '../lib/formatApiError'
import {
  IconArrowRight,
  IconCheck,
  IconLogo,
  IconSparkles,
  IconBolt,
  IconShieldCheck,
} from '../components/landing/LandingIcons'

function formatLoginError(ex) {
  if (ex.response?.status === 401) {
    return 'That handle is already taken with a different password. Try another handle, Continue as guest, or the demo account.'
  }
  return formatApiError(ex)
}

export default function Login() {
  const nav = useNavigate()
  const loc = useLocation()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const [guestLoading, setGuestLoading] = useState(false)

  const from = loc.state?.from || '/mission-control'

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
      toast.success('Signed in.')
      nav(from, { replace: true })
    } catch (ex) {
      const msg = formatLoginError(ex)
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
        setErr(formatLoginError(ex))
      }
    } finally {
      setGuestLoading(false)
    }
  }

  function onUseDemoCreds() {
    setEmail('demo@demo.com')
    setPassword('demo123')
  }

  return (
    <div className="lp-auth-shell">
      <aside className="lp-auth-aside">
        <div className="lp-auth-aside-inner">
          <Link to="/" className="lp-auth-aside-brand">
            <IconLogo />
            <span>Helix</span>
          </Link>
          <h2>Welcome back to your AI SDLC copilot.</h2>
          <p>
            Sign in to pick up where you left off — or use any handle and password and
            Helix will spin up a fresh account for you instantly.
          </p>
          <ul className="lp-auth-aside-points">
            <li>
              <IconSparkles /> Multi-agent pipeline: intent · ambiguity · backlog · tests
            </li>
            <li>
              <IconBolt /> Streams artifacts live over SSE — never wait for a wall of text
            </li>
            <li>
              <IconShieldCheck /> Citation audit on every export, approved-only gate
            </li>
          </ul>
        </div>
        <p className="lp-auth-aside-footer">
          Built for AI-Thon — judges welcome. Any login works.
        </p>
      </aside>

      <main className="lp-auth-pane">
        <div className="lp-auth-card">
          <Link to="/" className="lp-auth-back">
            ← Back to home
          </Link>
          <h1 className="lp-auth-title">Sign in to Helix</h1>
          <p className="lp-auth-sub">
            Any email and password works — we'll auto-create the account on first use.
          </p>

          <form className="lp-auth-form" onSubmit={onSubmit}>
            <div className="lp-auth-field">
              <label htmlFor="lp-login-email">Email or username</label>
              <input
                id="lp-login-email"
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
              <label htmlFor="lp-login-password">Password</label>
              <input
                id="lp-login-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={1}
                maxLength={128}
                autoComplete="current-password"
                placeholder="••••••••"
              />
            </div>
            {err && <p className="lp-auth-err">{err}</p>}
            <button
              type="submit"
              className="lp-btn lp-btn-primary lp-btn-lg lp-auth-submit"
              disabled={loading}
            >
              {loading ? 'Signing in…' : 'Sign in'}
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
              {guestLoading ? 'Spinning up guest…' : 'Continue as guest (no signup)'}
            </button>
            <button
              type="button"
              className="lp-btn lp-btn-ghost"
              onClick={onUseDemoCreds}
            >
              Use the seeded demo account
            </button>
          </div>

          <p className="lp-auth-switch">
            New here? <Link to="/register">Create an account</Link>
          </p>
          <p className="lp-auth-hint">
            Tip: try <code>demo@demo.com</code> / <code>demo123</code> — or invent any
            credentials.
          </p>
        </div>
      </main>
    </div>
  )
}
