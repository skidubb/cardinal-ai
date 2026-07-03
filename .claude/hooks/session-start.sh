#!/usr/bin/env bash
# Cardinal Element session bootstrap.
# Announces project layout and checks that the three subprojects are importable.
# Best-effort: never fails a session — only reports.

set -u

CE_REPO_ROOT="${CE_REPO_ROOT:-$(pwd)}"
AGENT_BUILDER="$CE_REPO_ROOT/CE - Agent Builder"
ORCHESTRATION="$CE_REPO_ROOT/CE - Multi-Agent Orchestration"
EVALS="$CE_REPO_ROOT/CE - Evals"

echo "=== Cardinal Element session start ==="
echo "repo: $CE_REPO_ROOT"

check_venv() {
  local label="$1" dir="$2"
  if [ -d "$dir/venv" ]; then
    echo "[venv] $label: present ($dir/venv)"
  elif [ -d "$dir" ]; then
    echo "[venv] $label: MISSING — run: cd \"$dir\" && python -m venv venv && source venv/bin/activate && pip install -e ."
  fi
}

check_venv "Agent Builder" "$AGENT_BUILDER"
check_venv "Orchestration" "$ORCHESTRATION"
check_venv "Evals"         "$EVALS"

if command -v docker >/dev/null 2>&1; then
  if docker compose -f "$CE_REPO_ROOT/docker-compose.yml" ps postgres 2>/dev/null | grep -q "healthy\|running"; then
    echo "[postgres] running"
  else
    echo "[postgres] not running — start with: docker compose up -d postgres"
  fi
else
  echo "[postgres] docker not available in this environment (ok — persistence degrades gracefully)"
fi

if [ -f "$CE_REPO_ROOT/.env" ]; then
  if grep -q "^LANGFUSE_SECRET_KEY=" "$CE_REPO_ROOT/.env" 2>/dev/null; then
    echo "[langfuse] keys present in .env"
  else
    echo "[langfuse] no LANGFUSE_SECRET_KEY — traces will no-op"
  fi
else
  echo "[env] no root .env file (subprojects may have their own)"
fi

echo "======================================="
