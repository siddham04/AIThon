import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { api } from '../../api/client'
import {
  readPinnedProjectIds,
  sortProjectsWithPins,
  togglePinnedProjectId,
} from '../../lib/pinnedProjects'
import { useAuthStore, useProjectStore } from '../../store/useStore'
import { useDarkMode } from '../../hooks/useDarkMode'
import { SkeletonPulse } from '../ui/Skeleton'

const linkCls = ({ isActive }) =>
  `nav-item ${isActive ? 'active' : ''}`.trim()

export default function Sidebar({ projectId }) {
  const [collapsed, setCollapsed] = useState(false)
  const asideRef = useRef(null)
  const nav = useNavigate()
  const logout = useAuthStore((s) => s.logout)
  const user = useAuthStore((s) => s.user)
  const { projects, setProjects, loading, setLoading } = useProjectStore()
  const { dark, toggle } = useDarkMode()
  const [pinnedIds, setPinnedIds] = useState(readPinnedProjectIds)

  const orderedProjects = useMemo(
    () => sortProjectsWithPins(projects, pinnedIds),
    [projects, pinnedIds],
  )

  useGSAP(
    () => {
      const el = asideRef.current
      if (!el) return
      gsap.to(el, {
        width: collapsed ? 72 : 260,
        duration: 0.45,
        ease: 'power2.out',
      })
      const labels = el.querySelectorAll('.nav-label')
      gsap.to(labels, {
        opacity: collapsed ? 0 : 1,
        x: collapsed ? -6 : 0,
        maxWidth: collapsed ? 0 : 200,
        duration: 0.22,
        stagger: collapsed ? 0.02 : 0.04,
        ease: 'power2.out',
        pointerEvents: collapsed ? 'none' : 'auto',
      })
    },
    { dependencies: [collapsed] },
  )

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
    return () => {
      cancelled = true
    }
  }, [setProjects, setLoading])

  return (
    <aside ref={asideRef} className="sidebar">
      <div className="sidebar-top">
        <Link to="/new" className="brand">
          {!collapsed && <span>Helix</span>}
          {collapsed && <span className="brand-mini">H</span>}
        </Link>
        <button
          type="button"
          className="icon-btn"
          title={collapsed ? 'Expand' : 'Collapse'}
          onClick={() => setCollapsed((c) => !c)}
        >
          {collapsed ? '»' : '«'}
        </button>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/new" className={linkCls} title="New project">
          <span className="nav-ico">＋</span>
          <span className="nav-label">New project</span>
        </NavLink>
        {projectId && (
          <>
            <NavLink end to={`/project/${projectId}`} className={linkCls} title="Workspace">
              <span className="nav-ico">▣</span>
              <span className="nav-label">Workspace</span>
            </NavLink>
            <NavLink
              to={`/project/${projectId}/preview`}
              className={linkCls}
              title="Stakeholder preview (read-only)"
            >
              <span className="nav-ico">◇</span>
              <span className="nav-label">Handoff</span>
            </NavLink>
            <NavLink
              to={`/project/${projectId}/analytics`}
              className={linkCls}
              title="Analytics"
            >
              <span className="nav-ico">📊</span>
              <span className="nav-label">Analytics</span>
            </NavLink>
          </>
        )}
      </nav>

      <div className="sidebar-section">
        {!collapsed && <p className="sidebar-heading">Projects</p>}
        {loading ? (
          <div className="sk-stack">
            {Array.from({ length: 5 }).map((_, i) => (
              <SkeletonPulse key={i} className="sk-row" />
            ))}
          </div>
        ) : (
          <ul className="project-list">
            {orderedProjects.map((p) => {
              const pinned = pinnedIds.includes(p.id)
              return (
                <li key={p.id} className="project-list-item">
                  <Link
                    to={`/project/${p.id}`}
                    className={p.id === projectId ? 'project-link active' : 'project-link'}
                    title={p.name}
                  >
                    {!collapsed ? (
                      <>
                        {pinned ? <span className="project-pin-mark">★ </span> : null}
                        {p.name}
                      </>
                    ) : (
                      p.name.slice(0, 2)
                    )}
                  </Link>
                  {!collapsed && (
                    <button
                      type="button"
                      className={`project-pin-btn ${pinned ? 'is-pinned' : ''}`}
                      title={pinned ? 'Unpin project' : 'Pin to top'}
                      aria-pressed={pinned}
                      onClick={(e) => {
                        e.preventDefault()
                        togglePinnedProjectId(p.id)
                        setPinnedIds(readPinnedProjectIds())
                      }}
                    >
                      {pinned ? '★' : '☆'}
                    </button>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <div className="sidebar-footer">
        <button
          type="button"
          className="btn ghost small"
          onClick={toggle}
          title={dark ? 'Switch to light theme' : 'Switch to dark theme'}
          aria-pressed={dark}
        >
          {dark ? 'Light mode' : 'Dark mode'}
        </button>
        <div className="user-line">
          {!collapsed && <span className="muted small">{user?.email}</span>}
          <button
            type="button"
            className="btn ghost small"
            onClick={() => {
              logout()
              nav('/login')
            }}
          >
            Log out
          </button>
        </div>
      </div>
    </aside>
  )
}
