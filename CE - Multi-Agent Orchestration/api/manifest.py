"""Protocol manifest generator — scans protocols/ for capability.yaml metadata."""

from __future__ import annotations

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

        protocols.append({
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
            "has_stage_manifest": bool(cap.get("stages")),
        })

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
