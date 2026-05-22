# Archived pages

Orphan React pages from the hackathon-era UI were removed from `src/pages/` in the P0 cleanup (May 2026).

**Active routed pages (9):**

- `Landing.jsx`, `Login.jsx`, `Register.jsx`
- `MissionControl.jsx`, `AiWorkspace.jsx`, `DeliveryCommandCenter.jsx`
- `CopilotChat.jsx`, `Settings.jsx`, `WinningDemoScreen.jsx`

To restore a page from git history:

```bash
git show HEAD~1:helix-frontend/src/pages/Dashboard.jsx > Dashboard.jsx
```

Re-run `scripts/archive_orphan_pages.ps1` if new orphan `.jsx` files appear at `pages/` root.
