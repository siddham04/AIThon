import '../lib/gsapInit'
import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { motion, useReducedMotion } from 'framer-motion'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '../api/client'
import { HELIX_AUTO_DEMO_KEY } from '../lib/demoConfig'
import { useAuthStore } from '../store/useStore'
import { useDarkMode } from '../hooks/useDarkMode'
import { isHeroParticlesEnabled } from '../lib/helixVisualSettings'
import {
  IconArrowRight,
  IconCheck,
  IconUsers,
  IconCode,
  IconClipboard,
  IconSun,
  IconMoon,
  IconLogo,
  IconGithub,
} from '../components/landing/LandingIcons'
import Counter from '../components/fx/Counter'
import Tilt from '../components/fx/Tilt'
import MagneticButton from '../components/fx/MagneticButton'
import { HERO_TITLE, POSITIONING_LINE, APPROVE_EXPORT_CTA } from '../lib/productMessaging'
import { formatGuestSessionError } from '../lib/formatApiError'
import { checkApiHealth } from '../lib/apiHealth'

const HeroParticles = lazy(() => import('../components/landing/HeroParticles'))

const STATS = [
  { value: '1', label: 'upload — you give messy requirements' },
  { value: '4', label: 'agents — PM, Architect, QA, Scrum' },
  { value: '100%', label: 'delivery readiness when all gates pass' },
  { value: '0', label: 'dashboard tours — one package, one flow' },
]

const FEATURES = [
  {
    icon: IconUsers,
    title: 'AI Product Manager',
    description:
      'Turns chaos into stories, acceptance criteria, and scope — you approve, not write from scratch.',
  },
  {
    icon: IconCode,
    title: 'AI Architect & QA',
    description:
      'Architecture, test cases, and risk analysis run autonomously while you supervise in Workspace.',
  },
  {
    icon: IconClipboard,
    title: 'AI Scrum Master',
    description:
      'Sprint plan and effort estimates — you Approve & Export when ready; Helix never auto-pushes to Jira.',
  },
]

const WORKFLOW = [
  {
    step: '01',
    title: 'Upload & Launch',
    description: 'Upload your requirement. Launch the AI team — agents do the SDLC work.',
  },
  {
    step: '02',
    title: 'Autonomous pipeline',
    description:
      'PM → architecture → stories → sprint plan → tests → risks — autonomous by default.',
  },
  {
    step: '03',
    title: 'Approve & Export',
    description:
      'Checklist of what the AI produced. One click approves scope and downloads Jira CSV — you control the import.',
  },
]

const USE_CASES = [
  {
    icon: IconClipboard,
    role: 'Product Managers',
    points: [
      'Turn meeting notes into a backlog instantly',
      'Catch ambiguity before sprint planning',
      'Share a polished preview with stakeholders',
    ],
  },
  {
    icon: IconCode,
    role: 'Engineering Leads',
    points: [
      'Pre-sized tasks with effort & dependency hints',
      'Trace any task back to the source clause',
      'Export approved scope straight to JIRA / GitHub',
    ],
  },
  {
    icon: IconUsers,
    role: 'QA & Stakeholders',
    points: [
      'Test scenarios generated alongside each story',
      'Read-only preview link for non-engineers',
      'Full audit footer on every export',
    ],
  },
]

function NavBar({ dark, onToggleTheme, onGuest, guestLoading }) {
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  return (
    <header className={`lp-nav ${scrolled ? 'is-scrolled' : ''}`}>
      <a className="lp-nav-brand" href="#top">
        <IconLogo />
        <span>Helix</span>
        <span className="lp-nav-brand-tag">SDLC Copilot</span>
      </a>
      <nav className="lp-nav-links" aria-label="Primary">
        <a href="#features">Features</a>
        <a href="#workflow">How it works</a>
        <a href="#personas">For teams</a>
        <a href="#impact">Impact</a>
      </nav>
      <div className="lp-nav-cta">
        <button
          type="button"
          className="lp-icon-btn"
          onClick={onToggleTheme}
          aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
          title={dark ? 'Light mode' : 'Dark mode'}
        >
          {dark ? <IconSun /> : <IconMoon />}
        </button>
        <Link to="/login" className="lp-btn lp-btn-ghost">
          Sign in
        </Link>
        <MagneticButton>
          <button
            type="button"
            className="lp-btn lp-btn-primary"
            onClick={onGuest}
            disabled={guestLoading}
          >
            {guestLoading ? 'Spinning up…' : 'Try as Guest'}
            <IconArrowRight />
          </button>
        </MagneticButton>
      </div>
    </header>
  )
}

function Section({ id, eyebrow, title, kicker, children, className = '' }) {
  const reduce = useReducedMotion()
  return (
    <section id={id} className={`lp-section ${className}`}>
      <motion.div
        className="lp-section-head"
        initial={reduce ? false : { opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-80px' }}
        transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
      >
        {eyebrow && <p className="lp-eyebrow">{eyebrow}</p>}
        {title && <h2 className="lp-section-title">{title}</h2>}
        {kicker && <p className="lp-section-kicker">{kicker}</p>}
      </motion.div>
      {children}
    </section>
  )
}

export default function Landing() {
  const root = useRef(null)
  const nav = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const { dark, toggle } = useDarkMode()
  const [guestLoading, setGuestLoading] = useState(false)
  const reduce = useReducedMotion()

  useGSAP(
    () => {
      const ctx = gsap.context(() => {
        const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })
        tl.from('.lp-hero-eyebrow', { opacity: 0, y: 14, duration: 0.4 })
          .from(
            '.lp-hero-title-word',
            { opacity: 0, y: 28, duration: 0.5, stagger: 0.05 },
            '-=0.15',
          )
          .from('.lp-hero-sub', { opacity: 0, y: 12, duration: 0.55 }, '-=0.25')
          .from(
            '.lp-hero-cta-row',
            { opacity: 0, y: 14, duration: 0.5, ease: 'back.out(1.2)' },
            '-=0.25',
          )
          .from('.lp-hero-meta', { opacity: 0, y: 12, duration: 0.5 }, '-=0.2')
          .from(
            '.lp-hero-trust',
            { opacity: 0, y: 12, duration: 0.5, stagger: 0.06 },
            '-=0.2',
          )
      }, root)
      return () => ctx.revert()
    },
    { scope: root },
  )

  async function ensureSession() {
    const health = await checkApiHealth(api)
    if (!health.ok) {
      return {
        ok: false,
        message:
          health.message +
          ' (Free Render may sleep — wait 60s and try again, or open /api/health.)',
      }
    }

    let guestEx
    try {
      const { data } = await api.post('/auth/guest')
      setAuth({ email: 'Guest', guest: true }, data.access_token)
      return { ok: true }
    } catch (ex) {
      guestEx = ex
    }
    try {
      const { data } = await api.post('/auth/login', {
        email: 'demo@demo.com',
        password: 'demo123',
      })
      setAuth({ email: 'demo@demo.com' }, data.access_token)
      return { ok: true }
    } catch (loginEx) {
      return { ok: false, message: formatGuestSessionError(guestEx, loginEx) }
    }
  }

  async function handleGuest() {
    if (guestLoading) return
    setGuestLoading(true)
    try {
      const session = await ensureSession()
      if (!session.ok) {
        toast.error(session.message)
        return
      }
      toast.success('Welcome — workspace is ready.')
      nav('/mission-control', { replace: true })
    } finally {
      setGuestLoading(false)
    }
  }

  async function handleHackathonDemo() {
    if (guestLoading) return
    setGuestLoading(true)
    try {
      const session = await ensureSession()
      if (!session.ok) {
        toast.error(session.message)
        return
      }
      sessionStorage.setItem(HELIX_AUTO_DEMO_KEY, '1')
      toast.success('Launching judge demo…')
      nav('/judge-demo', { replace: true, state: { autoStart: true } })
    } finally {
      setGuestLoading(false)
    }
  }

  return (
    <div ref={root} className="lp" id="top">
      <NavBar
        dark={dark}
        onToggleTheme={toggle}
        onGuest={handleGuest}
        guestLoading={guestLoading}
      />

      <div
        className="lp-hero-canvas"
        aria-hidden
        style={{ background: dark ? '#020617' : '#f0f9ff' }}
      >
        {isHeroParticlesEnabled() && (
          <Suspense fallback={null}>
            <HeroParticles dark={dark} />
          </Suspense>
        )}
      </div>

      <section className="lp-hero" aria-labelledby="lp-hero-title">
        <div className="lp-hero-inner">
          <p className="lp-hero-eyebrow">
            <span className="lp-eyebrow-dot" /> Autonomous SDLC team · AI-Thon
          </p>
          <h1 id="lp-hero-title" className="lp-hero-title">
            {HERO_TITLE.split(' ').map((w, i) => (
              <span key={`${w}-${i}`} className="lp-hero-title-word">
                {w}
              </span>
            ))}
          </h1>
          <p className="lp-hero-sub">
            Not another dashboard with twenty-five features. Helix is PM, Architect, QA,
            and Scrum Master in one flow — you upload, the team builds your delivery package,
            you review and export.
          </p>
          <div className="lp-hero-cta-row">
            <MagneticButton>
              <button
                type="button"
                className="lp-btn lp-btn-primary lp-btn-lg"
                onClick={() => void handleHackathonDemo()}
                disabled={guestLoading}
              >
                {guestLoading ? 'Starting…' : 'Start hackathon demo'}
                <IconArrowRight />
              </button>
            </MagneticButton>
            <Link to="/mission-control" className="lp-btn lp-btn-outline lp-btn-lg">
              Upload your own PRD
            </Link>
            <Link to="/register" className="lp-btn lp-btn-outline lp-btn-lg">
              Create account
            </Link>
            <Link to="/login" className="lp-btn lp-btn-ghost lp-btn-lg">
              Sign in
            </Link>
          </div>
          <p className="lp-hero-meta">
            <IconCheck /> Judges: one button → Judge Demo · <IconCheck /> Mission Control = custom
            upload only
          </p>
          <div className="lp-hero-trust-row">
            {[
              'Launch AI team',
              'Live agent run',
              'Review checklist',
              APPROVE_EXPORT_CTA,
            ].map((t) => (
              <span key={t} className="lp-hero-trust">
                {t}
              </span>
            ))}
          </div>
        </div>
        <div className="lp-hero-glow" aria-hidden />
      </section>

      <section className="lp-stats" aria-label="Helix impact metrics">
        <div className="lp-stats-inner">
          {STATS.map((s, idx) => (
            <motion.div
              key={s.label}
              className="lp-stat"
              initial={reduce ? false : { opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.4, delay: idx * 0.06 }}
            >
              <span className="lp-stat-value">
                <Counter value={s.value} duration={1500 + idx * 120} />
              </span>
              <span className="lp-stat-label">{s.label}</span>
            </motion.div>
          ))}
        </div>
      </section>

      <Section
        id="features"
        eyebrow="Your team"
        title="Four roles. One outcome."
        kicker={POSITIONING_LINE}
      >
        <div className="lp-features-grid">
          {FEATURES.map((f, idx) => {
            const Icon = f.icon
            return (
              <Tilt key={f.title} max={6} scale={1.015} as="div">
                <motion.article
                  className="lp-feature"
                  initial={reduce ? false : { opacity: 0, y: 22 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-60px' }}
                  transition={{ duration: 0.45, delay: (idx % 3) * 0.06 }}
                >
                  <span className="lp-feature-icon">
                    <Icon />
                  </span>
                  <h3>{f.title}</h3>
                  <p>{f.description}</p>
                </motion.article>
              </Tilt>
            )
          })}
        </div>
      </Section>

      <Section
        id="workflow"
        eyebrow="How it works"
        title="Three surfaces. Zero tool sprawl."
        kicker="Mission Control → Workspace → Delivery Package. That is the product."
      >
        <div className="lp-workflow">
          {WORKFLOW.map((w, idx) => (
            <Tilt key={w.step} max={4} scale={1.01}>
              <motion.div
                className="lp-step"
                initial={reduce ? false : { opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-60px' }}
                transition={{ duration: 0.4, delay: idx * 0.07 }}
              >
                <span className="lp-step-num">{w.step}</span>
                <h3>{w.title}</h3>
                <p>{w.description}</p>
              </motion.div>
            </Tilt>
          ))}
        </div>
      </Section>

      <Section
        id="personas"
        eyebrow="For every role on the team"
        title="Helix meets you where you work."
        kicker="Product, engineering, and QA share one source of truth — generated, refined, and exported in minutes."
      >
        <div className="lp-personas">
          {USE_CASES.map((p, idx) => {
            const Icon = p.icon
            return (
              <Tilt key={p.role} max={5} scale={1.012} as="div">
                <motion.article
                  className="lp-persona"
                  initial={reduce ? false : { opacity: 0, y: 22 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-60px' }}
                  transition={{ duration: 0.45, delay: idx * 0.06 }}
                >
                  <span className="lp-persona-icon">
                    <Icon />
                  </span>
                  <h3>{p.role}</h3>
                  <ul>
                    {p.points.map((line) => (
                      <li key={line}>
                        <IconCheck /> {line}
                      </li>
                    ))}
                  </ul>
                </motion.article>
              </Tilt>
            )
          })}
        </div>
      </Section>

      <Section
        id="impact"
        eyebrow="Measured impact"
        title="Built for the AI-Thon judges, ready for real teams."
        kicker="Every metric is computed by the same pipeline you see in the workspace — no hand-waving."
        className="lp-section-impact"
      >
        <div className="lp-impact">
          <motion.div
            className="lp-impact-card lp-impact-card-primary"
            initial={reduce ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.5 }}
          >
            <p className="lp-eyebrow">Live demo path</p>
            <h3>
              New project → <em>Load sample requirement</em> → Ingest → watch the stream.
            </h3>
            <p>
              Hit <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> for the command palette,
              review the checklist (stories, tasks, tests, sprint plan, risks), then{' '}
              <strong>{APPROVE_EXPORT_CTA}</strong> for a Jira CSV you import yourself.
            </p>
            <div className="lp-hero-cta-row" style={{ marginTop: '1.25rem' }}>
              <button
                type="button"
                className="lp-btn lp-btn-primary"
                onClick={handleGuest}
                disabled={guestLoading}
              >
                {guestLoading ? 'Spinning up…' : 'Launch the workspace'}
                <IconArrowRight />
              </button>
              <Link to="/login" className="lp-btn lp-btn-outline">
                I already have an account
              </Link>
            </div>
          </motion.div>
          <motion.div
            className="lp-impact-card"
            initial={reduce ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.5, delay: 0.08 }}
          >
            <p className="lp-eyebrow">Defensible numbers</p>
            <ul className="lp-impact-list">
              <li>
                <strong>~4 hrs → ~4 min</strong> from raw text to a complete, cited
                backlog — measured on the bundled sample requirement.
              </li>
              <li>
                <strong>citation_item_rate</strong> exposed on every project so QA can
                gate exports on coverage, not vibes.
              </li>
              <li>
                <strong>Streaming SSE</strong> per stage (intent, ambiguity, backlog,
                tests, estimates, risks) keeps the loop transparent.
              </li>
            </ul>
          </motion.div>
        </div>
      </Section>

      <section className="lp-cta" aria-label="Get started">
        <motion.div
          className="lp-cta-inner"
          initial={reduce ? false : { opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.55 }}
        >
          <h2>Stop translating documents. Start shipping outcomes.</h2>
          <p>
            Spin up a guest workspace in one click, or create a permanent account to keep
            your projects.
          </p>
          <div className="lp-hero-cta-row" style={{ justifyContent: 'center' }}>
            <MagneticButton>
              <button
                type="button"
                className="lp-btn lp-btn-primary lp-btn-lg"
                onClick={handleGuest}
                disabled={guestLoading}
              >
                {guestLoading ? 'Spinning up…' : 'Try Helix as a guest'}
                <IconArrowRight />
              </button>
            </MagneticButton>
            <Link to="/register" className="lp-btn lp-btn-outline lp-btn-lg">
              Create free account
            </Link>
          </div>
        </motion.div>
      </section>

      <footer className="lp-footer">
        <div className="lp-footer-inner">
          <div className="lp-footer-brand">
            <span className="lp-nav-brand">
              <IconLogo />
              <span>Helix</span>
            </span>
            <p className="lp-footer-tag">
              Intelligent SDLC Copilot — turning raw requirements into shipped quality.
            </p>
          </div>
          <div className="lp-footer-cols">
            <div className="lp-footer-col">
              <h4>Product</h4>
              <a href="#features">Features</a>
              <a href="#workflow">How it works</a>
              <a href="#personas">For teams</a>
            </div>
            <div className="lp-footer-col">
              <h4>Get started</h4>
              <Link to="/register">Create account</Link>
              <Link to="/login">Sign in</Link>
              <button
                type="button"
                className="lp-footer-link"
                onClick={handleGuest}
                disabled={guestLoading}
              >
                Try as guest
              </button>
            </div>
            <div className="lp-footer-col">
              <h4>Built for</h4>
              <span>AI-Thon submission</span>
              <span>Hackathon judges</span>
              <a
                href="https://github.com"
                target="_blank"
                rel="noreferrer"
                className="lp-footer-icon-link"
              >
                <IconGithub /> View source
              </a>
            </div>
          </div>
        </div>
        <p className="lp-footer-meta">
          © {new Date().getFullYear()} Helix — Built for AI-Thon. All trademarks belong
          to their respective owners.
        </p>
      </footer>
    </div>
  )
}
