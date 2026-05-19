import { lazy, Suspense, useRef } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { Link } from 'react-router-dom'
import { useDarkMode } from '../hooks/useDarkMode'

const HeroParticles = lazy(() => import('../components/landing/HeroParticles'))

const title = 'From raw requirements to shipped quality.'

export default function Landing() {
  const root = useRef(null)
  const { dark, toggle } = useDarkMode()

  useGSAP(
    () => {
      const ctx = gsap.context(() => {
        const tl = gsap.timeline({ defaults: { ease: 'power2.out' } })
        tl.from('.landing-eyebrow', { opacity: 0, y: 12, duration: 0.45 })
          .from(
            '.landing-title-word',
            { opacity: 0, y: 24, duration: 0.45, stagger: 0.04 },
            '-=0.2',
          )
          .from('.landing-sub', { opacity: 0, duration: 0.55 }, '-=0.15')
          .from(
            '.landing-cta-row',
            { opacity: 0, scale: 0.94, duration: 0.4, ease: 'back.out(1.4)' },
            '-=0.2',
          )
      }, root)
      return () => ctx.revert()
    },
    { scope: root },
  )

  return (
    <div ref={root} className="landing">
      <div className="landing-theme-bar">
        <button
          type="button"
          className="btn ghost small"
          onClick={toggle}
          title={dark ? 'Switch to light theme' : 'Switch to dark theme'}
          aria-pressed={dark}
        >
          {dark ? 'Light mode' : 'Dark mode'}
        </button>
      </div>
      <Suspense
        fallback={
          <div
            className="hero-canvas"
            aria-hidden
            style={{ background: dark ? '#020617' : '#f0f9ff' }}
          />
        }
      >
        <HeroParticles dark={dark} />
      </Suspense>
      <div className="landing-overlay">
        <p className="landing-eyebrow">Helix — Intelligent SDLC Copilot</p>
        <h1 className="landing-title">
          {title.split(' ').map((w, i) => (
            <span
              key={`${w}-${i}`}
              className="landing-title-word"
              style={{ display: 'inline-block', marginRight: '0.35em' }}
            >
              {w}
            </span>
          ))}
        </h1>
        <p className="landing-sub">
          Traceable stories, tasks, tests, and ambiguity surfacing — with a copilot that
          understands your graph.
        </p>
        <div className="landing-cta-row">
          <Link to="/login" className="btn btn-primary landing-cta">
            Sign in
          </Link>
          <Link to="/register" className="btn ghost landing-cta landing-cta-secondary">
            Create account
          </Link>
        </div>
        <p className="landing-demo-hint muted small">
          Tip: after sign-in, press <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd> anywhere in the app
          for the command palette — ideal for live demos.
        </p>
      </div>
    </div>
  )
}
