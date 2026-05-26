#!/usr/bin/env bash
# Helix — Judge Mode launcher (macOS / Linux / WSL)
#
# One-command, offline-safe demo. See docs/JUDGE_MODE.md.
#
# What this does:
#   1. Verifies prerequisites (python3, node, npm).
#   2. Starts the backend on :8765 in demo mode (HELIX_DEMO_FAST=true).
#   3. Starts the frontend dev server on :5173.
#   4. Polls /api/health until green, then opens the seeded project
#      Delivery Package in the default browser.
#   5. Prints a single status line per gate; exits non-zero on any failure.
#
# Stop both servers: Ctrl+C in this window.

set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8765}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
NO_BROWSER="${NO_BROWSER:-0}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

c_cyan="$(printf '\033[36m')"
c_green="$(printf '\033[32m')"
c_red="$(printf '\033[31m')"
c_reset="$(printf '\033[0m')"

step()  { printf "%s[judge_demo]%s %s\n" "$c_cyan"  "$c_reset" "$*"; }
ok()    { printf "%s[judge_demo] OK  %s%s\n" "$c_green" "$*" "$c_reset"; }
fail()  { printf "%s[judge_demo] FAIL %s%s\n" "$c_red"   "$*" "$c_reset" 1>&2; }

# 1. Prereqs ------------------------------------------------------------
step "Checking prerequisites..."
for cmd in python3 node npm; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    fail "$cmd not found on PATH. Install it, then retry."
    exit 2
  fi
done
ok "python3, node, npm available"

# 2. Free target ports --------------------------------------------------
port_free() {
  local p="$1"
  if command -v lsof >/dev/null 2>&1; then
    ! lsof -i ":$p" -sTCP:LISTEN -t >/dev/null 2>&1
  elif command -v ss >/dev/null 2>&1; then
    ! ss -ltn "sport = :$p" | tail -n +2 | grep -q ":$p"
  else
    return 0
  fi
}
for p in "$BACKEND_PORT" "$FRONTEND_PORT"; do
  if ! port_free "$p"; then
    fail "Port $p is already in use. Free it (e.g. 'lsof -i :$p') and retry."
    exit 3
  fi
done
ok "Ports $BACKEND_PORT and $FRONTEND_PORT are free"

# 3. Backend ------------------------------------------------------------
BACKEND_LOG="$(mktemp -t helix-backend.XXXXXX.log)"
FRONTEND_LOG="$(mktemp -t helix-frontend.XXXXXX.log)"

step "Starting backend on :$BACKEND_PORT (log: $BACKEND_LOG)"
(
  cd "$REPO_ROOT/helix-backend"
  if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
  python scripts/seed.py 2>/dev/null || true
  export HELIX_DEMO_FAST=true
  export HELIX_USE_AI=false
  export HELIX_ALLOW_INSECURE_JWT=1
  exec uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT"
) >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# 4. Frontend -----------------------------------------------------------
step "Starting frontend on :$FRONTEND_PORT (log: $FRONTEND_LOG)"
(
  cd "$REPO_ROOT/helix-frontend"
  if [[ ! -d "node_modules" ]]; then
    npm ci
  fi
  exec npm run dev -- --port "$FRONTEND_PORT" --host
) >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

cleanup() {
  step "Stopping backend ($BACKEND_PID) + frontend ($FRONTEND_PID)..."
  kill "$BACKEND_PID"  >/dev/null 2>&1 || true
  kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  wait "$BACKEND_PID"  2>/dev/null || true
  wait "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 5. Poll backend health ------------------------------------------------
step "Waiting for backend /api/health (up to 90s)..."
healthy=0
for _ in $(seq 1 45); do
  sleep 2
  if curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/health" >/dev/null 2>&1; then
    healthy=1
    break
  fi
done
if [[ "$healthy" -ne 1 ]]; then
  fail "Backend never became healthy on :$BACKEND_PORT"
  echo "  --- backend log tail ---"
  tail -n 40 "$BACKEND_LOG" || true
  exit 4
fi
ok "Backend healthy on http://127.0.0.1:$BACKEND_PORT"

# 6. Poll frontend ------------------------------------------------------
step "Waiting for frontend on :$FRONTEND_PORT (up to 90s)..."
ui_ok=0
for _ in $(seq 1 45); do
  sleep 2
  if curl -fsS "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
    ui_ok=1
    break
  fi
done
if [[ "$ui_ok" -ne 1 ]]; then
  fail "Frontend never responded on :$FRONTEND_PORT"
  echo "  --- frontend log tail ---"
  tail -n 40 "$FRONTEND_LOG" || true
  exit 6
fi
ok "Frontend responding on http://localhost:$FRONTEND_PORT"

# 7. Open browser -------------------------------------------------------
DEMO_URL="http://localhost:$FRONTEND_PORT/project/proj_demo_seed01/ai-workspace"
if [[ "$NO_BROWSER" -ne 1 ]]; then
  step "Opening $DEMO_URL"
  if command -v open       >/dev/null 2>&1; then open       "$DEMO_URL" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open   "$DEMO_URL" >/dev/null 2>&1 || true
  elif command -v wslview  >/dev/null 2>&1; then wslview    "$DEMO_URL" >/dev/null 2>&1 || true
  fi
fi

echo ""
echo "================================================================"
echo " HELIX JUDGE MODE READY"
echo "================================================================"
echo " API:        http://127.0.0.1:$BACKEND_PORT"
echo " UI:         http://localhost:$FRONTEND_PORT"
echo " Pre-baked:  $DEMO_URL"
echo " Login:      demo@demo.com / demo123  (or 'Try as Guest')"
echo " Mode:       HELIX_DEMO_FAST=true, HELIX_USE_AI=false (offline)"
echo "================================================================"
echo ""
echo "Press Ctrl+C to stop both servers."

# 8. Stay alive until child dies ---------------------------------------
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 5
done

if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  fail "Backend process exited unexpectedly."
  tail -n 40 "$BACKEND_LOG" || true
  exit 7
fi
if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
  fail "Frontend process exited unexpectedly."
  tail -n 40 "$FRONTEND_LOG" || true
  exit 8
fi
