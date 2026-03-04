"""Protocol manifest generator — scans protocols/ for capability.yaml metadata."""

from __future__ import annotations

from pathlib import Path

import yaml


PROTOCOLS_DIR = Path(__file__).resolve().parent.parent / "protocols"


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
        })

    return protocols
