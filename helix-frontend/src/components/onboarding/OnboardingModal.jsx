import { useRef, useState } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { markOnboardingSeen } from './onboardingStorage'

const slides = [
  {
    title: 'Autonomous by default',
    body: 'Upload a requirement and launch the AI team. PM, Architect, QA, and Scrum agents generate stories, tasks, tests, and plans — you do not write the backlog.',
  },
  {
    title: 'AI does the SDLC work',
    body: 'Analysis → architecture → stories → sprint plan → tests → risks. The pipeline runs without you clicking through every tool.',
  },
  {
    title: 'You approve before export',
    body: 'AI Workspace shows a checklist of what was generated. Approve & Export downloads Jira CSV — Helix does not auto-push without your sign-off.',
  },
]

export default function OnboardingModal({ onClose, onLoadSample }) {
  const [step, setStep] = useState(0)
  const isLast = step === slides.length - 1
  const cardRef = useRef(null)
  const slideRef = useRef(null)

  const finish = () => {
    markOnboardingSeen()
    onClose?.()
  }

  useGSAP(
    () => {
      if (!cardRef.current) return
      gsap.from(cardRef.current, {
        opacity: 0,
        y: 12,
        duration: 0.28,
        ease: 'power2.out',
      })
    },
    { scope: cardRef },
  )

  useGSAP(
    () => {
      const el = slideRef.current
      if (!el) return
      gsap.fromTo(
        el,
        { opacity: 0, x: 28 },
        { opacity: 1, x: 0, duration: 0.32, ease: 'power2.out' },
      )
    },
    { dependencies: [step] },
  )

  return (
    <dialog open className="modal onboarding-modal-wrap" aria-labelledby="onb-title">
      <div ref={cardRef} className="modal-card onboarding-card">
        <div ref={slideRef} key={step}>
          <h3 id="onb-title">{slides[step].title}</h3>
          <p className="onboarding-body">{slides[step].body}</p>
        </div>

        <div className="onboarding-dots" role="tablist" aria-label="Onboarding steps">
          {slides.map((_, i) => (
            <button
              key={i}
              type="button"
              className={`onboarding-dot ${i === step ? 'active' : ''}`}
              aria-label={`Step ${i + 1} of ${slides.length}`}
              aria-current={i === step ? 'step' : undefined}
              onClick={() => setStep(i)}
            />
          ))}
        </div>

        <div className="row spread onboarding-actions">
          <button type="button" className="btn ghost" onClick={finish}>
            Skip
          </button>
          <div className="row">
            {step > 0 && (
              <button type="button" className="btn" onClick={() => setStep((s) => s - 1)}>
                Back
              </button>
            )}
            {!isLast && (
              <button type="button" className="btn btn-primary" onClick={() => setStep((s) => s + 1)}>
                Next
              </button>
            )}
            {isLast && (
              <>
                <button
                  type="button"
                  className="btn"
                  onClick={() => {
                    onLoadSample?.()
                    finish()
                  }}
                >
                  Load sample
                </button>
                <button type="button" className="btn btn-primary" onClick={finish}>
                  Got it
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </dialog>
  )
}
