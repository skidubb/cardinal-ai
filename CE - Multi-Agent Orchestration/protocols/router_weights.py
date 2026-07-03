"""Shared reader for P45 Whitehead weights, used by P0a to close the router→weights loop.

P45 (`p45_whitehead_weights`) writes performance records to `~/.coordination-lab/weights.json`
via `record(agent, protocol, problem_type, score)`. This module aggregates those records
along the (protocol, problem_type) axis so the router can bias its recommendation toward
historically better-performing protocols.

Best-effort: if the weights file is missing or malformed, all readers return empty results
and the router falls back to its LLM-only decision. Never raises.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


WEIGHTS_PATH = os.path.join(os.path.expanduser("~"), ".coordination-lab", "weights.json")

# A protocol needs at least this many recorded runs before we let it override the LLM.
MIN_SAMPLES_FOR_OVERRIDE = 5
# The mean score gap over the LLM's pick that justifies overriding it.
OVERRIDE_SCORE_MARGIN = 0.15


@dataclass(slots=True)
class ProtocolPerformance:
    protocol: str
    problem_type: str
    mean_score: float
    sample_count: int

    def as_dict(self) -> dict:
        return {
            "protocol": self.protocol,
            "problem_type": self.problem_type,
            "mean_score": round(self.mean_score, 3),
            "sample_count": self.sample_count,
        }


def _load_records() -> list[dict]:
    """Return the raw records list from the weights file. Never raises."""
    if not os.path.exists(WEIGHTS_PATH):
        return []
    try:
        with open(WEIGHTS_PATH) as f:
            data = json.load(f)
        records = data.get("records", [])
        return records if isinstance(records, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def performance_by_protocol(problem_type: str) -> dict[str, ProtocolPerformance]:
    """Aggregate all recorded scores for a given problem_type, keyed by protocol.

    Returns an empty dict when the weights file is absent or has no matching records —
    callers should treat that as "no signal, fall back to LLM decision".
    """
    scores: dict[str, list[float]] = {}
    for rec in _load_records():
        rec_type = str(rec.get("problem_type", "")).strip().lower()
        if rec_type != problem_type.strip().lower():
            continue
        proto = str(rec.get("protocol", "")).strip()
        if not proto:
            continue
        try:
            score = float(rec.get("score"))
        except (TypeError, ValueError):
            continue
        scores.setdefault(proto, []).append(score)

    return {
        proto: ProtocolPerformance(
            protocol=proto,
            problem_type=problem_type,
            mean_score=sum(vals) / len(vals),
            sample_count=len(vals),
        )
        for proto, vals in scores.items()
    }


def format_for_prompt(perf: dict[str, ProtocolPerformance], top_n: int = 8) -> str:
    """Render the historical performance as a compact prompt block.

    Returns an empty string when there's no signal — the caller can skip injection.
    """
    if not perf:
        return ""
    ranked = sorted(perf.values(), key=lambda p: p.mean_score, reverse=True)[:top_n]
    lines = ["Historical performance for this problem type (higher = better):"]
    for p in ranked:
        lines.append(
            f"  {p.protocol}: mean={round(p.mean_score, 2)}, n={p.sample_count}"
        )
    return "\n".join(lines)


def suggest_override(
    llm_choice: str,
    perf: dict[str, ProtocolPerformance],
    *,
    min_samples: int = MIN_SAMPLES_FOR_OVERRIDE,
    margin: float = OVERRIDE_SCORE_MARGIN,
) -> tuple[str | None, str | None]:
    """Decide whether historical data justifies overriding the LLM's recommended protocol.

    Returns (override_protocol, rationale). Both are None when the LLM pick stands.

    The override fires only when a well-sampled alternative beats the LLM choice by
    at least `margin`. If the LLM choice itself is unranked (no history), we do not
    override — insufficient signal to compare.
    """
    if not perf:
        return None, None
    llm_perf = perf.get(llm_choice)
    if llm_perf is None:
        return None, None

    best = max(perf.values(), key=lambda p: p.mean_score)
    if best.protocol == llm_choice:
        return None, None
    if best.sample_count < min_samples:
        return None, None
    if best.mean_score - llm_perf.mean_score < margin:
        return None, None

    rationale = (
        f"router_weights: {best.protocol} historically outperforms {llm_choice} "
        f"on this problem type "
        f"(mean {round(best.mean_score, 2)} vs {round(llm_perf.mean_score, 2)}, "
        f"n={best.sample_count})"
    )
    return best.protocol, rationale
