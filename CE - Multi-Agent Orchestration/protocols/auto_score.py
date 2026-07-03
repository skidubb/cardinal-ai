"""Auto-score completed runs and write results to P45 weights.

Sprint 3 upgrade to Cardinal Element's learning surface. Previously P45
`record()` required a human `--score`; nothing scored runs automatically, so
the P0a→weights loop had no data flowing through it. This module fixes that:

Every completed run gets a score, and the score is written directly to the
same JSON file P45 reads and P0a uses. Two backends are supported:

1. **heuristic** (default) — cheap, deterministic scoring based on envelope
   shape (synthesis present, no error, cost within bounds, agent outputs
   present). Runs on every completion; no LLM cost.
2. **ce_evals** — invokes the CE-Evals judge (Claude, GPT-4, or Gemini) if
   installed and configured. Real LLM-as-judge scoring. Higher signal.

Selection: env var ``AUTO_SCORE_BACKEND`` (values: ``heuristic``, ``ce_evals``,
``off``). Default: ``heuristic``. Setting ``off`` disables the loop entirely.

Best-effort throughout: any failure to score, load records, or write is
logged and swallowed. Auto-scoring must never break a run.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from protocols.router_weights import WEIGHTS_PATH

_log = logging.getLogger(__name__)


BACKEND_ENV_VAR = "AUTO_SCORE_BACKEND"
DEFAULT_BACKEND = "heuristic"

# Heuristic scoring parameters (tuned to spread scores across [0, 1] for
# a realistic run distribution).
_HEURISTIC_SYNTHESIS_WEIGHT = 0.35
_HEURISTIC_AGENT_OUTPUT_WEIGHT = 0.25
_HEURISTIC_STATUS_WEIGHT = 0.25
_HEURISTIC_COST_EFFICIENCY_WEIGHT = 0.15

# Cost bands used by the efficiency term (USD). A run under LOW gets full
# credit; between LOW and HIGH the credit tapers; above HIGH is zero.
_COST_LOW = 0.10
_COST_HIGH = 2.00


@dataclass(slots=True)
class ScoreResult:
    """The outcome of an auto-score attempt."""

    scored: bool
    score: float | None = None
    backend: str = ""
    problem_type: str = "general"
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "scored": self.scored,
            "score": self.score,
            "backend": self.backend,
            "problem_type": self.problem_type,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

async def auto_score_and_record(envelope: Any, problem_type: str | None = None) -> ScoreResult:
    """Score a run envelope and append records to the P45 weights file.

    One record is written per agent so P45's per-agent recommendation logic
    keeps working. All records share the same score — auto-scoring gives one
    quality signal for the run, not per-agent signals.

    Returns a `ScoreResult` regardless of success, so callers can log it.
    """
    backend = os.getenv(BACKEND_ENV_VAR, DEFAULT_BACKEND).strip().lower() or DEFAULT_BACKEND
    if backend == "off":
        return ScoreResult(scored=False, backend="off", reason="AUTO_SCORE_BACKEND=off")

    resolved_type = (problem_type or _infer_problem_type(envelope)).strip() or "general"

    try:
        score = await _score(envelope, backend)
    except Exception as e:  # pragma: no cover — defensive
        _log.debug("auto_score: scoring failed (%s)", e, exc_info=True)
        return ScoreResult(scored=False, backend=backend, reason=f"scoring_error:{type(e).__name__}")

    if score is None:
        return ScoreResult(scored=False, backend=backend, reason="backend_returned_none")

    protocol_key = getattr(envelope, "protocol_key", "") or ""
    agent_keys = list(getattr(envelope, "agent_keys", []) or [])

    if not protocol_key or not agent_keys:
        return ScoreResult(
            scored=False,
            backend=backend,
            score=score,
            problem_type=resolved_type,
            reason="missing_protocol_or_agents",
        )

    ok = _append_records(protocol_key, agent_keys, resolved_type, score)
    if not ok:
        return ScoreResult(
            scored=False,
            backend=backend,
            score=score,
            problem_type=resolved_type,
            reason="weights_write_failed",
        )

    return ScoreResult(
        scored=True,
        backend=backend,
        score=score,
        problem_type=resolved_type,
        reason="ok",
    )


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

async def _score(envelope: Any, backend: str) -> float | None:
    if backend == "heuristic":
        return _heuristic_score(envelope)
    if backend == "ce_evals":
        judged = await _ce_evals_score(envelope)
        if judged is not None:
            return judged
        # ce_evals absent or failed — fall back to heuristic so the loop still
        # closes with weaker signal rather than going silent.
        return _heuristic_score(envelope)
    _log.warning("auto_score: unknown backend %r, falling back to heuristic", backend)
    return _heuristic_score(envelope)


def _heuristic_score(envelope: Any) -> float:
    """Deterministic score in [0, 1] based on envelope shape."""
    status = str(getattr(envelope, "status", "") or "").lower()
    status_term = 1.0 if status == "completed" else 0.0

    synthesis = str(getattr(envelope, "result_summary", "") or "").strip()
    synthesis_term = min(1.0, len(synthesis) / 400.0)

    agent_outputs = list(getattr(envelope, "agent_outputs", []) or [])
    non_empty = [a for a in agent_outputs if str(getattr(a, "text", "") or "").strip()]
    if agent_outputs:
        agent_term = len(non_empty) / len(agent_outputs)
    else:
        agent_term = 0.0

    cost_summary = getattr(envelope, "cost", {}) or {}
    total_cost = 0.0
    if isinstance(cost_summary, dict):
        try:
            total_cost = float(cost_summary.get("total_usd", 0.0) or 0.0)
        except (TypeError, ValueError):
            total_cost = 0.0
    if total_cost <= _COST_LOW:
        cost_term = 1.0
    elif total_cost >= _COST_HIGH:
        cost_term = 0.0
    else:
        cost_term = 1.0 - (total_cost - _COST_LOW) / (_COST_HIGH - _COST_LOW)

    score = (
        _HEURISTIC_STATUS_WEIGHT * status_term
        + _HEURISTIC_SYNTHESIS_WEIGHT * synthesis_term
        + _HEURISTIC_AGENT_OUTPUT_WEIGHT * agent_term
        + _HEURISTIC_COST_EFFICIENCY_WEIGHT * cost_term
    )
    return max(0.0, min(1.0, round(score, 4)))


async def _ce_evals_score(envelope: Any) -> float | None:
    """Optional CE-Evals LLM-as-judge scoring. Returns None if unavailable."""
    try:
        from ce_evals import Judge, Rubric  # noqa: F401
    except ImportError:
        return None
    try:
        # CE-Evals is imported lazily and used with a default general-purpose
        # rubric. If a project ships a protocol-specific rubric, replace this
        # call with `Rubric.from_yaml(rubric_path)`.
        rubric = Rubric.general()  # type: ignore[attr-defined]
        judge = Judge(backend="claude", rubric=rubric)  # type: ignore[call-arg]
        payload = _envelope_to_judge_payload(envelope)
        result = await judge.score(payload)
        return float(getattr(result, "score", None) or result["score"])
    except Exception as e:  # pragma: no cover — best-effort
        _log.debug("auto_score: ce_evals path unavailable (%s)", e, exc_info=True)
        return None


def _envelope_to_judge_payload(envelope: Any) -> dict[str, Any]:
    return {
        "question": getattr(envelope, "question", ""),
        "protocol": getattr(envelope, "protocol_key", ""),
        "synthesis": getattr(envelope, "result_summary", ""),
        "result": getattr(envelope, "result_json", None),
    }


# ---------------------------------------------------------------------------
# Weight file I/O — mirrors P45's shape so both readers/writers agree
# ---------------------------------------------------------------------------

def _append_records(
    protocol_key: str,
    agent_keys: list[str],
    problem_type: str,
    score: float,
) -> bool:
    """Append one record per agent to the shared weights file. Never raises."""
    try:
        if os.path.exists(WEIGHTS_PATH):
            with open(WEIGHTS_PATH) as f:
                data = json.load(f)
        else:
            data = {"records": []}
    except (OSError, json.JSONDecodeError) as e:
        _log.debug("auto_score: could not load %s (%s), starting fresh", WEIGHTS_PATH, e)
        data = {"records": []}

    records = data.setdefault("records", [])
    if not isinstance(records, list):
        records = []
        data["records"] = records

    now = datetime.now(timezone.utc).isoformat()
    for agent in agent_keys:
        records.append(
            {
                "agent": agent,
                "protocol": protocol_key,
                "problem_type": problem_type,
                "score": score,
                "timestamp": now,
                "source": "auto_score",
            }
        )

    try:
        os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
        with open(WEIGHTS_PATH, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except OSError as e:
        _log.warning("auto_score: failed to write %s (%s)", WEIGHTS_PATH, e)
        return False


# ---------------------------------------------------------------------------
# Problem-type inference — used when the caller doesn't supply one
# ---------------------------------------------------------------------------

_PROTOCOL_TO_PROBLEM_TYPE = {
    "p16_ach": "Diagnostic",
    "p24_causal_loop_mapping": "Systems Analysis",
    "p25_system_archetype_detection": "Systems Analysis",
    "p33_evaporation_cloud": "Multi-Stakeholder",
    "p34_current_reality_tree": "Diagnostic",
    "p38_klein_premortem": "Adversarial",
    "p39_popper_falsification": "Adversarial",
    "p17_red_blue_white": "Adversarial",
    "p19_vickrey_auction": "Prioritization",
    "p20_borda_count": "Prioritization",
    "p18_delphi_method": "Estimation",
    "p32_tetlock_forecast": "Estimation",
    "p5_constraint_negotiation": "Constraint Definition",
    "p05_constraint_negotiation": "Constraint Definition",
    "p8_min_specs": "Constraint Definition",
    "p08_min_specs": "Constraint Definition",
    "p21_interests_negotiation": "Multi-Stakeholder",
    "p6_triz": "Exploration",
    "p06_triz": "Exploration",
    "p26_crazy_eights": "Exploration",
    "p30_llull_combinatorial": "Exploration",
    "p13_ecocycle_planning": "Portfolio Management",
    "p48_black_swan_detection": "Systems Analysis",
}


def _infer_problem_type(envelope: Any) -> str:
    """Best-effort mapping from protocol_key → canonical problem_type."""
    protocol = str(getattr(envelope, "protocol_key", "") or "").lower()
    if protocol in _PROTOCOL_TO_PROBLEM_TYPE:
        return _PROTOCOL_TO_PROBLEM_TYPE[protocol]
    # Envelope metadata may carry a router-supplied problem_type on more recent runs.
    metadata = getattr(envelope, "metadata", {}) or {}
    if isinstance(metadata, dict):
        pt = metadata.get("problem_type")
        if isinstance(pt, str) and pt.strip():
            return pt.strip()
    return "general"
