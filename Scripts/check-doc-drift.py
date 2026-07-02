#!/usr/bin/env python3
"""Doc-drift checker — verifies that counts stated in docs match the code.

Ground truth is DERIVED, never hand-written:
  protocols   -> count of  CE - Multi-Agent Orchestration/protocols/*/capability.yaml
  agents      -> len(BUILTIN_AGENTS)          (import; skipped if deps missing)
  tool schemas-> len(ALL_TOOL_SCHEMAS)        (import; skipped if deps missing)
  role prompts-> len(_ROLE_PROMPTS)           (import; skipped if deps missing)
  role map    -> len(ROLE_TOOL_MAP)           (import; skipped if deps missing)

Usage:
  python scripts/check-doc-drift.py            # full check (imports where possible)
  python scripts/check-doc-drift.py --fs-only  # filesystem-derived checks only (fast; hook-safe)
  python scripts/check-doc-drift.py --quiet    # print nothing unless drift found

Exit codes: 0 clean, 1 drift found. Skipped checks (missing deps) never fail.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAO = ROOT / "CE - Multi-Agent Orchestration"
AB_SRC = ROOT / "CE - Agent Builder" / "src"

DOC_FILES = [
    ROOT / "CLAUDE.md",
    ROOT / "README.md",
    MAO / "CLAUDE.md",
    MAO / "README.md",
    ROOT / "CE - Agent Builder" / ".claude" / "CLAUDE.md",
    ROOT / ".planning" / "PROJECT.md",
]

# claim-pattern -> ground-truth key
CLAIM_PATTERNS: list[tuple[str, str]] = [
    (r"(\d+)\s+(?:multi-agent\s+)?(?:implemented\s+)?(?:coordination\s+)?protocols?\b", "protocols"),
    (r"##\s+(\d+)\s+Protocols", "protocols"),
    (r"(\d+)-agent registry", "agents"),
    (r"(\d+)\s+agents\s+across", "agents"),
    (r"(\d+)\s+tool schemas", "tool_schemas"),
    (r"(\d+)\s+role-specific system prompts", "role_prompts"),
    (r"tool mappings for (\d+) roles", "role_map"),
]

# lines matching these are historical/phase notes, not live claims
IGNORE_LINE = re.compile(r"consolidat|previously|superseded|Phase \d|v1\.\d", re.IGNORECASE)


def derive_truth(fs_only: bool) -> dict[str, int | None]:
    truth: dict[str, int | None] = {
        "protocols": len(list((MAO / "protocols").glob("*/capability.yaml"))),
        "agents": None,
        "tool_schemas": None,
        "role_prompts": None,
        "role_map": None,
    }
    if fs_only:
        return truth

    sys.path.insert(0, str(MAO))
    sys.path.insert(0, str(AB_SRC))
    try:
        from protocols.agents import BUILTIN_AGENTS  # type: ignore
        truth["agents"] = len(BUILTIN_AGENTS)
    except Exception as exc:  # noqa: BLE001 — any import failure just skips the check
        print(f"  (skip agents check — cannot import protocols.agents: {exc})", file=sys.stderr)
    try:
        from csuite.tools.schemas import ALL_TOOL_SCHEMAS  # type: ignore
        truth["tool_schemas"] = len(ALL_TOOL_SCHEMAS)
        from csuite.tools.registry import ROLE_TOOL_MAP  # type: ignore
        truth["role_map"] = len(ROLE_TOOL_MAP)
        from csuite.agents.sdk_agent import _ROLE_PROMPTS  # type: ignore
        truth["role_prompts"] = len(_ROLE_PROMPTS)
    except Exception as exc:  # noqa: BLE001
        print(f"  (skip csuite checks — cannot import csuite: {exc})", file=sys.stderr)
    return truth


def main() -> int:
    fs_only = "--fs-only" in sys.argv
    quiet = "--quiet" in sys.argv
    truth = derive_truth(fs_only)
    failures: list[str] = []

    for doc in DOC_FILES:
        if not doc.exists():
            failures.append(f"{doc.relative_to(ROOT)}: file missing")
            continue
        for lineno, line in enumerate(doc.read_text().splitlines(), 1):
            if IGNORE_LINE.search(line):
                continue
            for pattern, key in CLAIM_PATTERNS:
                for m in re.finditer(pattern, line):
                    expected = truth[key]
                    if expected is None:
                        continue
                    claimed = int(m.group(1))
                    if claimed != expected:
                        failures.append(
                            f"{doc.relative_to(ROOT)}:{lineno}: claims {claimed} {key}, "
                            f"actual is {expected}  |  {line.strip()[:90]}"
                        )

    if failures:
        print("DOC DRIFT DETECTED:")
        for f in failures:
            print(f"  {f}")
        return 1
    if not quiet:
        checked = {k: v for k, v in truth.items() if v is not None}
        print(f"doc-drift: clean ({', '.join(f'{k}={v}' for k, v in checked.items())})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
