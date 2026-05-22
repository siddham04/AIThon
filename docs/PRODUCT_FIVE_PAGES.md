# Helix — 5-page product

**AI-first, hackathon-polished.** All other UI routes redirect here.

| # | Route | Page | Role |
|---|-------|------|------|
| 1 | `/mission-control` | Mission Control | Home — upload (PDF, DOCX, text, Jira, meeting) → Launch AI team → live status |
| 2 | `/ai-workspace` | AI Workspace | Checklist (stories, tasks, tests, sprint, risks) → **Approve & Export** (CSV; no auto-push to Jira) |
| 3 | `/delivery-command` | Delivery Center | Sprint plan, team allocation, dependency graph, timeline |
| 4 | `/copilot` | Copilot (SDLC chatbot) | Trained assistant — grounded Q&A + actions on project artifacts |
| 5 | `/settings` | Settings | Team size, velocity, tech stack, Jira/GitHub/Azure credentials |

## Removed

- **35 orphan pages** deleted from `helix-frontend/src/pages/`
- Judge Demo, Delivery Package, legacy dashboards → redirects
- **11 legacy CSS bundles** removed from `main.jsx` (kept: `index`, `tidy`, `helix-design`, `workspace`, `product-five`)
- **Three.js ambient** removed from `AppShell` (saves ~880 KB chunk on app load)

## Human vs AI (judge-safe framing)

**Autonomous by default** — AI runs the full SDLC. Humans only:

1. Upload on Mission Control  
2. See checklist: stories, tasks, tests, sprint plan, risks  
3. Click **Approve & Export** (marks scope approved, downloads Jira CSV — you import; Helix does not auto-push)

| Humans | AI |
|--------|-----|
| Upload + Approve & Export | PM, Architect, QA, Scrum pipeline |
| Settings (team + keys) | Sprint plan, graph, estimates in Delivery Center |
| Copilot questions | Answers from project context |

## Legacy URLs

All old paths (`/dashboard`, `/judge-demo`, `/delivery-package`, `/studio`, …) redirect via `lib/productFlow.js`.
