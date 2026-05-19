# Push Helix to GitHub (`siddham04/AIThon`)

If `git push` returns **403** / `RPC failed` even though the remote is correct, GitHub is rejecting the **credential** (not your code).

## Option A — One-shot script (fastest on Windows)

From the repo root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\push-github.ps1
```

Paste your **fine-grained PAT** when prompted. Requirements on the token:

- **Repository access:** include **`AIThon`** (or “All repositories”).
- **Permissions:** **Contents → Read and write**, **Metadata → Read**.
- If the repo is under an **organization**, click **Authorize SSO** for that org on the token page.

The script pushes over HTTPS once and sets `main` to track `origin/main`. It does **not** save the token in `git remote`.

## Option B — Credential Manager + normal push

1. Windows **Credential Manager** → remove `git:https://github.com` entries.
2. `git push -u origin main`
3. Username: `siddham04` — Password: **PAT** (not your GitHub password).

## Option C — SSH (no PAT in HTTPS)

1. Create a key: `ssh-keygen -t ed25519 -C "your_email" -f $HOME\.ssh\id_ed25519_github -N ""`
2. Add **public** key in GitHub → Settings → SSH keys.
3. `git remote set-url origin git@github.com:siddham04/AIThon.git`
4. `git push -u origin main`

## TLS warning (Git Credential Manager)

Re-enable verification when you can: [GCM TLS verify](https://aka.ms/gcm/tlsverify).
