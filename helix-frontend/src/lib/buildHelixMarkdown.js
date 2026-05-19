import { buildExportAuditFooter } from './exportAuditLine'

/** One-click PRD-style export for demos and handoff (client-side). */
export function buildHelixBundleMarkdown(
  {
    projectName,
    summary,
    stories,
    tasks,
    workingRequirement,
    citationItemRate,
    includeAuditFooter = true,
  },
) {
  const lines = []
  lines.push(`# ${projectName || 'Helix project'}`, '')
  if (summary?.one_liner) {
    lines.push('## Summary', summary.one_liner, '')
  }
  if (summary?.objective) {
    lines.push('### Objective', summary.objective, '')
  }
  if (citationItemRate != null && !Number.isNaN(Number(citationItemRate))) {
    lines.push(
      '### Traceability',
      `Estimated citation coverage (stories/tasks/tests with sources): **${Math.round(Number(citationItemRate) * 100)}%**`,
      '',
    )
  }
  if (workingRequirement?.trim()) {
    lines.push('## Working requirement', '', workingRequirement.trim(), '')
  }
  if (stories?.length) {
    lines.push('## User stories', '')
    for (const s of stories) {
      lines.push(`### ${s.title || 'Untitled'}`, s.goal || '', '')
    }
  }
  if (tasks?.length) {
    lines.push('## Tasks', '')
    for (const t of tasks) {
      lines.push(`- **${t.title || 'Task'}**`, `  ${t.description || ''}`, '')
    }
  }
  let out = lines.join('\n').trim()
  if (includeAuditFooter) out += buildExportAuditFooter()
  return out
}
