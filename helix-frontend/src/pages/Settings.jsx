import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuthStore, useProjectStore } from '../store/useStore'
import { useDarkMode } from '../hooks/useDarkMode'
import {
  DEFAULT_HUMAN_SETTINGS,
  loadHumanSettings,
  saveHumanSettings,
} from '../lib/helixSettings'
import { PRIORITY_MODES, TECH_PRESETS } from '../lib/missionConfig'

export default function Settings() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const navigate = useNavigate()
  const { projects, setProjects, loading, setLoading } = useProjectStore()
  const { dark, toggle } = useDarkMode()
  const [apiOk, setApiOk] = useState(null)
  const [form, setForm] = useState(() => loadHumanSettings())

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api
      .get('/projects')
      .then(({ data }) => {
        if (!cancelled) setProjects(data)
      })
      .catch(() => {
        if (!cancelled) setProjects([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    api
      .get('/health')
      .then(() => {
        if (!cancelled) setApiOk(true)
      })
      .catch(() => {
        if (!cancelled) setApiOk(false)
      })
    return () => {
      cancelled = true
    }
  }, [setProjects, setLoading])

  const patch = (key, value) => {
    setForm((f) => {
      const next = { ...f, [key]: value }
      saveHumanSettings(next)
      return next
    })
  }

  const resetHuman = () => {
    setForm({ ...DEFAULT_HUMAN_SETTINGS })
    saveHumanSettings(DEFAULT_HUMAN_SETTINGS)
  }

  return (
    <div className="p5-page st-page">
      <header className="p5-hero">
        <p className="p5-eyebrow">Humans only</p>
        <h1>Settings</h1>
        <p className="muted">
          Team preferences and integration credentials. AI runs everything else in Mission
          Control.
        </p>
      </header>

      <section className="p5-panel">
        <h2>Team (optional)</h2>
        <p className="muted small" style={{ marginBottom: '0.75rem' }}>
          Defaults work for demos — adjust only if you want sprint math tailored to your org.
        </p>
        <div className="p5-grid-2" style={{ marginTop: '0.75rem' }}>
          <label>
            <span className="muted small">Team size (optional)</span>
            <select
              value={form.teamSize}
              onChange={(e) => patch('teamSize', Number(e.target.value))}
            >
              {[2, 4, 6, 8, 10, 12].map((n) => (
                <option key={n} value={n}>
                  {n} engineers
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="muted small">Velocity (pts / sprint)</span>
            <input
              type="number"
              min={1}
              max={200}
              value={form.velocity}
              onChange={(e) => patch('velocity', Number(e.target.value))}
            />
          </label>
          <label>
            <span className="muted small">Sprint length (weeks)</span>
            <select
              value={form.sprintWeeks}
              onChange={(e) => patch('sprintWeeks', Number(e.target.value))}
            >
              {[1, 2, 3, 4].map((w) => (
                <option key={w} value={w}>
                  {w}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="muted small">Priority</span>
            <select
              value={form.priorityMode}
              onChange={(e) => patch('priorityMode', e.target.value)}
            >
              {PRIORITY_MODES.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label style={{ display: 'block', marginTop: '0.75rem' }}>
          <span className="muted small">Tech stack</span>
          <input
            value={form.techStack}
            onChange={(e) => patch('techStack', e.target.value)}
            style={{ width: '100%' }}
          />
        </label>
        <div className="p5-chip-row" style={{ marginTop: '0.5rem' }}>
          {TECH_PRESETS.map((stack) => (
            <button
              key={stack}
              type="button"
              className="p5-chip"
              onClick={() => patch('techStack', stack)}
            >
              {stack}
            </button>
          ))}
        </div>
      </section>

      <section className="p5-panel">
        <h2>Jira</h2>
        <p className="muted small">
          Stored locally for demo. Export uses CSV after Approve &amp; Export — optional API push
          only when you configure it.
        </p>
        <div className="p5-grid-2" style={{ marginTop: '0.5rem' }}>
          <label>
            <span className="muted small">Base URL</span>
            <input
              value={form.jiraBaseUrl}
              onChange={(e) => patch('jiraBaseUrl', e.target.value)}
              placeholder="https://your.atlassian.net"
            />
          </label>
          <label>
            <span className="muted small">Project key</span>
            <input
              value={form.jiraProjectKey}
              onChange={(e) => patch('jiraProjectKey', e.target.value)}
            />
          </label>
          <label>
            <span className="muted small">Email</span>
            <input
              value={form.jiraEmail}
              onChange={(e) => patch('jiraEmail', e.target.value)}
            />
          </label>
          <label>
            <span className="muted small">API token</span>
            <input
              type="password"
              value={form.jiraToken}
              onChange={(e) => patch('jiraToken', e.target.value)}
            />
          </label>
        </div>
      </section>

      <section className="p5-panel">
        <h2>GitHub</h2>
        <div className="p5-grid-2" style={{ marginTop: '0.5rem' }}>
          <label>
            <span className="muted small">Token</span>
            <input
              type="password"
              value={form.githubToken}
              onChange={(e) => patch('githubToken', e.target.value)}
            />
          </label>
          <label>
            <span className="muted small">Repo (owner/name)</span>
            <input
              value={form.githubRepo}
              onChange={(e) => patch('githubRepo', e.target.value)}
            />
          </label>
        </div>
      </section>

      <section className="p5-panel">
        <h2>Azure OpenAI</h2>
        <p className="muted small">Backend uses .env — these are presenter notes / local copy.</p>
        <div className="p5-grid-2" style={{ marginTop: '0.5rem' }}>
          <label>
            <span className="muted small">Endpoint</span>
            <input
              value={form.azureEndpoint}
              onChange={(e) => patch('azureEndpoint', e.target.value)}
            />
          </label>
          <label>
            <span className="muted small">Deployment</span>
            <input
              value={form.azureDeployment}
              onChange={(e) => patch('azureDeployment', e.target.value)}
            />
          </label>
          <label style={{ gridColumn: '1 / -1' }}>
            <span className="muted small">API key</span>
            <input
              type="password"
              value={form.azureKey}
              onChange={(e) => patch('azureKey', e.target.value)}
            />
          </label>
        </div>
      </section>

      <section className="p5-panel">
        <h2>Account & appearance</h2>
        <p className="muted small">{user?.email || 'Signed in'}</p>
        <div className="p5-actions" style={{ marginTop: '0.5rem' }}>
          <button type="button" className="btn ghost" onClick={toggle}>
            {dark ? 'Light mode' : 'Dark mode'}
          </button>
          <button type="button" className="btn ghost" onClick={resetHuman}>
            Reset team defaults
          </button>
          <button
            type="button"
            className="btn ghost"
            onClick={() => {
              logout()
              navigate('/login')
            }}
          >
            Log out
          </button>
        </div>
        <p className="muted small" style={{ marginTop: '0.75rem' }}>
          API {apiOk === null ? '…' : apiOk ? 'connected' : 'down'}
        </p>
      </section>

      <section className="p5-panel">
        <h2>Projects</h2>
        {loading && <p className="muted">Loading…</p>}
        {!loading && projects.length === 0 && (
          <p className="muted">
            No projects — <Link to="/mission-control">Mission Control</Link>
          </p>
        )}
        <ul className="p5-list">
          {projects.map((p) => (
            <li key={p.id}>
              <Link to={`/project/${p.id}/ai-workspace`}>{p.name}</Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
