/**
 * Judge Demo + Mission Control — uses canonical autonomous pipeline.
 */
import { AUTONOMOUS_PIPELINE, pipelineStepForDemoStep } from './autonomousPipeline'

export const MESSY_DEMO_REQUIREMENT =
  'We need to roll out OTP-based login for our B2B portal next quarter. ' +
  'End users will receive a 6-digit code via SMS through Twilio; on success ' +
  'we mint a 24h JWT and rotate the refresh token. Admins must enable MFA ' +
  'for everyone in the Finance org by Q3. The new flow has to integrate ' +
  'Stripe for the upcoming Premium tier (monthly + annual). Rollback plan ' +
  'is unclear today. Out of scope: WhatsApp delivery, biometric login, ' +
  'and the legacy LDAP integration. The system must support 10k concurrent ' +
  'sessions, p99 < 500ms, and meet GDPR — user data deleted within 30 days ' +
  'of account closure. Reporting and analytics for OTP delivery are TBD.'

/** @deprecated use AUTONOMOUS_PIPELINE — kept for imports */
export const JUDGE_DEMO_BEATS = AUTONOMOUS_PIPELINE.filter((s) => s.id !== 'export')

export function beatForDemoStep(stepId) {
  const pipe = pipelineStepForDemoStep(stepId)
  if (!pipe) return null
  return { id: pipe.id, label: pipe.label, icon: pipe.icon, demoSteps: pipe.demoSteps }
}

export function delay(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

export async function ensureDemoProject(api, { name = 'Judge Demo — Autonomous SDLC', rawText }) {
  const { data } = await api.post('/projects', {
    name,
    raw_text: rawText || MESSY_DEMO_REQUIREMENT,
  })
  return data.id
}

export function demoStreamUrl(projectId) {
  const base = import.meta.env.VITE_API_BASE?.replace(/\/$/, '') || '/api'
  const root = base.startsWith('http') ? base : `${window.location.origin}${base}`
  return projectId ? `${root}/demo/${projectId}/run` : `${root}/demo/run`
}

