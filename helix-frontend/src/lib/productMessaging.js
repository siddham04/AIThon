/**
 * Single source of truth for the Helix product narrative.
 *
 * The mentor line judges should remember:
 *   "Upload messy requirements → launch AI team → get a release-ready
 *    delivery package with full traceability in under 10 minutes."
 *
 * Anywhere we surface a tagline, CTA, or hero copy, import from this
 * file. Do NOT duplicate the phrasing in JSX strings.
 */

export const HERO_TITLE =
  'From messy requirements to a release-ready delivery package — in under 10 minutes.'

export const NARRATIVE_PITCH =
  'Upload messy requirements → launch the AI team → get a release-ready delivery package with full traceability. Under 10 minutes, every artifact cited back to its source clause.'

export const POSITIONING_LINE =
  'Autonomous by default. You review, approve, then export — nothing ships to Jira without your sign-off.'

export const LAUNCH_CTA = 'Launch AI team'
export const LAUNCH_CTA_SUB =
  'AI generates everything · you approve before export'

export const APPROVE_EXPORT_CTA = 'Approve & Export'

/**
 * The four narrative beats — used on the landing STATS row so the
 * homepage mirrors the same story arc as the demo.
 *
 * Keep these short; they render as <Counter value={…} /> with a label.
 */
export const NARRATIVE_BEATS = [
  { value: '1', label: 'upload — paste, file, URL, or voice' },
  { value: '11', label: 'AI stages stream live, in parallel' },
  { value: '< 10', label: 'minutes to a release-ready package' },
  { value: '100%', label: 'artifacts cited back to source clauses' },
]

/**
 * Short, scannable description of the three product surfaces — used by
 * the "How it works" section on Landing and by GUIDED_TOUR.md.
 */
export const SURFACE_STEPS = [
  {
    step: '01',
    title: 'Upload & launch',
    description:
      'Paste, drop a PDF, or speak the requirement. Hit Launch — the AI team takes it from there.',
  },
  {
    step: '02',
    title: 'Watch the AI team run',
    description:
      '11 streamed stages: quality → review board → ambiguity → stories → architecture → sprint plan → APIs → tests → backlog → readiness gate.',
  },
  {
    step: '03',
    title: 'Approve & export',
    description:
      'Release-ready Delivery Package — every artifact cites its source clause. Approve, then push to Jira / ADO / GitHub / CSV.',
  },
]
