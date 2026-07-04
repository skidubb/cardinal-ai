"""Protocol manifest generator — scans protocols/ for capability.yaml metadata."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


PROTOCOLS_DIR = Path(__file__).resolve().parent.parent / "protocols"

# Cache — stages lookups happen on every run envelope build; read once.
_STAGES_CACHE: dict[str, list[dict]] = {}
_STAGES_LOADED = False


def _load_capability(protocol_dir: Path) -> dict | None:
    cap_file = protocol_dir / "capability.yaml"
    if not cap_file.exists():
        return None
    with open(cap_file) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Orchestration-pattern inference
# ---------------------------------------------------------------------------
# Keep in sync with cardinal-portal/src/components/run/orchestrationPattern.ts.
# Values: single_agent | sequence | parallel | hub_and_spoke | hybrid_matrix | decentralized.


def _slug(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")


def _stage_kind(stage: dict) -> str | None:
    return stage.get("kind") or stage.get("stage_type")


def _infer_pattern_from_stages(stages: list[dict], cap: dict) -> str:
    agent_stages = [s for s in stages if _stage_kind(s) == "agent"]
    synthesis_stages = [s for s in stages if _stage_kind(s) == "synthesis"]
    max_a = cap.get("max_agents")
    min_a = cap.get("min_agents") or 0

    # Router / dispatcher protocols (min=max=0): no agent fan-out.
    if max_a == 0 and min_a == 0:
        return "single_agent"
    # Explicit single-agent protocol (P01: min=max=1).
    if max_a == 1 and min_a <= 1:
        return "single_agent"

    if not agent_stages:
        return "sequence"

    # Decentralized: multiple agent stages, no synthesizer.
    if not synthesis_stages and len(agent_stages) > 1:
        return "decentralized"

    # Hybrid / matrix: an agent stage depends on a prior agent stage (revisit).
    def _resolve_dep(dep: str) -> dict | None:
        dep_slug = _slug(dep)
        if not dep_slug:
            return None
        for s in stages:
            if _slug(s.get("key")) == dep_slug or _slug(s.get("name")) == dep_slug:
                return s
        for s in stages:
            for candidate in (_slug(s.get("key")), _slug(s.get("name"))):
                if candidate and candidate.startswith(dep_slug + "_"):
                    return s
        return None

    if len(agent_stages) >= 2:
        for s in agent_stages:
            for dep in s.get("depends_on") or []:
                target = _resolve_dep(dep)
                if (
                    target is not None
                    and _stage_kind(target) == "agent"
                    and target is not s
                ):
                    return "hybrid_matrix"

    # Parallel: one agent stage + synthesis (canonical P3 shape).
    if len(agent_stages) == 1 and synthesis_stages:
        return "parallel"

    # Hub-and-spoke: multiple non-chained agent stages + synthesis.
    if len(agent_stages) >= 2 and synthesis_stages:
        return "hub_and_spoke"

    return "sequence"


def _infer_pattern_from_metadata(cap: dict) -> str:
    """Fallback when no YAML stages exist. Coarse signals only."""
    min_a = cap.get("min_agents") or 0
    max_a = cap.get("max_agents")
    supports_rounds = bool(cap.get("supports_rounds"))
    name = (cap.get("name") or "").lower()

    if max_a == 0 and min_a == 0:
        return "single_agent"
    if max_a == 1 and min_a <= 1:
        return "single_agent"
    if supports_rounds:
        return "hybrid_matrix"
    if any(k in name for k in ("sequential", "pipeline", "polya", "ooda", "walk")):
        return "sequence"
    if any(
        k in name
        for k in (
            "red",
            "troika",
            "ach",
            "competing hypotheses",
            "heard",
            "wicked",
            "min specs",
            "one two four",
            "1-2-4",
            "25/10",
            "crowd",
            "discovery action",
            "affinity",
            "crazy eights",
            "evaporation",
            "current reality",
            "premortem",
            "delphi",
        )
    ):
        return "hub_and_spoke"
    return "parallel"


def _infer_orchestration_pattern(cap: dict) -> str:
    # Category override: Decentralized Coordination (P53-P57) protocols are
    # pure tick schedulers and always report as decentralized regardless of
    # how their YAML stages happen to be factored.
    if (cap.get("category") or "").strip() == "Decentralized Coordination":
        return "decentralized"

    stages = cap.get("stages")
    if isinstance(stages, list) and stages:
        try:
            return _infer_pattern_from_stages(stages, cap)
        except Exception:  # noqa: BLE001 — pattern is best-effort metadata.
            pass
    return _infer_pattern_from_metadata(cap)


_DEFAULT_RECOMMENDED_AGENTS = ["ceo", "cfo", "cto"]


def _resolve_recommended_agents(cap: dict) -> list[str]:
    """Return curated agents from capability.yaml, or a sensible default.

    Single-agent protocols (max_agents=1) get [ceo] as a default — the
    [ceo, cfo, cto] fallback is only meaningful for multi-agent protocols.
    Router/dispatcher protocols (min=max=0) return an empty list.
    """
    declared = cap.get("recommended_agents")
    if declared:
        return list(declared)
    max_a = cap.get("max_agents")
    min_a = cap.get("min_agents") or 0
    if max_a == 0 and min_a == 0:
        return []
    if max_a == 1:
        return ["ceo"]
    return list(_DEFAULT_RECOMMENDED_AGENTS)


def _free_protocol_keys() -> frozenset[str]:
    """Protocols available on the free plan (lazy import avoids a cycle)."""
    from api.entitlements import FREE_PROTOCOL_KEYS

    return FREE_PROTOCOL_KEYS


def get_protocol_manifest() -> list[dict]:
    """Scan all protocol directories and return metadata list."""
    protocols = []
    for d in sorted(PROTOCOLS_DIR.iterdir()):
        if not d.is_dir() or not d.name.startswith("p"):
            continue
        # Skip non-protocol dirs like __pycache__
        if d.name.startswith("__"):
            continue

        cap = _load_capability(d)
        if cap is None:
            continue

        protocols.append(
            {
                "key": d.name,
                "protocol_id": cap.get("protocol_id", d.name),
                "name": cap.get("name", d.name),
                "category": cap.get("category", ""),
                "problem_types": cap.get("problem_types", []),
                "cost_tier": cap.get("cost_tier", ""),
                "min_agents": cap.get("min_agents", 1),
                "max_agents": cap.get("max_agents"),
                "supports_rounds": cap.get("supports_rounds", False),
                "description": cap.get("description", ""),
                "when_to_use": cap.get("when_to_use", ""),
                "when_not_to_use": cap.get("when_not_to_use", ""),
                "tools_enabled": cap.get("tools_enabled", True),
                "premium": d.name not in _free_protocol_keys(),
                "has_stage_manifest": bool(cap.get("stages")),
                "orchestration_pattern": _infer_orchestration_pattern(cap),
                "recommended_agents": _resolve_recommended_agents(cap),
            }
        )

    return protocols


def get_protocol_stages(protocol_key: str) -> list[dict]:
    """Return the declarative `stages:` list from a protocol's capability.yaml.

    Returns an empty list if the protocol has no manifest or no stages declared.
    Cached on first call.

    Each stage dict may contain:
        name: str                — human-readable stage name
        description: str         — what the stage does / produces
        implicit: bool           — true for prompt-embedded framing stages
        produces: str | list[str] — Result dataclass field(s) that hold output
        kind: "agent" | "mechanical" | "synthesis"
        required: bool           — default True; missing output → audit warning
        summary_role: str        — "primary_summary" | "structured_prelude" |
                                   "working_notes" | "ignore"
    """
    global _STAGES_LOADED
    if not _STAGES_LOADED:
        _load_all_stages()
    return _STAGES_CACHE.get(protocol_key, [])


def _load_all_stages() -> None:
    """Populate the stages cache from every capability.yaml once."""
    global _STAGES_LOADED
    for d in sorted(PROTOCOLS_DIR.iterdir()):
        if not d.is_dir() or not d.name.startswith("p") or d.name.startswith("__"):
            continue
        cap = _load_capability(d)
        if cap is None:
            continue
        stages = cap.get("stages")
        if isinstance(stages, list) and stages:
            _STAGES_CACHE[d.name] = stages
    _STAGES_LOADED = True


def invalidate_stages_cache() -> None:
    """Force re-read of capability.yaml files. Use in tests."""
    global _STAGES_LOADED
    _STAGES_CACHE.clear()
    _STAGES_LOADED = False
