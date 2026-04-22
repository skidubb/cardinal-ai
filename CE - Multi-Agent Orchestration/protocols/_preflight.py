"""One-time preflight banner for CLI protocol invocations.

Prints a short banner to stderr showing what external state a run will touch:
tenant slug, Postgres host, Langfuse on/off, AGENT_MODE, and CE_ALLOW_PROD.
Makes otherwise-invisible env configuration visible so devs notice when they're
about to write to production.

In ``strict`` mode (``--strict`` CLI flag, ``ENV=production``, or
``CE_PREFLIGHT_STRICT=1``), any FAIL check aborts the run with exit code 2.
In non-strict mode, FAILs print as warnings and the run continues.

Gating:
  * ``CE_SKIP_PREFLIGHT=1`` -> skip every check and the banner entirely
  * ``CE_QUIET=1`` -> skip the banner (checks still run if strict)
  * Not a TTY -> skip the banner unless ``CE_PREFLIGHT=1`` forces it on
  * Idempotent: prints at most once per Python process

Checks:
  1. Langfuse is active when the key is set (catches the silent-passthrough bug
     where ``@trace_protocol`` evaluates before ``.env`` is loaded).
  2. ``ce_db`` importable (catches venv without editable install).
  3. Postgres reachable in 2s (catches DB down, wrong port, bad credentials).
  4. Alembic at head (catches schema drift that would silently 500
     ``persist_run()``).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Literal

_PRINTED = False
_CheckStatus = Literal["ok", "warn", "fail", "skip"]
_CheckResult = tuple[_CheckStatus, str]

_HEAD_REVISION_EXPECTED = "004"  # Update when a new Alembic migration lands.


def _resolve_tenant() -> tuple[str, bool]:
    """Return (tenant_slug, allow_prod) mirroring persistence._default_tenant_slug."""
    allow_prod = os.environ.get("CE_ALLOW_PROD") == "1"
    if allow_prod:
        return "cardinal-element", True
    return os.environ.get("CE_DEV_TENANT") or "local-dev", False


def _resolve_strict(strict_flag: bool | None) -> bool:
    """Resolve strict mode: explicit flag > env > prod default."""
    if strict_flag is not None:
        return strict_flag
    if os.environ.get("CE_PREFLIGHT_STRICT") == "1":
        return True
    if os.environ.get("ENV", "").lower() == "production":
        return True
    return False


# ---------------------------------------------------------------------------
# Checks — each returns (status, message). Never raises.
# ---------------------------------------------------------------------------


def _check_langfuse() -> _CheckResult:
    key = os.environ.get("LANGFUSE_SECRET_KEY")
    if not key:
        return ("skip", "Langfuse: no key set (tracing disabled)")
    try:
        from protocols.langfuse_tracing import _langfuse_available, is_enabled
    except Exception as e:
        return ("fail", f"Langfuse: module import error — {type(e).__name__}: {e}")
    if not _langfuse_available or not is_enabled():
        return (
            "fail",
            "Langfuse: key is set but client never initialized. "
            "Likely .env was not loaded before langfuse_tracing import. "
            "Add find_and_load_dotenv() at the top of orchestrator.py.",
        )
    return ("ok", "Langfuse: client active, @trace_protocol will fire spans")


def _check_ce_db() -> _CheckResult:
    try:
        from ce_db import AgentOutput, Run, get_session  # noqa: F401
    except ImportError as e:
        return (
            "fail",
            f"ce_db: not importable ({e}). Run: pip install -e ../ce-db ../ce-shared",
        )
    except Exception as e:
        return ("fail", f"ce_db: import raised {type(e).__name__}: {e}")
    return ("ok", "ce_db: importable (Run, AgentOutput, get_session)")


def _check_postgres() -> _CheckResult:
    """Open a short-timeout connection and run SELECT 1."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return ("warn", "Postgres: DATABASE_URL not set — persistence will no-op")

    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    try:
        import psycopg2  # type: ignore[import-not-found]
    except ImportError:
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(sync_url, connect_args={"connect_timeout": 2})
            t0 = time.time()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            elapsed_ms = int((time.time() - t0) * 1000)
            return ("ok", f"Postgres: SELECT 1 ok ({elapsed_ms}ms) via SQLAlchemy")
        except Exception as e:
            return ("fail", f"Postgres: cannot connect — {type(e).__name__}: {e}")

    try:
        t0 = time.time()
        conn = psycopg2.connect(sync_url, connect_timeout=2)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        elapsed_ms = int((time.time() - t0) * 1000)
        return ("ok", f"Postgres: SELECT 1 ok ({elapsed_ms}ms)")
    except Exception as e:
        return ("fail", f"Postgres: cannot connect — {type(e).__name__}: {e}")


def _check_alembic() -> _CheckResult:
    """Query alembic_version and compare to the expected head revision.

    Uses the bundled ``_HEAD_REVISION_EXPECTED`` constant. Update that when a
    new migration is added. This avoids a runtime dependency on parsing
    the ce-db/alembic/versions/ directory at preflight time.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return ("warn", "Alembic: DATABASE_URL not set, cannot verify head")

    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(sync_url, connect_args={"connect_timeout": 2})
        try:
            with engine.connect() as conn:
                row = conn.execute(
                    text("SELECT version_num FROM alembic_version")
                ).fetchone()
        finally:
            engine.dispose()
    except Exception as e:
        msg = str(e).lower()
        if "does not exist" in msg or "undefinedtable" in msg:
            return (
                "fail",
                "Alembic: alembic_version table missing. Run: "
                "cd ce-db && alembic upgrade head",
            )
        return ("fail", f"Alembic: query failed — {type(e).__name__}: {e}")

    if row is None:
        return ("fail", "Alembic: alembic_version table exists but is empty")
    current = str(row[0])
    if current != _HEAD_REVISION_EXPECTED:
        return (
            "warn",
            f"Alembic: current={current}, expected={_HEAD_REVISION_EXPECTED}. "
            f"Run: cd ce-db && alembic upgrade head",
        )
    return ("ok", f"Alembic: at head ({current})")


# ---------------------------------------------------------------------------
# Banner assembly + print
# ---------------------------------------------------------------------------


def _run_checks() -> list[tuple[str, _CheckResult]]:
    """Run every check in order. Never raises."""
    checks: list[tuple[str, _CheckResult]] = []
    for name, fn in (
        ("langfuse", _check_langfuse),
        ("ce_db", _check_ce_db),
        ("postgres", _check_postgres),
        ("alembic", _check_alembic),
    ):
        try:
            checks.append((name, fn()))
        except Exception as e:
            checks.append(
                (name, ("fail", f"{name}: check raised {type(e).__name__}: {e}"))
            )
    return checks


def _format_status(status: _CheckStatus) -> str:
    return {
        "ok": "[ok]",
        "warn": "[!! ]",
        "fail": "[FAIL]",
        "skip": "[ -- ]",
    }[status]


def print_preflight(force: bool = False, strict: bool | None = None) -> None:
    """Print the preflight banner and run checks.

    Args:
        force: Print even when stderr isn't a TTY or ``CE_QUIET=1`` is set.
        strict: Override strict mode. If None, resolved from env (ENV=production,
            CE_PREFLIGHT_STRICT=1). Strict mode causes FAIL results to exit(2).

    In strict mode, a FAIL result exits before returning — callers should
    treat ``print_preflight()`` as "returns only on PASS or WARN."

    The banner prints at most once per process (idempotent via ``_PRINTED``),
    but strict-mode checks re-run on every call so an explicit
    ``print_preflight(strict=True)`` from a CLI main() can still abort even
    if the package's ``__init__.py`` already ran a non-strict preflight at
    import time (before ``.env`` was loaded).
    """
    global _PRINTED

    if os.environ.get("CE_SKIP_PREFLIGHT") == "1":
        return

    is_strict = _resolve_strict(strict)
    quiet = os.environ.get("CE_QUIET") == "1"
    is_tty = sys.stderr.isatty() if hasattr(sys.stderr, "isatty") else False
    banner_already_printed = _PRINTED and not force
    should_print_banner = (
        not banner_already_printed
        and (force or (not quiet and (is_tty or os.environ.get("CE_PREFLIGHT") == "1")))
    )

    # If the banner was already printed AND we're not strict, skip re-running
    # checks — they're expensive (DB round-trips) and we have nothing to do
    # with the results.
    if banner_already_printed and not is_strict:
        return

    checks = _run_checks()
    any_fail = any(result[0] == "fail" for _, result in checks)

    # Short-circuit: nothing to print, no strict fail → silent success
    if not should_print_banner and not (is_strict and any_fail):
        return

    tenant, allow_prod = _resolve_tenant()
    postgres_host = os.environ.get("POSTGRES_HOST") or "localhost (default)"
    langfuse_on = "ON" if os.environ.get("LANGFUSE_SECRET_KEY") else "off"
    mode = os.environ.get("AGENT_MODE", "production")

    bar = "─" * 72
    lines = [
        "",
        bar,
        f"  CE preflight  |  tenant={tenant}  postgres={postgres_host}",
        f"                |  langfuse={langfuse_on}  mode={mode}  strict={'on' if is_strict else 'off'}",
        bar,
    ]
    for name, (status, message) in checks:
        lines.append(f"  {_format_status(status)} {message}")
    if allow_prod:
        lines.append("  [!] CE_ALLOW_PROD=1 -- writes will land in PRODUCTION state")
    else:
        lines.append("  [ok] Safe mode: unauth'd writes scoped to isolated tenant")
    lines.append(bar)
    lines.append("")

    if should_print_banner:
        print("\n".join(lines), file=sys.stderr, flush=True)
        _PRINTED = True

    if is_strict and any_fail:
        if not should_print_banner:
            # Banner was suppressed but we're aborting — dump failures so the
            # user sees WHY the run died.
            print(
                "\n".join(
                    [
                        bar,
                        "  CE preflight FAILED (strict mode)",
                    ]
                    + [
                        f"  {_format_status(s)} {m}"
                        for _, (s, m) in checks
                        if s == "fail"
                    ]
                    + [bar]
                ),
                file=sys.stderr,
                flush=True,
            )
        sys.exit(2)
