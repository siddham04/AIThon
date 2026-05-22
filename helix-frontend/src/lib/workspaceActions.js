import { api } from '../api/client'
import { loadMissionConfig } from './missionConfig'

/** Classify user message → chat or structured action. */
export function classifyWorkspaceIntent(text) {
  const q = (text || '').trim().toLowerCase()
  if (!q) return { mode: 'chat' }

  if (/\b(generate|create|build|draw|run)\b.*\b(arch|architecture|diagram|system\s*design)\b/.test(q)
    || /\b(arch|architecture)\b.*\b(generate|create)\b/.test(q)) {
    return { mode: 'action', action: 'generate_architecture', label: 'Generate architecture' }
  }

  if (/\b(show|display|view|open|see|get)\b.*\b(sprint|plan|backlog)\b/.test(q)
    || /\bsprint\s*plan\b/.test(q)) {
    return { mode: 'action', action: 'show_sprint_plan', label: 'Sprint plan' }
  }

  if (/\b(regenerat|regen|refresh|re-?run|create)\b.*\b(tests?|test\s*cases?)\b/.test(q)
    || /\b(tests?|qa)\b.*\b(regenerat|generate)\b/.test(q)) {
    return { mode: 'action', action: 'regenerate_tests', label: 'Regenerate tests' }
  }

  if (/\b(estimat|forecast|how\s+long|story\s*points?|effort|timeline)\b/.test(q)
    && /\b(effort|points?|work|delivery|project)\b/.test(q)) {
    return { mode: 'action', action: 'estimate_effort', label: 'Effort estimate' }
  }

  if (/\b(show|list|display|what)\b.*\b(risks?|threats?)\b/.test(q)
    || /^what are the risks\??$/.test(q)) {
    return { mode: 'action', action: 'show_risks', label: 'Risk analysis' }
  }

  if (/\bwhy\b.*\b(priorit|rank|order|sprint|task|story)\b/.test(q)
    || /\b(priorit|rank).*\bwhy\b/.test(q)) {
    return { mode: 'action', action: 'explain_priority', label: 'Prioritization' }
  }

  return { mode: 'chat' }
}

async function projectText(projectId) {
  const { data } = await api.get(`/projects/${projectId}`)
  return (data.raw_input || '').trim()
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

export async function runWorkspaceAction(projectId, action, userQuestion) {
  const cfg = loadMissionConfig(projectId)

  switch (action) {
    case 'generate_architecture': {
      const diagram = await (async () => {
        try {
          const { data } = await api.post(`/studio/diagram/${projectId}/run`, null, {
            params: { use_ai: true },
          })
          return data
        } catch {
          const req = await projectText(projectId)
          const { data } = await api.post('/studio/diagram/generate', {
            requirement: req || 'System under design',
            use_ai: true,
          })
          return data
        }
      })()
      return {
        answer:
          'Here is the **system architecture** generated from your requirements. Layers and services are grounded in the current project scope.',
        artifact: {
          type: 'architecture',
          diagram,
        },
        suggested_followups: ['Show sprint plan', 'What are the risks?', 'Estimate effort'],
      }
    }

    case 'show_sprint_plan': {
      const plan = await (async () => {
        try {
          const res = await api.get(`/sprint-plan/${projectId}/auto`)
          return res.data
        } catch {
          const req = await projectText(projectId)
          const { data } = await api.post(`/sprint-plan/${projectId}/auto`, {
            requirement: req || 'Project requirements',
            team_size: cfg.teamSize,
            sprint_weeks: cfg.sprintWeeks,
            use_ai: true,
          })
          return data
        }
      })()
      return {
        answer: plan?.suggested_sprint
          ? `**Sprint plan** ready — suggested focus: **${plan.suggested_sprint}** (${plan.total_story_points ?? '—'} story points across ${plan.tasks?.length ?? 0} tasks).`
          : '**Sprint plan** generated from your backlog and team configuration.',
        artifact: { type: 'sprint', plan },
        suggested_followups: ['Why was this task prioritized?', 'Generate architecture', 'Estimate effort'],
      }
    }

    case 'show_risks': {
      const risk = await (async () => {
        try {
          const { data } = await api.get(`/studio/risk/${projectId}/json`)
          return data
        } catch {
          const { data } = await api.post(`/studio/risk/${projectId}/run`, null, {
            params: { use_ai: true },
          })
          return data
        }
      })()
      return {
        answer: `**Risk scan** — level **${risk?.risk_level || 'medium'}**. Payment, security, and scope gaps are highlighted below.`,
        artifact: {
          type: 'risks',
          risk,
          projectRisks: [],
        },
        suggested_followups: ['Generate architecture', 'Regenerate test cases', 'Show sprint plan'],
      }
    }

    case 'regenerate_tests': {
      await api.post(`/testcases/generate/${projectId}`).catch(() => null)
      await sleep(2800)
      const { data: cases } = await api.get(`/testcases/${projectId}`)
      const list = Array.isArray(cases) ? cases : cases?.test_cases || []
      return {
        answer: `Regenerated **${list.length} test cases** linked to your stories and acceptance criteria.`,
        artifact: { type: 'tests', cases: list },
        suggested_followups: ['What are the risks?', 'Show sprint plan', 'Which stories lack tests?'],
      }
    }

    case 'estimate_effort': {
      const { data: effort } = await api.post(`/studio/effort/${projectId}/run`, null, {
        params: { use_ai: true },
      }).catch(async () => {
        const req = await projectText(projectId)
        return api.post('/studio/effort/analyze', { requirement: req, use_ai: true })
      })
      return {
        answer: `**Effort estimate** — ~**${effort?.story_points ?? effort?.total_story_points ?? '—'}** story points · **${effort?.complexity || 'medium'}** complexity · ~**${Math.round(effort?.estimated_hours ?? 0)}** engineering hours.`,
        artifact: { type: 'effort', effort },
        suggested_followups: ['Show sprint plan', 'Generate architecture', 'What are the risks?'],
      }
    }

    case 'explain_priority': {
      const { data: turn } = await api.post(`/assistant/${projectId}/ask`, {
        question:
          `${userQuestion}\n\nExplain using concrete task titles, story points, priority fields, dependencies, and sprint placement from this project. Focus on *why* ordering decisions were made.`,
        use_ai: true,
      })
      return {
        answer: turn.answer,
        citations: turn.citations,
        suggested_followups: turn.suggested_followups || [
          'Show sprint plan',
          'What are the risks?',
          'Estimate effort',
        ],
        method: turn.method,
      }
    }

    default:
      return null
  }
}

export async function askWorkspaceChat(projectId, question) {
  const { data } = await api.post(`/assistant/${projectId}/ask`, {
    question,
    use_ai: true,
  })
  return data
}

export const WORKSPACE_STARTERS = [
  'Generate architecture',
  'Show sprint plan',
  'What are the risks?',
  'Why was this task prioritized?',
  'Regenerate test cases',
  'Estimate effort',
]
