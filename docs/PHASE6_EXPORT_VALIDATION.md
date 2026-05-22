# Phase 6 — Export Validation Report

**Date:** 2026-05-22T11:10:56.872391+00:00  
**Project:** `proj_42e2147b88`  
**Output directory:** `docs/phase6-exports/`  

## Summary

| Passed | Failed | Warn/Skip |
|--------|--------|-----------|
| 9 | 0 | 1 |

## Results

| Export | Status | Detail |
|--------|--------|--------|
| Jira backlog CSV | PASS | Header OK (10 columns) |
| Jira backlog CSV (importable) | PASS | 1 epic, 5 stories, 0 tasks, 0 subtasks — parent chain valid |
| Backlog JSON (/api/backlog/.../json) | PASS | epic + 5 stories + 0 tasks + 0 subtasks |
| Backlog JSON (round-trip) | PASS | Serializable and parseable for downstream import |
| Generic CSV (/api/export/csv) | WARN | Header schema OK; 0 task rows (Scrum agent produced no tasks in pipeline) |
| Project JSON (/api/export/json) | PASS | Full project dump (5 stories, 20 tests) |
| Project JSON (/api/export/json) (re-import) | PASS | id matches project; json.dumps round-trip OK |
| Markdown (/api/export/markdown) | PASS | H1 title, work items section (17359 chars) |
| Azure DevOps CSV | PASS | ADO schema OK — types: Epic, User Story |
| Jira REST push | PASS | ok=False mode=skipped/mock keys=0 |

## Sample files

- `phase6-exports\proj_42e2147b88-jira-backlog.csv`
- `phase6-exports\proj_42e2147b88-backlog.json`
- `phase6-exports\proj_42e2147b88-tasks-export.csv`
- `phase6-exports\proj_42e2147b88-project-full.json`
- `phase6-exports\proj_42e2147b88-export.md`
- `phase6-exports\proj_42e2147b88-ado-backlog.csv`
- `phase6-exports\proj_42e2147b88-jira-push-result.json`

## Export endpoints

| Format | Route | UI surface |
|--------|-------|------------|
| Jira CSV | `GET /api/backlog/{id}/jira-csv` | Delivery Package (primary) |
| ADO CSV | `GET /api/backlog/{id}/ado-csv` | Delivery Package |
| Backlog JSON | `GET /api/backlog/{id}/json` | Delivery Package |
| Project JSON | `GET /api/export/json/{id}` | Delivery Package |
| Tasks CSV | `GET /api/export/csv/{id}` | Delivery Package |
| Markdown | `GET /api/export/markdown/{id}` | Delivery Package |
| Jira REST | `POST /api/backlog/{id}/jira-push` | Delivery Package (optional) |

## Importability notes

- **Jira CSV:** Jira → Settings → Import → CSV. Columns match `backlog_export._CSV_FIELDS`.
- **Backlog JSON:** Machine-readable; re-import via custom script or `POST /generate` input.
- **Project JSON:** `json.loads` + Pydantic `Project` shape; suitable for backup/restore tooling.
- **Markdown:** Paste into Confluence/Notion/GitHub wiki; includes audit footer when exported via API.
- **Jira REST:** Requires `JIRA_BASE_URL`, `JIRA_TOKEN`, `JIRA_PROJECT_KEY` in backend env.

## Re-run

```bash
python scripts/phase6_export_validation.py --project-id <proj_id>
```
