"""Capability resolver — maps P0a recommendations to executable protocol runs.

Reads capability.yaml for each protocol to enforce safety rails:
- min_agents / max_agents: clamp agent list
- cost_tier: block protocols above ceiling
- allowlist: only route to well-tested protocols

Pure functions — no I/O beyond reading YAML files on disk.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


PROTOCOLS_DIR = Path(__file__).resolve().parent.parent


# Protocols v1 routes to. Well-tested, covering diverse interaction patterns.
# Expand as eval data justifies.
DEFAULT_ALLOWLIST: frozenset[str] = frozenset(
    {
        "p03_parallel_synthesis",
        "p04_multi_round_debate",
        "p06_triz",
        "p16_ach",
        "p17_red_blue_white",
        "p18_delphi_method",
        "p22_sequential_pipeline",
        "p23_cynefin_probe",
        "p32_tetlock_forecast",
        "p38_klein_premortem",
    }
)

# Sane default if user passes no agents. Three generalists that never fail to load.
DEFAULT_AGENTS: tuple[str, ...] = ("ceo", "cfo", "cto")

# Cost tier ordering (lower index = cheaper).
_COST_ORDER = {"low": 0, "medium": 1, "high": 2}


class ResolveError(Exception):
    """Raised when a recommendation cannot be safely executed."""


@dataclass
class ResolveResult:
    """An executable plan derived from a router decision."""

    protocol_key: str
    protocol_id: str
    name: str
    cost_tier: str
    agent_keys: list[str]
    supports_rounds: bool
    adjustments: list[str] = field(default_factory=list)


@functools.lru_cache(maxsize=1)
def _load_manifest() -> dict[str, dict[str, Any]]:
    """Return {protocol_key -> capability dict}. Cached across calls."""
    out: dict[str, dict[str, Any]] = {}
    for entry in sorted(PROTOCOLS_DIR.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("p"):
            continue
        if entry.name.startswith("__"):
            continue
        yaml_path = entry / "capability.yaml"
        if not yaml_path.exists():
            continue
        with open(yaml_path) as f:
            data = yaml.safe_load(f) or {}
        out[entry.name] = data
    return out


def _protocol_id_to_key_map() -> dict[str, str]:
    """Return {'P4' -> 'p04_multi_round_debate', ...}.

    P0a emits protocol_id (e.g., 'P4'); executor needs the dir key.
    """
    manifest = _load_manifest()
    out: dict[str, str] = {}
    for key, cap in manifest.items():
        pid = (cap.get("protocol_id") or "").strip()
        if pid:
            out[pid] = key
    return out


class Resolver:
    """Translates P0a output into a safely-executable plan."""

    def __init__(
        self,
        *,
        allowlist: frozenset[str] | None = None,
        max_cost_tier: str = "medium",
        default_agents: tuple[str, ...] = DEFAULT_AGENTS,
    ) -> None:
        self.allowlist = allowlist if allowlist is not None else DEFAULT_ALLOWLIST
        self.max_cost_tier = max_cost_tier
        self.default_agents = default_agents

    def resolve(
        self,
        *,
        recommended_protocol_id: str,
        alternatives: list[tuple[str, str]],
        requested_agents: list[str] | None,
    ) -> ResolveResult:
        """Map a recommendation to an executable plan.

        alternatives: list of (protocol_id, name) tuples, tried in order if primary fails.
        """
        id_map = _protocol_id_to_key_map()
        manifest = _load_manifest()
        adjustments: list[str] = []

        candidates = [recommended_protocol_id, *(pid for pid, _ in alternatives)]

        for pid in candidates:
            key = id_map.get(pid)
            if key is None:
                adjustments.append(f"{pid} unknown — trying next")
                continue
            if key not in self.allowlist:
                adjustments.append(f"{pid} not in allowlist — trying next")
                continue
            cap = manifest.get(key, {})
            if not self._cost_ok(cap.get("cost_tier", "medium")):
                adjustments.append(
                    f"{pid} cost_tier={cap.get('cost_tier')} exceeds max={self.max_cost_tier} — trying next"
                )
                continue

            agents, agent_adj = self._fit_agents(cap, requested_agents)
            adjustments.extend(agent_adj)

            return ResolveResult(
                protocol_key=key,
                protocol_id=pid,
                name=cap.get("name", key),
                cost_tier=cap.get("cost_tier", "medium"),
                agent_keys=agents,
                supports_rounds=bool(cap.get("supports_rounds", False)),
                adjustments=adjustments,
            )

        raise ResolveError(
            f"No candidate protocol was routable. Tried {candidates}. "
            f"Adjustments: {adjustments}"
        )

    def _cost_ok(self, tier: str) -> bool:
        t = _COST_ORDER.get(tier, 1)
        m = _COST_ORDER.get(self.max_cost_tier, 1)
        return t <= m

    def _fit_agents(
        self,
        cap: dict[str, Any],
        requested: list[str] | None,
    ) -> tuple[list[str], list[str]]:
        """Return (final_agents, adjustment_notes)."""
        notes: list[str] = []
        min_a = int(cap.get("min_agents") or 1)
        max_a = cap.get("max_agents")  # may be None = no cap

        agents = list(requested) if requested else list(self.default_agents)
        if not requested:
            notes.append(f"no agents provided — using defaults {list(self.default_agents)}")

        if len(agents) < min_a:
            needed = min_a - len(agents)
            backfill = [a for a in self.default_agents if a not in agents][:needed]
            agents.extend(backfill)
            notes.append(f"backfilled {needed} agent(s) to meet min_agents={min_a}")

        if max_a is not None and len(agents) > int(max_a):
            agents = agents[: int(max_a)]
            notes.append(f"clamped to max_agents={max_a}")

        return agents, notes


def clear_cache() -> None:
    """Clear the manifest cache (use in tests)."""
    _load_manifest.cache_clear()
