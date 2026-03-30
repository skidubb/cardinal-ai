"""Diagnostic CLI for environment health across the CE-AGENTS monorepo.

Run with ``python -m ce_shared.env_check`` or ``python -m ce_shared`` to get
a Rich-formatted report showing:

- Which ``.env`` was loaded
- All registry keys grouped by project, with redacted values
- Warnings for stale per-project ``.env`` files
"""

from __future__ import annotations

import os
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

from ce_shared.env import KEY_REGISTRY, KeyMeta, find_and_load_dotenv

__all__ = ["check_stale_envs", "group_keys_by_project", "redact", "run_check"]

# ---------------------------------------------------------------------------
# Project display names
# ---------------------------------------------------------------------------

_PROJECT_LABELS: dict[str, str] = {
    "agent-builder": "Agent Builder",
    "orchestration": "Orchestration",
    "evals": "Evals",
    "docker": "Docker / Database",
}

# Stale .env paths relative to monorepo root
_STALE_ENV_DIRS = [
    "CE - Agent Builder",
    "CE - Multi-Agent Orchestration",
    "CE - Evals",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def redact(value: str) -> str:
    """Redact a secret value, keeping first 4 and last 4 characters."""
    if len(value) < 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


def check_stale_envs(root: Path) -> list[str]:
    """Return paths to stale per-project .env files that should have been removed."""
    stale: list[str] = []
    for dirname in _STALE_ENV_DIRS:
        env_path = root / dirname / ".env"
        if env_path.is_file():
            stale.append(str(env_path))
    return stale


def group_keys_by_project() -> dict[str, list[KeyMeta]]:
    """Group KEY_REGISTRY entries by project using ``required_by`` and ``category``.

    Keys with category ``"docker"`` go into a ``"docker"`` group regardless
    of their ``required_by`` list.  All other keys are filed under each
    project listed in ``required_by``.
    """
    groups: dict[str, list[KeyMeta]] = {}
    for meta in KEY_REGISTRY.values():
        if meta.category == "docker":
            groups.setdefault("docker", []).append(meta)
        else:
            for project in meta.required_by:
                groups.setdefault(project, []).append(meta)
    return groups


# ---------------------------------------------------------------------------
# Main report
# ---------------------------------------------------------------------------


def run_check() -> None:
    """Print a Rich-formatted environment health report."""
    console = Console()

    # 1. Load .env -----------------------------------------------------------
    env_path: Path | None = None
    try:
        env_path = find_and_load_dotenv()
    except EnvironmentError as exc:
        console.print(f"[bold red]Environment error:[/] {exc}")

    if env_path is not None:
        console.print(f"\n[bold]Loaded .env:[/] {env_path}")
    else:
        console.print("\n[bold yellow]No monorepo .env found.[/]")

    # 2. Build grouped tables ------------------------------------------------
    groups = group_keys_by_project()
    total_keys = 0
    set_keys = 0
    warnings = 0

    # Deterministic ordering
    order = ["agent-builder", "orchestration", "evals", "docker"]
    for project_key in order:
        keys = groups.get(project_key)
        if not keys:
            continue

        label = _PROJECT_LABELS.get(project_key, project_key)
        table = Table(title=label, show_header=True, header_style="bold cyan")
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_column("Status")
        table.add_column("Required")

        for meta in keys:
            total_keys += 1
            value = os.environ.get(meta.name)
            is_set = value is not None

            if is_set:
                set_keys += 1
                display_value = redact(value)  # type: ignore[arg-type]
                status = Text("SET", style="green")
            elif meta.required:
                display_value = "-"
                status = Text("MISSING", style="bold red")
                warnings += 1
            else:
                display_value = "-"
                status = Text("MISSING", style="yellow")

            req_text = Text("required", style="red") if meta.required else Text("optional", style="dim")
            table.add_row(meta.name, display_value, status, req_text)

        console.print()
        console.print(table)

    # 3. Stale file warnings -------------------------------------------------
    # Try to determine monorepo root from the loaded .env path
    root: Path | None = None
    if env_path is not None:
        root = env_path.parent
    else:
        # Fallback: walk up from CWD looking for ce-shared/
        cur = Path.cwd().resolve()
        for d in [cur, *cur.parents]:
            if (d / "ce-shared").is_dir():
                root = d
                break

    if root is not None:
        stale = check_stale_envs(root)
        if stale:
            console.print()
            for path in stale:
                console.print(f"[bold yellow]WARNING:[/] Stale .env found: {path}")
                console.print("  This file should be removed. The monorepo root .env is the single source.")
                warnings += 1

    # 4. Summary -------------------------------------------------------------
    console.print(f"\n[bold]Summary:[/] {set_keys}/{total_keys} keys set, {warnings} warning(s)\n")


if __name__ == "__main__":
    run_check()
