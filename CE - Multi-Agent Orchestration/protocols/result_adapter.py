"""Result adapter — normalize per-protocol Result dataclasses into a uniform envelope.

Addresses a systemic bug: ~28 of 50 protocols were producing empty
`result_summary` because `extract_synthesis()` only recognized the standard
field names. This adapter provides:

1. A hybrid two-tier resolver:
   - Tier 1: explicit overrides for ~27 protocols with non-standard shapes
     (custom str field names, dict syntheses, or no-synthesis protocols
     whose summary must be composed from structured data)
   - Tier 2: generic introspection fallback — walks the dataclass for the
     first populated str field matching a priority list, and collects all
     non-bookkeeping list/dict fields as structured metadata

2. A single entry point: `adapt_result(protocol_key, result) -> AdaptedResult`

3. A blocklist of bookkeeping fields that should never surface to the user
   (timings, model_calls, raw_output, etc.) and an output cap to prevent
   metadata bloat.

Overrides are intentionally small (5-20 lines each) and co-located so the
adapter stays auditable. Adding a new non-standard protocol = one function.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

# Generous cap — a rich mitigation map / adversarial memo can legitimately
# run 5-15k chars. Downstream consumers (PDF, portal) may trim further.
MAX_SUMMARY_LEN = 30_000

# Hard cap on serialized metadata payload to prevent runaway growth.
MAX_METADATA_LEN = 256_000

# Priority order for generic str-field fallback. Explicit overrides win first.
# Order matters: protocols with both "synthesis" and a legacy alternate
# prefer the newer standard name.
_SUMMARY_FIELD_PRIORITY: tuple[str, ...] = (
    "synthesis",
    "final_synthesis",
    "final_output",
    "synthesis_text",
    "recommendation",
    "summary",
    "conclusion",
    "verdict",
    "assessment",
    "mitigation_map",
    "adversarial_memo",
    "adapted_recommendations",
    "portfolio_summary",
    "report",
    "reasoning",
    "routing_rationale",
    "final_response",
)

# Fields that should never appear in structured metadata — pure bookkeeping
# or data that already surfaces through another channel (agent outputs).
_METADATA_BLOCKLIST: frozenset[str] = frozenset({
    "question",
    "timings",
    "model_calls",
    "cost",
    "raw_output",
    # These are narratives/perspectives/rounds — surfaced as agent outputs
    "agent_contributions",
    "narratives",
    "perspectives",
    "rounds",
    "per_agent_outputs",
    "agent_narratives",
    "responses_by_agent",
})


# ── Output type ──────────────────────────────────────────────────────────────

@dataclass(slots=True)
class AdaptedResult:
    """Normalized envelope payload extracted from a protocol Result.

    `result_summary` is the user-facing Executive Summary text (markdown OK).
    `metadata` holds promoted structured fields for downstream rendering.
    `warnings` lists any non-fatal extraction issues for telemetry.
    """

    result_summary: str
    metadata: dict[str, Any]
    warnings: list[dict[str, Any]] = field(default_factory=list)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _trim(text: str, limit: int = MAX_SUMMARY_LEN) -> str:
    if not isinstance(text, str):
        text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n_[truncated]_"


def _nonempty_str(value: Any) -> str | None:
    """Return the value if it's a non-empty str after stripping, else None."""
    if isinstance(value, str) and value.strip():
        return value
    return None


def _getattr_or_key(obj: Any, key: str, default: Any = None) -> Any:
    """Support both dataclass attributes and dict-shaped results."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _compose(*parts: str) -> str:
    """Join non-empty markdown parts with a horizontal rule between sections."""
    blocks = [p.strip() for p in parts if p and p.strip()]
    return "\n\n".join(blocks)


def _fmt_bullets(items: list, key: str | None = None) -> str:
    """Render a list as markdown bullets. If items are dicts, extract `key`."""
    lines = []
    for item in items or []:
        if item is None:
            continue
        if isinstance(item, dict) and key:
            val = item.get(key)
            if not val:
                continue
            lines.append(f"- {val}")
        elif isinstance(item, dict):
            # Compact dict rendering: key: value pairs
            compact = ", ".join(f"**{k}**: {v}" for k, v in item.items() if v)
            if compact:
                lines.append(f"- {compact}")
        elif isinstance(item, str) and item.strip():
            lines.append(f"- {item.strip()}")
    return "\n".join(lines)


def _fmt_dict_sections(d: dict, heading_level: int = 3) -> str:
    """Render a dict as markdown sections (keys become headings).

    Useful for dict-shaped syntheses like p16 ACHResult.synthesis,
    p18 DelphiResult.reasoning_summary, etc.
    """
    if not isinstance(d, dict) or not d:
        return ""
    hashes = "#" * heading_level
    lines: list[str] = []
    for key, value in d.items():
        if value is None or (isinstance(value, (list, dict, str)) and not value):
            continue
        label = str(key).replace("_", " ").title()
        lines.append(f"{hashes} {label}")
        if isinstance(value, str):
            lines.append(value.strip())
        elif isinstance(value, list):
            lines.append(_fmt_bullets(value))
        elif isinstance(value, dict):
            lines.append(_fmt_dict_sections(value, heading_level + 1))
        else:
            lines.append(str(value))
        lines.append("")
    return "\n".join(lines).strip()


def _cap_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Enforce the metadata size cap by dropping oversize values."""
    capped = {}
    try:
        serialized = json.dumps(metadata, default=str)
    except (TypeError, ValueError):
        return {"_truncated": True, "_reason": "unserializable"}
    if len(serialized) <= MAX_METADATA_LEN:
        return metadata
    for key, value in metadata.items():
        try:
            size = len(json.dumps(value, default=str))
        except (TypeError, ValueError):
            continue
        if size <= MAX_METADATA_LEN // 4:
            capped[key] = value
    capped["_truncated"] = True
    return capped


# ── Override implementations ─────────────────────────────────────────────────
#
# Each function takes a result object and returns AdaptedResult. They focus on:
#   - Correct primary summary selection (the "answer")
#   - Markdown prelude rendering for rich structured data worth showing inline
#   - Metadata promotion for structured data that downstream consumers need

def _adapt_p38_klein_premortem(result: Any) -> AdaptedResult:
    mitigation = _getattr_or_key(result, "mitigation_map", "") or ""
    failure_modes = _getattr_or_key(result, "failure_modes", []) or []
    overlooked = _getattr_or_key(result, "overlooked_signals", []) or []

    prelude_parts: list[str] = []
    if failure_modes:
        convergent = [f for f in failure_modes if f.get("type") == "convergent"]
        unique = [f for f in failure_modes if f.get("type") != "convergent"]
        fm_parts = ["## Failure Modes"]
        if convergent:
            fm_parts.append("### Convergent (multiple agents flagged)")
            fm_parts.extend(
                f"- **{f.get('title', 'Untitled')}** — {f.get('description', '')}"
                for f in convergent
            )
        if unique:
            fm_parts.append("\n### Unique (single-agent)")
            fm_parts.extend(
                f"- **{f.get('title', 'Untitled')}** — {f.get('description', '')}"
                for f in unique
            )
        prelude_parts.append("\n".join(fm_parts))
    if overlooked:
        prelude_parts.append(
            "## Overlooked Signals\n" + _fmt_bullets(overlooked)
        )

    summary = _compose(*prelude_parts, "## Mitigation Map" if mitigation else "", mitigation)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "failure_modes": failure_modes,
            "overlooked_signals": overlooked,
        },
    )


def _adapt_p39_popper(result: Any) -> AdaptedResult:
    synthesis = _getattr_or_key(result, "synthesis", "") or ""
    verdict = _getattr_or_key(result, "verdict", "") or ""
    verdict_reasoning = _getattr_or_key(result, "verdict_reasoning", "") or ""
    conditions = _getattr_or_key(result, "conditions", []) or []
    recommendation = _getattr_or_key(result, "recommendation", "") or ""

    # Prefer synthesis if populated; fall back to verdict + reasoning
    if synthesis:
        primary = synthesis
    else:
        primary_parts = []
        if recommendation:
            primary_parts.append(f"**Recommendation under test:** {recommendation}")
        if verdict:
            primary_parts.append(f"**Verdict:** {verdict}")
        if verdict_reasoning:
            primary_parts.append(verdict_reasoning)
        primary = _compose(*primary_parts)

    prelude_parts = []
    if conditions:
        cond_lines = ["## Falsification Conditions"]
        for i, c in enumerate(conditions, start=1):
            cond_text = c.get("condition", "") if isinstance(c, dict) else str(c)
            assessment = c.get("assessment", "") if isinstance(c, dict) else ""
            cond_lines.append(f"{i}. {cond_text}")
            if assessment:
                cond_lines.append(f"   - _Assessment:_ {assessment}")
        prelude_parts.append("\n".join(cond_lines))

    summary = _compose(*prelude_parts, primary)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "verdict": verdict,
            "conditions": conditions,
        },
    )


def _adapt_p41_duke_decision(result: Any) -> AdaptedResult:
    assessment = _getattr_or_key(result, "assessment", "") or ""
    recommendation = _getattr_or_key(result, "recommendation", "") or ""
    reasoning = _getattr_or_key(result, "reasoning", "") or ""
    scores = _getattr_or_key(result, "scores", {}) or {}
    justifications = _getattr_or_key(result, "justifications", {}) or {}
    overall_score = _getattr_or_key(result, "overall_score", 0.0)

    header = []
    if recommendation:
        header.append(f"**Recommendation:** {recommendation}")
    if overall_score:
        header.append(f"**Decision-quality score:** {overall_score:.1f} / 6")

    scores_section = ""
    if scores:
        lines = ["## Quality Dimension Scores"]
        for dim, score in scores.items():
            just = justifications.get(dim, "") if isinstance(justifications, dict) else ""
            lines.append(f"- **{dim}** ({score}): {just}")
        scores_section = "\n".join(lines)

    summary = _compose(
        "\n".join(header),
        scores_section,
        "## Assessment" if assessment else "",
        assessment or reasoning,
    )

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "scores": scores,
            "justifications": justifications,
            "overall_score": overall_score,
        },
    )


def _adapt_p43_leibniz_audit(result: Any) -> AdaptedResult:
    synthesis = _getattr_or_key(result, "synthesis", "") or ""
    verdict = _getattr_or_key(result, "verdict", "") or ""
    recommendation = _getattr_or_key(result, "recommendation", "") or ""
    reasoning = _getattr_or_key(result, "reasoning", "") or ""
    steps = _getattr_or_key(result, "steps", []) or []
    audit_findings = _getattr_or_key(result, "audit_findings", []) or []

    primary = synthesis or verdict or reasoning

    header = []
    if recommendation:
        header.append(f"**Recommendation audited:** {recommendation}")
    if verdict and verdict != primary:
        header.append(f"**Verdict:** {verdict}")

    findings_section = ""
    if audit_findings:
        lines = ["## Audit Findings"]
        for f in audit_findings:
            if isinstance(f, dict):
                lines.append(f"- **{f.get('type', '')}**: {f.get('description', '')}")
            else:
                lines.append(f"- {f}")
        findings_section = "\n".join(lines)

    summary = _compose("\n".join(header), findings_section, primary)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "verdict": verdict,
            "steps": steps,
            "audit_findings": audit_findings,
        },
    )


def _adapt_p48_black_swan(result: Any) -> AdaptedResult:
    memo = _getattr_or_key(result, "adversarial_memo", "") or ""
    confluences = _getattr_or_key(result, "confluences", []) or []
    historical = _getattr_or_key(result, "historical_analogues", []) or []

    prelude_parts = []
    if confluences:
        lines = ["## Confluences"]
        for c in confluences[:10]:
            if isinstance(c, dict):
                desc = c.get("description", c.get("name", ""))
                impact = c.get("impact", "")
                lines.append(f"- **{desc}** {f'— {impact}' if impact else ''}")
        prelude_parts.append("\n".join(lines))

    summary = _compose(*prelude_parts, "## Adversarial Memo" if memo else "", memo)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "confluences": confluences,
            "historical_analogues": historical,
            "causal_graphs_count": len(_getattr_or_key(result, "causal_graphs", []) or []),
            "threshold_scans_count": len(_getattr_or_key(result, "threshold_scans", []) or []),
        },
    )


def _adapt_p0a_router(result: Any) -> AdaptedResult:
    reasoning = _getattr_or_key(result, "reasoning", "") or ""
    recommended = _getattr_or_key(result, "recommended_protocol", "")
    recommended_name = _getattr_or_key(result, "recommended_name", "")
    problem_type = _getattr_or_key(result, "problem_type", "")
    alternatives = _getattr_or_key(result, "alternatives", []) or []

    header = [f"**Recommended protocol:** `{recommended}`"]
    if recommended_name:
        header.append(f" — {recommended_name}")
    if problem_type:
        header.append(f"\n**Problem type:** {problem_type}")

    alt_section = ""
    if alternatives:
        lines = ["## Alternatives"]
        for alt in alternatives:
            proto = getattr(alt, "protocol", None) or (alt.get("protocol") if isinstance(alt, dict) else None)
            name = getattr(alt, "name", None) or (alt.get("name") if isinstance(alt, dict) else "")
            reason = getattr(alt, "reason", None) or (alt.get("reason") if isinstance(alt, dict) else "")
            if proto:
                lines.append(f"- `{proto}` ({name}) — {reason}")
        alt_section = "\n".join(lines)

    summary = _compose("".join(header), "## Reasoning" if reasoning else "", reasoning, alt_section)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "features": _getattr_or_key(result, "features", {}),
            "problem_type": problem_type,
            "recommended_protocol": recommended,
            "alternatives": [
                {"protocol": getattr(a, "protocol", "" if not isinstance(a, dict) else a.get("protocol", "")),
                 "name": getattr(a, "name", "") if not isinstance(a, dict) else a.get("name", ""),
                 "reason": getattr(a, "reason", "") if not isinstance(a, dict) else a.get("reason", "")}
                for a in alternatives
            ],
        },
    )


def _adapt_p0b_skip_gate(result: Any) -> AdaptedResult:
    reasoning = _getattr_or_key(result, "reasoning", "") or ""
    decision = _getattr_or_key(result, "decision", "")
    confidence = _getattr_or_key(result, "confidence", 0)
    single_agent_response = _getattr_or_key(result, "single_agent_response", "") or ""
    recommended = _getattr_or_key(result, "recommended_protocol", "")
    cost_savings = _getattr_or_key(result, "estimated_cost_savings", "")

    header = [f"**Gate decision:** {decision} (confidence {confidence}%)"]
    if decision == "skip" and cost_savings:
        header.append(f"**Estimated savings:** {cost_savings}")
    if decision == "escalate" and recommended:
        header.append(f"**Escalate to:** `{recommended}`")

    summary = _compose(
        "\n".join(header),
        "## Reasoning" if reasoning else "",
        reasoning,
        "## Single-Agent Response" if single_agent_response else "",
        single_agent_response,
    )

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "decision": decision,
            "confidence": confidence,
            "features": _getattr_or_key(result, "features", {}),
            "recommended_protocol": recommended,
        },
    )


def _adapt_p0c_tiered_escalation(result: Any) -> AdaptedResult:
    final_response = _getattr_or_key(result, "final_response", "") or ""
    final_tier = _getattr_or_key(result, "final_tier", 0)
    tier_results = _getattr_or_key(result, "tier_results", []) or []
    flagged = _getattr_or_key(result, "flagged_for_human", False)
    flag_reason = _getattr_or_key(result, "flag_reason", "")

    header = [f"**Resolved at tier:** {final_tier}"]
    if flagged:
        header.append(f"**⚠ Flagged for human review:** {flag_reason}")

    summary = _compose(
        "\n".join(header),
        "## Final Response" if final_response else "",
        final_response,
    )

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "final_tier": final_tier,
            "flagged_for_human": flagged,
            "tier_results": [
                {
                    "tier": getattr(t, "tier", t.get("tier") if isinstance(t, dict) else 0),
                    "confidence": getattr(t, "confidence", t.get("confidence") if isinstance(t, dict) else 0),
                    "reasoning": getattr(t, "reasoning", t.get("reasoning") if isinstance(t, dict) else ""),
                }
                for t in tier_results
            ],
        },
    )


def _adapt_p42_square(result: Any) -> AdaptedResult:
    reasoning = _getattr_or_key(result, "reasoning", "") or ""
    classification = _getattr_or_key(result, "classification", "")
    recommended = _getattr_or_key(result, "recommended_protocol", "")
    rationale = _getattr_or_key(result, "routing_rationale", "") or ""
    pos_a = _getattr_or_key(result, "position_a", "")
    pos_b = _getattr_or_key(result, "position_b", "")

    header = []
    if classification:
        header.append(f"**Classification:** {classification}")
    if recommended:
        header.append(f"**Recommended protocol:** `{recommended}`")

    positions = ""
    if pos_a or pos_b:
        positions = f"## Positions\n- **A:** {pos_a}\n- **B:** {pos_b}"

    summary = _compose(
        "\n".join(header),
        positions,
        "## Reasoning" if reasoning else "",
        reasoning,
        "## Routing Rationale" if rationale else "",
        rationale,
    )

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "classification": classification,
            "recommended_protocol": recommended,
            "routing_rationale": rationale,
        },
    )


def _adapt_p44_kant_router(result: Any) -> AdaptedResult:
    rationale = _getattr_or_key(result, "routing_rationale", "") or ""
    problem_type = _getattr_or_key(result, "problem_type", "")
    modality = _getattr_or_key(result, "modality", "")
    modality_reasoning = _getattr_or_key(result, "modality_reasoning", "") or ""
    recommended = _getattr_or_key(result, "recommended_protocol", "")

    header = [
        f"**Problem type:** {problem_type or '—'}",
        f"**Modality:** {modality or '—'}",
        f"**Recommended protocol:** `{recommended or '—'}`",
    ]

    summary = _compose(
        "\n".join(header),
        "## Modality Reasoning" if modality_reasoning else "",
        modality_reasoning,
        "## Routing Rationale" if rationale else "",
        rationale,
    )

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "problem_type": problem_type,
            "modality": modality,
            "recommended_protocol": recommended,
        },
    )


def _adapt_p11_dad(result: Any) -> AdaptedResult:
    recommendations = _getattr_or_key(result, "adapted_recommendations", "") or ""
    practices = _getattr_or_key(result, "extracted_practices", []) or []

    prelude = ""
    if practices:
        lines = ["## Transferable Practices"]
        for p in practices[:8]:
            if isinstance(p, dict):
                name = p.get("practice", p.get("name", ""))
                desc = p.get("description", "")
                if name:
                    lines.append(f"- **{name}** — {desc}")
        prelude = "\n".join(lines)

    summary = _compose(prelude, "## Recommendations" if recommendations else "", recommendations)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "extracted_practices": practices,
            "scouted_deviants_count": len(_getattr_or_key(result, "scouted_deviants", []) or []),
        },
    )


def _adapt_p13_ecocycle(result: Any) -> AdaptedResult:
    portfolio = _getattr_or_key(result, "portfolio_summary", "") or ""
    consensus = _getattr_or_key(result, "consensus_stages", {}) or {}
    action_plans = _getattr_or_key(result, "action_plans", {}) or {}
    contested = _getattr_or_key(result, "contested", []) or []

    prelude_parts = []
    if consensus:
        lines = ["## Initiative → Stage"]
        for init, stage in consensus.items():
            marker = " ⚠" if init in contested else ""
            lines.append(f"- **{init}** → {stage}{marker}")
        prelude_parts.append("\n".join(lines))

    if action_plans:
        lines = ["## Action Plans"]
        for init, actions in action_plans.items():
            lines.append(f"### {init}")
            lines.extend(f"- {a}" for a in actions)
        prelude_parts.append("\n".join(lines))

    summary = _compose(*prelude_parts, "## Portfolio Summary" if portfolio else "", portfolio)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "consensus_stages": consensus,
            "action_plans": action_plans,
            "contested": contested,
        },
    )


def _adapt_p20_borda(result: Any) -> AdaptedResult:
    report = _getattr_or_key(result, "report", "") or ""
    final_ranking = _getattr_or_key(result, "final_ranking", []) or []
    borda_scores = _getattr_or_key(result, "borda_scores", {}) or {}
    winner = _getattr_or_key(result, "winner", "")
    margin = _getattr_or_key(result, "margin", 0)

    header = []
    if winner:
        header.append(f"**Winner:** {winner} (margin: {margin})")

    ranking_section = ""
    if final_ranking:
        lines = ["## Final Ranking"]
        for i, option in enumerate(final_ranking, start=1):
            score = borda_scores.get(option, "—")
            lines.append(f"{i}. **{option}** — Borda score {score}")
        ranking_section = "\n".join(lines)

    summary = _compose("\n".join(header), ranking_section, "## Report" if report else "", report)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "winner": winner,
            "borda_scores": borda_scores,
            "final_ranking": final_ranking,
        },
    )


def _adapt_p16_ach(result: Any) -> AdaptedResult:
    """p16 ACH: synthesis is a dict — render it as markdown sections."""
    synthesis = _getattr_or_key(result, "synthesis", {}) or {}
    surviving = _getattr_or_key(result, "surviving", []) or []
    eliminated = _getattr_or_key(result, "eliminated", []) or []

    header_parts = []
    if surviving:
        header_parts.append(
            "## Surviving Hypotheses\n"
            + "\n".join(f"- **{h.label}** ({h.id})" for h in surviving if hasattr(h, "label"))
        )
    if eliminated:
        header_parts.append(
            "## Eliminated\n"
            + "\n".join(f"- {h.label}" for h in eliminated if hasattr(h, "label"))
        )

    rendered_synthesis = _fmt_dict_sections(synthesis) if isinstance(synthesis, dict) else str(synthesis)

    summary = _compose(*header_parts, "## Analysis" if rendered_synthesis else "", rendered_synthesis)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "surviving": [dataclasses.asdict(h) if dataclasses.is_dataclass(h) and not isinstance(h, type) else h for h in surviving],
            "eliminated": [dataclasses.asdict(h) if dataclasses.is_dataclass(h) and not isinstance(h, type) else h for h in eliminated],
            "evidence_count": len(_getattr_or_key(result, "evidence", []) or []),
        },
    )


def _adapt_p18_delphi(result: Any) -> AdaptedResult:
    reasoning_summary = _getattr_or_key(result, "reasoning_summary", {}) or {}
    final_estimate = _getattr_or_key(result, "final_estimate", 0.0)
    ci = _getattr_or_key(result, "confidence_interval", None)
    converged = _getattr_or_key(result, "converged", False)
    rounds_used = _getattr_or_key(result, "rounds_used", 0)

    header = [
        f"**Final estimate:** {final_estimate}",
        f"**Converged:** {'yes' if converged else 'no'} ({rounds_used} rounds)",
    ]
    if ci and isinstance(ci, (tuple, list)) and len(ci) == 2:
        header.append(f"**Confidence interval:** [{ci[0]}, {ci[1]}]")

    rendered = _fmt_dict_sections(reasoning_summary) if isinstance(reasoning_summary, dict) else str(reasoning_summary)

    summary = _compose("\n".join(header), "## Reasoning Summary" if rendered else "", rendered)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "final_estimate": final_estimate,
            "confidence_interval": list(ci) if ci else None,
            "converged": converged,
        },
    )


def _adapt_p19_vickrey(result: Any) -> AdaptedResult:
    synthesis = _getattr_or_key(result, "synthesis", {}) or {}
    winner = _getattr_or_key(result, "winner", "")
    winning_option = _getattr_or_key(result, "winning_option", "")
    original_conf = _getattr_or_key(result, "original_confidence", 0)
    second_price_conf = _getattr_or_key(result, "second_price_confidence", 0)
    calibrated = _getattr_or_key(result, "calibrated_justification", "") or ""

    header = []
    if winning_option:
        header.append(f"**Winning option:** {winning_option}")
    if winner:
        header.append(f"**Winning bidder:** {winner}")
    if original_conf or second_price_conf:
        header.append(f"**Confidence:** {original_conf} → {second_price_conf} (second-price calibrated)")

    rendered = _fmt_dict_sections(synthesis) if isinstance(synthesis, dict) else str(synthesis)

    summary = _compose(
        "\n".join(header),
        "## Calibrated Justification" if calibrated else "",
        calibrated,
        "## Analysis" if rendered else "",
        rendered,
    )

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "winner": winner,
            "winning_option": winning_option,
            "original_confidence": original_conf,
            "second_price_confidence": second_price_conf,
        },
    )


def _adapt_p23_cynefin(result: Any) -> AdaptedResult:
    action_plan = _getattr_or_key(result, "action_plan", {}) or {}
    consensus_domain = _getattr_or_key(result, "consensus_domain", "")
    was_contested = _getattr_or_key(result, "was_contested", False)

    header = [f"**Cynefin domain:** {consensus_domain}" + (" ⚠ (contested)" if was_contested else "")]

    rendered = _fmt_dict_sections(action_plan) if isinstance(action_plan, dict) else str(action_plan)

    summary = _compose("\n".join(header), "## Action Plan" if rendered else "", rendered)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "consensus_domain": consensus_domain,
            "was_contested": was_contested,
            "action_plan": action_plan,
        },
    )


def _adapt_p10_hsr(result: Any) -> AdaptedResult:
    common_ground = _getattr_or_key(result, "common_ground", "") or ""
    key_differences = _getattr_or_key(result, "key_differences", "") or ""
    translation_guide = _getattr_or_key(result, "translation_guide", "") or ""

    summary = _compose(
        "## Common Ground" if common_ground else "",
        common_ground,
        "## Key Differences" if key_differences else "",
        key_differences,
        "## Translation Guide" if translation_guide else "",
        translation_guide,
    )

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "common_ground": common_ground,
            "key_differences": key_differences,
            "reflection_count": len(_getattr_or_key(result, "reflections", []) or []),
        },
    )


def _adapt_p21_interests(result: Any) -> AdaptedResult:
    agreement = _getattr_or_key(result, "selected_agreement", {}) or {}
    options = _getattr_or_key(result, "generated_options", []) or []
    satisfaction = _getattr_or_key(result, "interest_satisfaction", {}) or {}
    categorized = _getattr_or_key(result, "categorized_interests", {}) or {}

    header = []
    if isinstance(agreement, dict) and agreement:
        title = agreement.get("title") or agreement.get("name") or ""
        desc = agreement.get("description") or agreement.get("summary") or ""
        if title:
            header.append(f"## Selected Agreement\n**{title}**\n\n{desc}")
        elif desc:
            header.append(f"## Selected Agreement\n{desc}")

    sat_section = ""
    if satisfaction:
        lines = ["## Interest Satisfaction"]
        for agent, score in satisfaction.items():
            score_val = f"{score:.0%}" if isinstance(score, (int, float)) else str(score)
            lines.append(f"- **{agent}**: {score_val}")
        sat_section = "\n".join(lines)

    options_section = ""
    if options:
        lines = ["## Generated Options"]
        for opt in options[:6]:
            if isinstance(opt, dict):
                title = opt.get("title", opt.get("option", ""))
                if title:
                    lines.append(f"- {title}")
        options_section = "\n".join(lines)

    summary = _compose(*header, sat_section, options_section)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "selected_agreement": agreement,
            "interest_satisfaction": satisfaction,
            "categorized_interests": categorized,
        },
    )


def _adapt_p24_causal_loop(result: Any) -> AdaptedResult:
    variables = _getattr_or_key(result, "variables", []) or []
    links = _getattr_or_key(result, "causal_links", []) or []
    reinforcing = _getattr_or_key(result, "reinforcing_loops", []) or []
    balancing = _getattr_or_key(result, "balancing_loops", []) or []
    leverage = _getattr_or_key(result, "leverage_points", []) or []

    header = [
        f"**Variables identified:** {len(variables)}",
        f"**Causal links:** {len(links)}",
        f"**Reinforcing loops:** {len(reinforcing)}",
        f"**Balancing loops:** {len(balancing)}",
    ]

    leverage_section = ""
    if leverage:
        lines = ["## Leverage Points"]
        for lp in leverage:
            if isinstance(lp, dict):
                lines.append(f"- **{lp.get('variable', '')}**: {lp.get('rationale', '')}")
            else:
                lines.append(f"- {lp}")
        leverage_section = "\n".join(lines)

    summary = _compose(" · ".join(header), leverage_section)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "variable_count": len(variables),
            "link_count": len(links),
            "reinforcing_loop_count": len(reinforcing),
            "balancing_loop_count": len(balancing),
            "leverage_points": leverage,
        },
    )


def _adapt_p25_archetype(result: Any) -> AdaptedResult:
    best_matches = _getattr_or_key(result, "best_matches", []) or []
    interventions = _getattr_or_key(result, "interventions", []) or []
    observed = _getattr_or_key(result, "observed_dynamics", []) or []

    matches_section = ""
    if best_matches:
        lines = ["## Best-Matching Archetypes"]
        for m in best_matches[:3]:
            name = getattr(m, "archetype", None) or (m.get("archetype") if isinstance(m, dict) else "")
            score = getattr(m, "score", None) or (m.get("score") if isinstance(m, dict) else "")
            reasoning = getattr(m, "reasoning", None) or (m.get("reasoning") if isinstance(m, dict) else "")
            lines.append(f"### {name} (score: {score})\n{reasoning}")
        matches_section = "\n".join(lines)

    interventions_section = ""
    if interventions:
        lines = ["## Recommended Interventions"]
        for i in interventions:
            if isinstance(i, dict):
                action = i.get("action", i.get("intervention", ""))
                rationale = i.get("rationale", "")
                if action:
                    lines.append(f"- **{action}** — {rationale}")
        interventions_section = "\n".join(lines)

    summary = _compose(matches_section, interventions_section)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "best_matches": [dataclasses.asdict(m) if dataclasses.is_dataclass(m) and not isinstance(m, type) else m for m in best_matches],
            "interventions": interventions,
            "observed_dynamics_count": len(observed),
        },
    )


def _adapt_p26_crazy_eights(result: Any) -> AdaptedResult:
    top_ideas = _getattr_or_key(result, "top_ideas", []) or []
    developed = _getattr_or_key(result, "developed_concepts", []) or []
    total = _getattr_or_key(result, "total_ideas", 0)
    clusters = _getattr_or_key(result, "clusters", []) or []

    header = [f"**{total} ideas generated across {len(clusters)} clusters.**"]

    top_section = ""
    if top_ideas:
        top_section = "## Top-Voted Ideas\n" + _fmt_bullets(top_ideas)

    developed_section = ""
    if developed:
        lines = ["## Developed Concepts"]
        for c in developed[:5]:
            if isinstance(c, dict):
                title = c.get("title", c.get("concept", ""))
                desc = c.get("description", c.get("development", ""))
                if title:
                    lines.append(f"### {title}\n{desc}")
        developed_section = "\n".join(lines)

    summary = _compose("\n".join(header), top_section, developed_section)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "top_ideas": top_ideas,
            "total_ideas": total,
            "cluster_count": len(clusters),
            "developed_concepts": developed,
        },
    )


def _adapt_p27_affinity(result: Any) -> AdaptedResult:
    strategic_insights = _getattr_or_key(result, "strategic_insights", []) or []
    themed_clusters = _getattr_or_key(result, "themed_clusters", []) or []
    hierarchy = _getattr_or_key(result, "hierarchy", []) or []
    total = _getattr_or_key(result, "total_items", 0)

    header = [f"**{total} items organized into {len(themed_clusters)} themed clusters.**"]

    insights_section = ""
    if strategic_insights:
        insights_section = "## Strategic Insights\n" + _fmt_bullets(strategic_insights)

    hierarchy_section = ""
    if hierarchy:
        lines = ["## Hierarchy"]
        for h in hierarchy[:10]:
            if isinstance(h, dict):
                level = h.get("level", "")
                label = h.get("label", h.get("theme", ""))
                if label:
                    lines.append(f"- {'  ' * int(level) if isinstance(level, int) else ''}**{label}**")
        hierarchy_section = "\n".join(lines)

    clusters_section = ""
    if themed_clusters:
        lines = ["## Themes"]
        for c in themed_clusters[:8]:
            if isinstance(c, dict):
                theme = c.get("theme", c.get("label", ""))
                items = c.get("items", [])
                if theme:
                    lines.append(f"- **{theme}** ({len(items)} items)")
        clusters_section = "\n".join(lines)

    summary = _compose("\n".join(header), insights_section, clusters_section, hierarchy_section)

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata={
            "total_items": total,
            "cluster_count": len(themed_clusters),
            "strategic_insights": strategic_insights,
        },
    )


def _adapt_walk(result: Any) -> AdaptedResult:
    """p49-p52 WalkResult shared adapter.

    Prefer synthesis_text (str) for the summary. The structured synthesis
    (WalkSynthesis dataclass) goes to metadata.
    """
    synthesis_text = _getattr_or_key(result, "synthesis_text", "") or ""
    structured = _getattr_or_key(result, "synthesis", None)
    collisions = _getattr_or_key(result, "collisions", []) or []

    # If synthesis_text is empty but structured synthesis exists, compose one
    if not synthesis_text and structured is not None:
        if dataclasses.is_dataclass(structured) and not isinstance(structured, type):
            structured_dict = dataclasses.asdict(structured)
        elif isinstance(structured, dict):
            structured_dict = structured
        else:
            structured_dict = {}
        synthesis_text = _fmt_dict_sections(structured_dict)

    collision_note = ""
    if collisions:
        collision_note = f"_{len(collisions)} cross-walk collisions detected._"

    summary = _compose(collision_note, synthesis_text)

    # Structured synthesis → metadata
    metadata: dict[str, Any] = {"collision_count": len(collisions)}
    if structured is not None:
        if dataclasses.is_dataclass(structured) and not isinstance(structured, type):
            metadata["structured_synthesis"] = dataclasses.asdict(structured)
        elif isinstance(structured, dict):
            metadata["structured_synthesis"] = structured

    return AdaptedResult(
        result_summary=_trim(summary),
        metadata=metadata,
    )


# ── Override registry ────────────────────────────────────────────────────────
#
# Match by protocol_key (from capability.yaml). Keys must match the directory
# names exactly (e.g. "p38_klein_premortem", not "p38" or "klein_premortem").

_OVERRIDES: dict[str, Callable[[Any], AdaptedResult]] = {
    "p38_klein_premortem": _adapt_p38_klein_premortem,
    "p39_popper_falsification": _adapt_p39_popper,
    "p41_duke_decision_quality": _adapt_p41_duke_decision,
    "p43_leibniz_audit": _adapt_p43_leibniz_audit,
    "p48_black_swan_detection": _adapt_p48_black_swan,
    "p0a_reasoning_router": _adapt_p0a_router,
    "p0b_skip_gate": _adapt_p0b_skip_gate,
    "p0c_tiered_escalation": _adapt_p0c_tiered_escalation,
    "p42_aristotle_square": _adapt_p42_square,
    "p44_kant_pre_router": _adapt_p44_kant_router,
    "p11_discovery_action_dialogue": _adapt_p11_dad,
    "p13_ecocycle_planning": _adapt_p13_ecocycle,
    "p20_borda_count": _adapt_p20_borda,
    "p16_ach": _adapt_p16_ach,
    "p18_delphi_method": _adapt_p18_delphi,
    "p19_vickrey_auction": _adapt_p19_vickrey,
    "p23_cynefin_probe": _adapt_p23_cynefin,
    "p10_heard_seen_respected": _adapt_p10_hsr,
    "p21_interests_negotiation": _adapt_p21_interests,
    "p24_causal_loop_mapping": _adapt_p24_causal_loop,
    "p25_system_archetype_detection": _adapt_p25_archetype,
    "p26_crazy_eights": _adapt_p26_crazy_eights,
    "p27_affinity_mapping": _adapt_p27_affinity,
    "p49_walk_base": _adapt_walk,
    "p50_tournament_walk": _adapt_walk,
    "p51_wildcard_walk": _adapt_walk,
    "p52_drift_return_walk": _adapt_walk,
}


# ── Generic fallback ─────────────────────────────────────────────────────────

def _generic_adapt(result: Any) -> AdaptedResult:
    """Introspection-based fallback for protocols without an explicit override.

    Covers the 23 happy-path protocols with standard `synthesis: str` fields
    and any new protocols added later that follow the convention.
    """
    summary: str | None = None

    # Attribute lookup (dataclass / object)
    for name in _SUMMARY_FIELD_PRIORITY:
        val = _getattr_or_key(result, name)
        nonempty = _nonempty_str(val)
        if nonempty:
            summary = nonempty
            break

    # Dict fallback: if summary field is a dict, render as markdown
    if summary is None:
        for name in _SUMMARY_FIELD_PRIORITY:
            val = _getattr_or_key(result, name)
            if isinstance(val, dict) and val:
                summary = _fmt_dict_sections(val)
                break

    # Collect structured metadata: every list/dict field except blocklisted
    metadata: dict[str, Any] = {}
    fields_iter: list[tuple[str, Any]] = []
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        for f in dataclasses.fields(result):
            fields_iter.append((f.name, getattr(result, f.name)))
    elif isinstance(result, dict):
        fields_iter = list(result.items())
    else:
        for key in dir(result):
            if key.startswith("_"):
                continue
            val = getattr(result, key, None)
            if callable(val):
                continue
            fields_iter.append((key, val))

    for name, value in fields_iter:
        if name in _METADATA_BLOCKLIST:
            continue
        if name in _SUMMARY_FIELD_PRIORITY:
            continue  # already captured as summary
        if isinstance(value, (list, dict)) and value:
            # Unwrap dataclass instances inside lists
            if isinstance(value, list):
                metadata[name] = [
                    dataclasses.asdict(v) if dataclasses.is_dataclass(v) and not isinstance(v, type) else v
                    for v in value
                ]
            else:
                metadata[name] = value

    return AdaptedResult(
        result_summary=_trim(summary or ""),
        metadata=_cap_metadata(metadata),
    )


# ── Public entry point ───────────────────────────────────────────────────────

def adapt_result(protocol_key: str, result: Any) -> AdaptedResult:
    """Normalize a protocol's Result dataclass into a uniform envelope.

    Tier 1: explicit override for protocols with non-standard shapes.
    Tier 2: generic introspection for conventional shapes.
    Both paths return AdaptedResult(result_summary, metadata, warnings).
    """
    override = _OVERRIDES.get(protocol_key)

    warnings: list[dict[str, Any]] = []

    try:
        if override is not None:
            adapted = override(result)
            adapted.metadata = _cap_metadata(adapted.metadata)
            return adapted
    except Exception as exc:  # noqa: BLE001 — never crash the run on adapter failure
        warnings.append({
            "code": "adapter_override_failed",
            "message": f"{protocol_key} adapter raised {type(exc).__name__}: {exc}",
            "component": "result_adapter",
            "level": "warning",
            "recoverable": True,
        })
        logger.exception("Adapter override failed for %s", protocol_key)

    # Fall through to generic (also covers the override-failure case)
    try:
        adapted = _generic_adapt(result)
        adapted.warnings = warnings + adapted.warnings
        return adapted
    except Exception as exc:  # noqa: BLE001
        warnings.append({
            "code": "adapter_generic_failed",
            "message": f"generic adapter raised {type(exc).__name__}: {exc}",
            "component": "result_adapter",
            "level": "warning",
            "recoverable": True,
        })
        logger.exception("Generic adapter failed for %s", protocol_key)
        return AdaptedResult(result_summary="", metadata={}, warnings=warnings)
