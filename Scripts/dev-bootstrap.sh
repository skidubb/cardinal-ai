#!/usr/bin/env bash
#
# dev-bootstrap.sh — Bring a fresh laptop to a working CE-AGENTS local dev
# state in one command. Safe to re-run (idempotent).
#
# What it does:
#   1. Probes Postgres port. If 5432 is held by a non-ce-agents container,
#      finds the next free port in 5434..5440 and records it in .env.local.
#   2. Starts ce-agents-postgres (via docker compose) on the chosen port.
#      Hard-checks the target DB identity (POSTGRES_DB=ce_platform,
#      POSTGRES_USER=ce) before any destructive action.
#   3. Installs ce-shared, ce-db, ce-graph editable into each project's venv.
#      Install order matters: ce-shared first, because ce-db depends on it and
#      will otherwise stomp the editable install with a stale published copy.
#   4. Runs `alembic upgrade head` against the chosen Postgres.
#   5. Writes + reads back a sanity run via p53_contract_net in research mode
#      (no LLM calls, no cost) and confirms the `runs` row is present.
#   6. Prints the final state: port, installs, alembic head, round-trip.
#
# Flags:
#   --non-interactive    Never prompt. Fail if a decision is needed.
#   --skip-sanity-run    Don't attempt the research-mode smoke test.
#   --dry-run            Print the plan, do not execute destructive steps.
#
# Escape hatches:
#   CE_BOOTSTRAP_PORT=N  Force a specific Postgres host port.
#   CE_SKIP_CONTAINER=1  Don't touch docker; assume Postgres is already up.
#
# Exit codes: 0 = success, 1 = user aborted, 2 = infra check failed,
#   3 = migration failed, 4 = sanity run failed.

set -euo pipefail

# ─── Locate repo root ────────────────────────────────────────────────────────
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$REPO_ROOT"

# ─── Flag parsing ────────────────────────────────────────────────────────────
NON_INTERACTIVE=0
SKIP_SANITY=0
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --non-interactive) NON_INTERACTIVE=1 ;;
    --skip-sanity-run) SKIP_SANITY=1 ;;
    --dry-run)         DRY_RUN=1 ;;
    -h|--help)
      sed -n '2,30p' "$0"
      exit 0
      ;;
    *)
      echo "unknown flag: $arg" >&2
      exit 1
      ;;
  esac
done

# In CI / non-TTY, default to non-interactive
if [[ ! -t 0 ]]; then NON_INTERACTIVE=1; fi

# ─── Logging helpers ─────────────────────────────────────────────────────────
BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; GRN=$'\033[32m'
YEL=$'\033[33m'; CYA=$'\033[36m'; RST=$'\033[0m'
step()  { echo "${CYA}${BOLD}▸ $*${RST}"; }
ok()    { echo "  ${GRN}✓${RST} $*"; }
warn()  { echo "  ${YEL}!${RST} $*" >&2; }
fail()  { echo "  ${RED}✗${RST} $*" >&2; }
prompt_yes() {
  if [[ $NON_INTERACTIVE -eq 1 ]]; then
    warn "non-interactive mode: assuming 'no' for: $1"
    return 1
  fi
  read -r -p "  ? $1 [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]]
}
run_or_print() {
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  ${DIM}[dry-run]${RST} $*"
  else
    eval "$@"
  fi
}

# ─── 1. Port selection ───────────────────────────────────────────────────────
step "1/5  Select Postgres host port"

port_holder_container() {
  # Return container name bound to the given host port, or empty.
  docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | \
    awk -v p="$1" '$0 ~ ":"p"->" {print $1; exit}'
}

port_free() {
  ! nc -z 127.0.0.1 "$1" 2>/dev/null
}

CHOSEN_PORT=""
if [[ -n "${CE_BOOTSTRAP_PORT:-}" ]]; then
  CHOSEN_PORT="$CE_BOOTSTRAP_PORT"
  ok "using CE_BOOTSTRAP_PORT=$CHOSEN_PORT (env override)"
else
  HOLDER="$(port_holder_container 5432 || true)"
  if [[ -z "$HOLDER" ]]; then
    CHOSEN_PORT=5432
    ok "port 5432 is free — using it"
  elif [[ "$HOLDER" == ce-agents-* ]]; then
    CHOSEN_PORT=5432
    ok "port 5432 already held by ce-agents container ($HOLDER) — using it"
  else
    warn "port 5432 is held by '$HOLDER' (not ce-agents)"
    for cand in 5434 5435 5436 5437 5438 5439 5440; do
      if port_free "$cand"; then
        CHOSEN_PORT="$cand"
        ok "next free port: $CHOSEN_PORT"
        break
      fi
    done
    if [[ -z "$CHOSEN_PORT" ]]; then
      fail "no free port in 5434..5440"
      exit 2
    fi
  fi
fi

# Write .env.local so downstream processes (alembic, CLI runs) can pick it up.
# We do NOT edit .env itself — it may be shared/committed.
if [[ "$CHOSEN_PORT" != "5432" ]]; then
  ENVLOCAL="$REPO_ROOT/.env.local"
  DB_URL="postgresql+asyncpg://ce:ce_local@localhost:$CHOSEN_PORT/ce_platform"
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  ${DIM}[dry-run]${RST} would write DATABASE_URL=$DB_URL to $ENVLOCAL"
  else
    {
      echo "# Written by scripts/dev-bootstrap.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)"
      echo "DATABASE_URL=$DB_URL"
      echo "POSTGRES_HOST=localhost"
      echo "POSTGRES_PORT=$CHOSEN_PORT"
    } > "$ENVLOCAL"
    ok "wrote $ENVLOCAL (DATABASE_URL overrides .env for non-5432 port)"
  fi
fi

# ─── 2. Start + verify Postgres ──────────────────────────────────────────────
step "2/5  Ensure ce-agents Postgres is running on $CHOSEN_PORT"

if [[ "${CE_SKIP_CONTAINER:-0}" == "1" ]]; then
  ok "CE_SKIP_CONTAINER=1: skipping docker. Assuming Postgres is up."
else
  if [[ "$CHOSEN_PORT" != "5432" ]]; then
    warn "non-5432 port chosen — docker compose as-written publishes to 5432."
    warn "start your ce-agents-postgres manually on $CHOSEN_PORT, or set CE_SKIP_CONTAINER=1 and run a separate container."
    warn "skipping docker-compose start for this run. ${BOLD}Bring Postgres up yourself on port $CHOSEN_PORT before proceeding.${RST}"
  else
    if ! docker ps --format '{{.Names}}' | grep -q '^ce-agents-postgres'; then
      if docker ps -a --format '{{.Names}}' | grep -q '^ce-agents-postgres'; then
        warn "ce-agents-postgres container exists but is stopped"
        if prompt_yes "start ce-agents-postgres?"; then
          run_or_print "docker compose -f '$REPO_ROOT/docker-compose.yml' up -d postgres"
          ok "started ce-agents-postgres"
        else
          fail "user declined — aborting"
          exit 1
        fi
      else
        run_or_print "docker compose -f '$REPO_ROOT/docker-compose.yml' up -d postgres"
        ok "created + started ce-agents-postgres"
      fi
    else
      ok "ce-agents-postgres already running"
    fi
  fi
fi

# Hard-check DB identity before we do anything destructive (like alembic upgrade).
CONTAINER_ON_PORT="$(port_holder_container "$CHOSEN_PORT" || true)"
if [[ -z "$CONTAINER_ON_PORT" ]] && [[ $DRY_RUN -eq 0 ]]; then
  fail "no container bound to port $CHOSEN_PORT after start attempt"
  exit 2
fi
if [[ -n "$CONTAINER_ON_PORT" ]]; then
  DB_NAME="$(docker exec "$CONTAINER_ON_PORT" printenv POSTGRES_DB 2>/dev/null || echo "")"
  DB_USER="$(docker exec "$CONTAINER_ON_PORT" printenv POSTGRES_USER 2>/dev/null || echo "")"
  if [[ "$DB_NAME" != "ce_platform" ]] || [[ "$DB_USER" != "ce" ]]; then
    fail "container '$CONTAINER_ON_PORT' on port $CHOSEN_PORT has POSTGRES_DB=$DB_NAME, POSTGRES_USER=$DB_USER — refusing to run migrations against it"
    fail "expected POSTGRES_DB=ce_platform POSTGRES_USER=ce"
    exit 2
  fi
  ok "port $CHOSEN_PORT: container=$CONTAINER_ON_PORT db=$DB_NAME user=$DB_USER (matches)"
fi

# ─── 3. Editable installs (order matters) ────────────────────────────────────
step "3/5  Install ce-shared, ce-db, ce-graph editable into each venv"

VENVS=(
  "$REPO_ROOT/CE - Multi-Agent Orchestration/venv"
  "$REPO_ROOT/CE - Agent Builder/venv"
  "$REPO_ROOT/CE - Evals/venv"
)
EDITABLES=(
  "$REPO_ROOT/ce-shared"
  "$REPO_ROOT/ce-db"
  "$REPO_ROOT/ce-graph"
)

for VENV in "${VENVS[@]}"; do
  if [[ ! -d "$VENV" ]]; then
    warn "venv not found: $VENV (skipping)"
    continue
  fi
  echo "  ${DIM}→ $VENV${RST}"
  # shellcheck disable=SC1091
  if [[ $DRY_RUN -eq 0 ]]; then source "$VENV/bin/activate"; fi
  for EDIT in "${EDITABLES[@]}"; do
    if [[ ! -d "$EDIT" ]]; then
      warn "skip missing: $EDIT"
      continue
    fi
    run_or_print "pip install --quiet -e '$EDIT'"
  done
  if [[ $DRY_RUN -eq 0 ]]; then deactivate 2>/dev/null || true; fi
  ok "installs done for $(basename "$(dirname "$VENV")")"
done

# ─── 4. Alembic upgrade head ─────────────────────────────────────────────────
step "4/5  Alembic upgrade head"

# Alembic needs a reachable DATABASE_URL pointed at the chosen port. If we
# wrote .env.local, source it. Otherwise rely on .env at the repo root.
ALEMBIC_DB_URL=""
if [[ "$CHOSEN_PORT" != "5432" ]]; then
  ALEMBIC_DB_URL="postgresql+psycopg2://ce:ce_local@localhost:$CHOSEN_PORT/ce_platform"
fi

pushd "$REPO_ROOT/ce-db" > /dev/null
if [[ -d "$REPO_ROOT/CE - Multi-Agent Orchestration/venv" ]] && [[ $DRY_RUN -eq 0 ]]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/CE - Multi-Agent Orchestration/venv/bin/activate"
fi
if [[ -n "$ALEMBIC_DB_URL" ]]; then
  run_or_print "SQLALCHEMY_URL='$ALEMBIC_DB_URL' alembic -x db_url='$ALEMBIC_DB_URL' upgrade head"
else
  run_or_print "alembic upgrade head"
fi
if [[ $DRY_RUN -eq 0 ]]; then
  CURRENT_REV="$(alembic current 2>/dev/null | grep -oE '[0-9]{3}[a-z_]*' | head -1 || echo "unknown")"
  ok "alembic revision: $CURRENT_REV"
  deactivate 2>/dev/null || true
fi
popd > /dev/null

# ─── 5. Sanity round-trip ────────────────────────────────────────────────────
step "5/5  Sanity run: P53 in research mode, confirm Postgres round-trip"

if [[ $SKIP_SANITY -eq 1 ]]; then
  warn "--skip-sanity-run: not running the round-trip"
else
  SANITY_VENV="$REPO_ROOT/CE - Multi-Agent Orchestration/venv"
  if [[ ! -d "$SANITY_VENV" ]]; then
    warn "Orchestration venv not found — skipping sanity run"
  elif [[ $DRY_RUN -eq 1 ]]; then
    echo "  ${DIM}[dry-run]${RST} would run P53 research-mode smoke + Postgres SELECT"
  else
    # shellcheck disable=SC1091
    source "$SANITY_VENV/bin/activate"
    pushd "$REPO_ROOT/CE - Multi-Agent Orchestration" > /dev/null
    # Research mode: no Anthropic API calls, instantaneous.
    export AGENT_MODE=research
    export CE_QUIET=1
    if python -m protocols.p53_contract_net.run -q "dev-bootstrap sanity" -a ceo cfo --mode research > /tmp/dev-bootstrap-sanity.log 2>&1; then
      ok "sanity run completed"
    else
      fail "sanity run errored — see /tmp/dev-bootstrap-sanity.log"
      popd > /dev/null; deactivate 2>/dev/null || true
      exit 4
    fi
    unset AGENT_MODE CE_QUIET
    popd > /dev/null
    deactivate 2>/dev/null || true

    # Read back from Postgres to prove the round-trip
    if [[ -n "$CONTAINER_ON_PORT" ]]; then
      RUNS_COUNT="$(docker exec "$CONTAINER_ON_PORT" psql -U ce -d ce_platform -tAc "SELECT COUNT(*) FROM runs WHERE protocol_key='p53_contract_net';" 2>/dev/null || echo "?")"
      if [[ "$RUNS_COUNT" =~ ^[0-9]+$ ]] && [[ "$RUNS_COUNT" -gt 0 ]]; then
        ok "runs table has $RUNS_COUNT p53_contract_net row(s) — round-trip verified"
      else
        warn "runs table row-count check returned: $RUNS_COUNT (sanity run may not have persisted; check logs)"
      fi
    fi
  fi
fi

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "${BOLD}Bootstrap summary${RST}"
echo "  port:             $CHOSEN_PORT"
echo "  container:        ${CONTAINER_ON_PORT:-(none)}"
echo "  env override:     ${ENVLOCAL:-(none — using repo-root .env)}"
echo "  editable installs: ce-shared, ce-db, ce-graph into 3 venvs"
echo "  alembic:          ${CURRENT_REV:-(not verified)}"
echo ""
echo "${GRN}${BOLD}✓ Ready.${RST} Run: ${DIM}cd 'CE - Multi-Agent Orchestration' && source venv/bin/activate && python -m protocols.p53_contract_net.run -q 'hello' -a ceo --strict${RST}"
