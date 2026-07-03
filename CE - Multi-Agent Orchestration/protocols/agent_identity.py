"""Bridge between the two agent registries — kill prompt drift.

The Cardinal Element monorepo holds agent identity in two places:

1. **Agent Builder** — `csuite.prompts.*_prompt.CEO_SYSTEM_PROMPT`
   Fat (100-300 line) prompts used by `SdkAgent`. This is the identity that
   actually runs when a protocol calls `agent.chat()` in production mode.

2. **Orchestration** — `protocols.agents.BUILTIN_AGENTS[key]["system_prompt"]`
   Thin (1-4 sentence) prompts used when protocols display an agent, quote
   its role in a synthesis prompt, or run in research mode.

Historically these could drift without anyone noticing because `AgentBridge`
delegates `chat()` to `SdkAgent` (fat) while exposing `system_prompt` (thin)
to protocol consumers. This module surfaces the divergence:

- `get_fat_prompt(key)` — lazily imports and returns the fat prompt if
  Agent Builder is installed, else None.
- `get_thin_prompt(key)` — the display-tier prompt from `protocols.agents`.
- `identity_check(key)` — verifies the fat and thin openers agree on the
  role name (first sentence). Returns `IdentityCheck` with diagnostics.
- `audit_identities()` — runs `identity_check` across every C-Suite key
  and returns a list of mismatches. Used by tests to fail loudly on drift.

Best-effort: if Agent Builder isn't importable in this environment (e.g.
research mode, headless CI), the fat side returns None and the audit
reports "fat_unavailable" rather than failing.
"""

from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from typing import Any


# The 7 C-Suite executives that have both thin and fat definitions.
CSUITE_KEYS: tuple[str, ...] = ("ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro")

# Mapping from agent key → fat prompt import location.
_FAT_PROMPT_IMPORTS: dict[str, tuple[str, str]] = {
    "ceo": ("csuite.prompts.ceo_prompt", "CEO_SYSTEM_PROMPT"),
    "cfo": ("csuite.prompts.cfo_prompt", "CFO_SYSTEM_PROMPT"),
    "cto": ("csuite.prompts.cto_prompt", "CTO_SYSTEM_PROMPT"),
    "cmo": ("csuite.prompts.cmo_prompt", "CMO_SYSTEM_PROMPT"),
    "coo": ("csuite.prompts.coo_prompt", "COO_SYSTEM_PROMPT"),
    "cpo": ("csuite.prompts.cpo_prompt", "CPO_SYSTEM_PROMPT"),
    "cro": ("csuite.prompts.cro_prompt", "CRO_SYSTEM_PROMPT"),
}

# Human-readable role name used to check that fat and thin agree on identity.
_EXPECTED_ROLE_NAMES: dict[str, str] = {
    "ceo": "Chief Executive Officer",
    "cfo": "Chief Financial Officer",
    "cto": "Chief Technology Officer",
    "cmo": "Chief Marketing Officer",
    "coo": "Chief Operating Officer",
    "cpo": "Chief Product Officer",
    "cro": "Chief Revenue Officer",
}


@dataclass(slots=True)
class IdentityCheck:
    """The outcome of a fat-vs-thin identity comparison for one agent key."""

    key: str
    thin_available: bool
    fat_available: bool
    thin_opener: str = ""
    fat_opener: str = ""
    role_name_match: bool = False
    verdict: str = ""

    @property
    def ok(self) -> bool:
        return self.thin_available and self.fat_available and self.role_name_match

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "thin_available": self.thin_available,
            "fat_available": self.fat_available,
            "thin_opener": self.thin_opener,
            "fat_opener": self.fat_opener,
            "role_name_match": self.role_name_match,
            "verdict": self.verdict,
        }


def get_fat_prompt(key: str) -> str | None:
    """Return the fat prompt for an agent key, or None if unavailable.

    Never raises. If the Agent Builder package isn't importable in this
    environment, returns None.
    """
    location = _FAT_PROMPT_IMPORTS.get(key.lower())
    if location is None:
        return None
    module_name, attr_name = location
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return None
    prompt = getattr(module, attr_name, None)
    return prompt if isinstance(prompt, str) and prompt.strip() else None


def get_thin_prompt(key: str) -> str | None:
    """Return the thin display prompt from `protocols.agents.BUILTIN_AGENTS`.

    Defensive against `protocols.agents` transitively failing to import in
    slim environments (e.g. no litellm, broken cryptography) — falls back
    to parsing just the executive dict from source. Never raises.
    """
    key = key.lower()
    try:
        from protocols.agents import BUILTIN_AGENTS

        entry = BUILTIN_AGENTS.get(key)
        if isinstance(entry, dict):
            prompt = entry.get("system_prompt")
            if isinstance(prompt, str) and prompt.strip():
                return prompt
    except BaseException:  # noqa: BLE001 — Rust panics from broken deps aren't Exceptions
        pass

    # Fallback: source-file scan for the EXECUTIVE_AGENTS dict.
    return _thin_prompt_from_source(key)


def _thin_prompt_from_source(key: str) -> str | None:
    """Extract a thin prompt by parsing protocols/agents.py without importing it."""
    import ast
    from pathlib import Path

    source_path = Path(__file__).with_name("agents.py")
    try:
        source = source_path.read_text()
    except OSError:
        return None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    # Collect every top-level assignment to a dict literal, then look for the key.
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for k_node, v_node in zip(node.value.keys, node.value.values):
            if not isinstance(k_node, ast.Constant) or not isinstance(k_node.value, str):
                continue
            if k_node.value.lower() != key:
                continue
            if not isinstance(v_node, ast.Dict):
                continue
            for inner_k, inner_v in zip(v_node.keys, v_node.values):
                if (
                    isinstance(inner_k, ast.Constant)
                    and inner_k.value == "system_prompt"
                    and isinstance(inner_v, ast.Constant)
                    and isinstance(inner_v.value, str)
                ):
                    return inner_v.value
    return None


def _first_sentence(text: str, max_chars: int = 160) -> str:
    text = text.strip()
    if not text:
        return ""
    # Take the first line or first sentence, whichever comes first.
    line = text.splitlines()[0].strip()
    match = re.search(r"[.!?]\s", line)
    opener = line[: match.end()] if match else line
    return opener[:max_chars].strip()


def identity_check(key: str) -> IdentityCheck:
    """Compare fat vs thin identity for one agent key. Never raises."""
    key = key.lower()
    thin = get_thin_prompt(key)
    fat = get_fat_prompt(key)
    expected_role = _EXPECTED_ROLE_NAMES.get(key, "")

    check = IdentityCheck(
        key=key,
        thin_available=thin is not None,
        fat_available=fat is not None,
        thin_opener=_first_sentence(thin or ""),
        fat_opener=_first_sentence(fat or ""),
    )

    if not check.thin_available:
        check.verdict = "thin_missing — no BUILTIN_AGENTS entry"
        return check
    if not check.fat_available:
        check.verdict = "fat_unavailable — Agent Builder not importable in this env"
        return check
    if not expected_role:
        check.verdict = "no_expected_role — key not in _EXPECTED_ROLE_NAMES"
        return check

    thin_has = expected_role.lower() in (thin or "").lower()
    fat_has = expected_role.lower() in (fat or "").lower()
    check.role_name_match = thin_has and fat_has
    if not thin_has:
        check.verdict = f"thin_missing_role — thin prompt does not mention '{expected_role}'"
    elif not fat_has:
        check.verdict = f"fat_missing_role — fat prompt does not mention '{expected_role}'"
    else:
        check.verdict = "ok"
    return check


def audit_identities(keys: tuple[str, ...] = CSUITE_KEYS) -> list[IdentityCheck]:
    """Run `identity_check` across the given keys (default: all C-Suite)."""
    return [identity_check(k) for k in keys]


def drift_report() -> str:
    """Human-readable drift audit. Used by the /audit-drift skill."""
    lines = ["Agent identity drift report", "=" * 40]
    for check in audit_identities():
        status = "OK " if check.ok else "!! "
        lines.append(f"{status}{check.key}: {check.verdict}")
        if check.thin_opener and check.fat_opener and not check.ok:
            lines.append(f"    thin: {check.thin_opener}")
            lines.append(f"    fat : {check.fat_opener}")
    return "\n".join(lines)
