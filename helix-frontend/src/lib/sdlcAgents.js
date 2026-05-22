/**
 * Five AI surfaces for hackathon narrative: 4 pipeline agents + SDLC Copilot.
 */
import { MISSION_AGENTS } from './missionAgents'

export const SDLC_COPILOT_AGENT = {
  id: 'copilot',
  label: 'SDLC Copilot',
  short: 'Copilot',
  glyph: '💬',
  role: 'Trained on your project — stories, APIs, risks, sprint',
}

export const PRODUCT_AI_AGENTS = [...MISSION_AGENTS, SDLC_COPILOT_AGENT]

/** Grounded prompts aligned with backend sdlc_assistant intents */
export const SDLC_COPILOT_STARTERS = [
  'Which requirements are incomplete?',
  'What APIs need changes?',
  'Which requirements are ambiguous?',
  'Show all security risks.',
  'Which stories don\'t have tests?',
  'Summarise the architecture in one paragraph.',
]
