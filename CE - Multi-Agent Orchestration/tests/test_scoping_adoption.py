"""Scoping adoption compliance test.

Tracks the debt of retrofitting `scoped_prompt` (or the older
`filter_context_for_agent` / `build_context_blocks`) across the 48+
existing protocols. Every retrofit lowers the "unretrofitted" count and
drives the progressive-disclosure grade toward A.

This test is DESIGNED TO FAIL LOUDLY if the adoption count regresses
without also lowering the ratchet. Bumping the ratchet is a deliberate
commitment: "N protocols now adopt scoping — do not slip below N."
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Ratchets — bump these upward as retrofits land.
# ---------------------------------------------------------------------------

# Number of protocol orchestrators that call any scoping primitive:
#   `scoped_prompt`, `filter_context_for_agent`, `build_context_blocks`,
#   `format_results_for_synthesis` (which layers per-worker context)
MIN_ADOPTING_PROTOCOLS = 5

# Names known to adopt scoping today. Add a name here after retrofitting
# to bump the ratchet. Reject any test that removes without justification.
KNOWN_ADOPTERS = frozenset({
    "p04_multi_round_debate",
    "p05_constraint_negotiation",
    "p17_red_blue_white",
    "p48_black_swan_detection",
    "p53_stigmergy",
})


PROTOCOLS_DIR = Path(__file__).resolve().parent.parent / "protocols"

SCOPING_MARKERS = (
    "scoped_prompt",
    "filter_context_for_agent",
    "build_context_blocks",
    "format_results_for_synthesis",
)


def _protocol_dirs() -> list[Path]:
    return sorted(
        p for p in PROTOCOLS_DIR.iterdir()
        if p.is_dir()
        and p.name.startswith("p")
        and not p.name.startswith("_")
        and (p / "orchestrator.py").exists()
    )


def _adopters() -> set[str]:
    adopters: set[str] = set()
    for protocol_dir in _protocol_dirs():
        orchestrator = (protocol_dir / "orchestrator.py").read_text()
        prompts_file = protocol_dir / "prompts.py"
        combined = orchestrator + (prompts_file.read_text() if prompts_file.exists() else "")
        if any(marker in combined for marker in SCOPING_MARKERS):
            adopters.add(protocol_dir.name)
    return adopters


def test_scoping_adoption_meets_ratchet() -> None:
    adopters = _adopters()
    assert len(adopters) >= MIN_ADOPTING_PROTOCOLS, (
        f"Scoping adoption regressed. Expected at least {MIN_ADOPTING_PROTOCOLS} "
        f"protocols using scoping primitives, found {len(adopters)}: "
        f"{sorted(adopters)}"
    )


def test_known_adopters_still_adopt() -> None:
    adopters = _adopters()
    dropped = KNOWN_ADOPTERS - adopters
    assert not dropped, (
        f"Protocol(s) dropped scoping adoption without updating KNOWN_ADOPTERS: {sorted(dropped)}"
    )


@pytest.mark.parametrize("name", sorted(KNOWN_ADOPTERS))
def test_named_adopter_imports_a_scoping_primitive(name: str) -> None:
    orchestrator = (PROTOCOLS_DIR / name / "orchestrator.py").read_text()
    assert any(marker in orchestrator for marker in SCOPING_MARKERS), (
        f"{name} is in KNOWN_ADOPTERS but its orchestrator.py doesn't reference "
        f"any of {SCOPING_MARKERS}"
    )
