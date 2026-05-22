import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import { useAuthStore } from '../../store/useStore'
import { PRIMARY_NAV, navPath } from '../../lib/productFlow'
import { PRODUCT_AI_AGENTS } from '../../lib/sdlcAgents'

export default function Sidebar({ projectId }) {
  const [collapsed, setCollapsed] = useState(true)
  const navigate = useNavigate()
  const logout = useAuthStore((s) => s.logout)
  const user = useAuthStore((s) => s.user)
  const reduceMotion = useReducedMotion()

  return (
    <aside
      className={`sidebar sidebar--minimal${collapsed ? ' sidebar--collapsed' : ' sidebar--expanded'}`}
    >
      <div className="sidebar-top">
        <Link to="/judge-demo" className="brand" title="Helix — Start Judge Demo">
          {!collapsed && <span>Helix</span>}
          {collapsed && <span className="brand-mini">H</span>}
        </Link>
        <button
          type="button"
          className="icon-btn sidebar-toggle"
          title={collapsed ? 'Expand' : 'Collapse'}
          onClick={() => setCollapsed((c) => !c)}
          aria-expanded={!collapsed}
        >
          {collapsed ? '»' : '«'}
        </button>
      </div>

      {!collapsed && (
        <p className="sidebar-principle muted small">Judge Demo first · then package</p>
      )}

      <nav className="sidebar-nav sidebar-nav--native" aria-label="Product navigation">
        {PRIMARY_NAV.map((item, index) => {
          const disabled = item.requiresProject && !projectId
          const to = navPath(projectId, item.segment, item.global)
          const judgeClass = item.judge ? ' nav-item--judge' : ''
          const copilotClass = item.highlight ? ' nav-item--copilot' : ''

          if (disabled) {
            return (
              <span
                key={item.segment}
                className={`nav-item nav-item--native nav-item--disabled${judgeClass}`}
                title={`${item.label} — launch a project first`}
              >
                <span className="nav-ico">{item.icon}</span>
                <span className="nav-label-wrap">
                  <span className="nav-label">{item.label}</span>
                  {!collapsed && <span className="nav-tagline">{item.tagline}</span>}
                </span>
              </span>
            )
          }

          const navTitle =
            item.judge && collapsed
              ? 'Judge Demo — 5-min autonomous SDLC (recommended for judges)'
              : `${item.label} — ${item.tagline}`

          return (
            <NavLink
              key={item.segment}
              to={to}
              end={item.segment === '/mission-control' && !projectId}
              className={({ isActive }) =>
                `nav-item nav-item--native${judgeClass}${copilotClass}${isActive ? ' active' : ''}`.trim()
              }
              title={navTitle}
            >
              {({ isActive }) => (
                <motion.span
                  className="nav-item-inner"
                  initial={false}
                  animate={reduceMotion ? {} : isActive ? { scale: 1.02 } : { scale: 1 }}
                  whileHover={reduceMotion ? {} : { scale: 1.03 }}
                  whileTap={reduceMotion ? {} : { scale: 0.98 }}
                  transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
                >
                  <span className={`nav-ico${item.judge ? ' nav-ico--judge' : ''}`}>{item.icon}</span>
                  {collapsed && item.judge && (
                    <span className="nav-collapsed-badge" aria-hidden>
                      Demo
                    </span>
                  )}
                  <span className="nav-label-wrap">
                    <span className="nav-label-row">
                      {!collapsed && (
                        <span className="nav-step muted" aria-hidden>
                          {index + 1}
                        </span>
                      )}
                      <span className="nav-label">{item.label}</span>
                    </span>
                    {!collapsed && item.tagline && (
                      <span className="nav-tagline">{item.tagline}</span>
                    )}
                  </span>
                  {isActive && !reduceMotion && (
                    <motion.span
                      className="nav-active-glow"
                      layoutId="nav-glow"
                      transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                    />
                  )}
                </motion.span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {!collapsed && (
        <div className="sidebar-agents" aria-label="AI agents">
          <p className="sidebar-agents-title muted small">AI team</p>
          <ul className="sidebar-agents-list">
            {PRODUCT_AI_AGENTS.map((a) => (
              <li key={a.id} title={a.label}>
                <span className="sidebar-agent-glyph" aria-hidden>
                  {a.glyph}
                </span>
                <span className="sidebar-agent-name">{a.short || a.label}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="sidebar-footer sidebar-footer--minimal">
        <div className="user-line">
          {!collapsed && <span className="muted small sidebar-email">{user?.email}</span>}
          <button
            type="button"
            className="btn ghost small"
            onClick={() => {
              logout()
              navigate('/login')
            }}
          >
            {collapsed ? '↪' : 'Log out'}
          </button>
        </div>
      </div>
    </aside>
  )
}
