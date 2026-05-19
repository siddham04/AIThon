# Submission ZIP under 50 MB

Do **not** zip `node_modules`, Python virtualenvs, `.git`, or build output — they are huge and **regenerate** from `package-lock.json` / `requirements.txt`.

## What was likely bloating your folder

| Path | Typical size | Action |
|------|----------------|--------|
| `helix-frontend/node_modules/` | hundreds of MB | **Delete** before zipping; restore with `npm ci`. |
| `.venv`, `helix-backend/.venv`, `helix-backend/.venv2` | hundreds of MB–1 GB+ | **Delete**; restore with `python -m venv .venv` + `pip install -r requirements.txt`. |
| `helix-frontend/dist/` | a few MB | **Delete**; optional; recreated by `npm run build`. |
| `.git/` | varies | **Exclude** from hackathon ZIP (optional); judges only need source. |

## One-command ZIP (recommended)

From the **repository root**:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\make_submission_zip.ps1
```

Creates **`Helix-AI-Thon-submission.zip`** next to the project folder (parent of the repo), excluding the paths above. Uses Windows **`tar`** (`--exclude`).

If `tar` is missing, install **Git for Windows** or use **7-Zip** with manual excludes matching `.gitignore`.

## Manual check before upload

```powershell
(Get-Item .\Helix-AI-Thon-submission.zip).Length / 1MB
```

Target: **under 50 MB**.

## If the ZIP is still too large

1. Ensure no **video** or **dataset** was committed under `docs/` or `helix-frontend/public/`.
2. Run `git status` — only submission-needed files should be present.
3. Clone fresh from GitHub to an empty folder, then zip (guarantees no local venv).
