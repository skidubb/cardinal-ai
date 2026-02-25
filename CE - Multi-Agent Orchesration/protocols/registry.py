"""Protocol Capability Card registry.

Discovers capability.yaml files across all protocol directories and provides
dynamic routing prompt generation for P0a.
"""

from __future__ import annotations

import functools
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


PROTOCOLS_DIR = Path(__file__).resolve().parent


@dataclass
class ProtocolCapability:
    protocol_id: str
    name: str
    category: str
    problem_types: list[str] = field(default_factory=list)
    cost_tier: str = "medium"
    min_agents: int = 2
    max_agents: int | None = None
    supports_rounds: bool = False
    description: str = ""
    when_to_use: str = ""
    when_not_to_use: str = ""


def discover_protocols(protocols_dir: Path | None = None) -> list[ProtocolCapability]:
    """Scan protocols/p*/capability.yaml and return all capability cards.

    Results are cached when using the default protocols_dir.
    """
    if protocols_dir is None:
        return _discover_protocols_cached()
    return _discover_protocols_uncached(protocols_dir)


@functools.lru_cache(maxsize=1)
def _discover_protocols_cached() -> list[ProtocolCapability]:
    return _discover_protocols_uncached(PROTOCOLS_DIR)


def _discover_protocols_uncached(root: Path) -> list[ProtocolCapability]:
    """Scan protocols/p*/capability.yaml and return all capability cards."""
    cards: list[ProtocolCapability] = []

    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("p"):
            continue
        yaml_path = entry / "capability.yaml"
        if not yaml_path.exists():
            continue
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        if not data:
            continue
        cards.append(ProtocolCapability(
            protocol_id=data.get("protocol_id", entry.name),
            name=data.get("name", entry.name),
            category=data.get("category", "Unknown"),
            problem_types=data.get("problem_types", []),
            cost_tier=data.get("cost_tier", "medium"),
            min_agents=data.get("min_agents", 2),
            max_agents=data.get("max_agents"),
            supports_rounds=data.get("supports_rounds", False),
            description=data.get("description", ""),
            when_to_use=data.get("when_to_use", ""),
            when_not_to_use=data.get("when_not_to_use", ""),
        ))

    return cards


def build_routing_prompt_section(cards: list[ProtocolCapability] | None = None) -> str:
    """Generate the 'Protocol mapping' and 'Cost tiers' blocks for P0a routing."""
    if cards is None:
        cards = discover_protocols()

    # Group by problem type
    problem_map: dict[str, list[str]] = {}
    for card in cards:
        for pt in card.problem_types:
            problem_map.setdefault(pt, []).append(f"{card.protocol_id} {card.name}")

    # Group by cost tier
    cost_map: dict[str, list[str]] = {"low": [], "medium": [], "high": []}
    for card in cards:
        tier = card.cost_tier
        cost_map.setdefault(tier, []).append(f"{card.protocol_id}")

    # Build protocol mapping section
    lines = ["Protocol mapping:"]
    for problem_type, protocols in sorted(problem_map.items()):
        lines.append(f"- {problem_type}: {', '.join(protocols)}")

    lines.append("")
    lines.append("Cost tiers:")
    for tier in ("low", "medium", "high"):
        protocols = cost_map.get(tier, [])
        if protocols:
            lines.append(f"- {tier}: {', '.join(sorted(protocols))}")

    return "\n".join(lines)
