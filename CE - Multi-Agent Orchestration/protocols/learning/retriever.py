"""Retrieve learning insights before a protocol run."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select

logger = logging.getLogger(__name__)


class RunInsights(BaseModel):
    """Pre-run insights retrieved from past protocol runs."""

    protocol_scores: dict[str, float] = {}
    recommended_protocol: str | None = None
    optimal_rounds: int | None = None
    optimal_agents: list[str] | None = None
    thinking_budget: int | None = None
    institutional_memory: str | None = None
    confidence: float = 0.0
    sample_size: int = 0

    @property
    def has_recommendations(self) -> bool:
        return self.confidence > 0.3 and self.sample_size >= 3


_EMPTY = RunInsights()


async def retrieve_insights(
    protocol_key: str,
    question: str,
    question_categories: list[str],
) -> RunInsights:
    """Retrieve relevant learning before a protocol run. Returns empty on failure."""
    try:
        from ce_db.session import get_session
        from ce_db.models.insights import ProtocolInsight

        async with get_session() as session:
            scores = await _get_protocol_scores(session, question_categories)
            config = await _get_config_insight(session, protocol_key, question_categories)
            contextual = await _get_best_contextual(session, protocol_key, question_categories)

            sample_size = sum(v["n"] for v in scores.values()) if scores else 0

            return RunInsights(
                protocol_scores={k: v["avg_score"] for k, v in scores.items()},
                recommended_protocol=_pick_best(scores, protocol_key),
                optimal_rounds=config.get("optimal_rounds") if config else None,
                optimal_agents=config.get("optimal_agents") if config else None,
                thinking_budget=config.get("thinking_budget") if config else None,
                institutional_memory=contextual.best_synthesis if contextual else None,
                confidence=min(1.0, sample_size / 20),
                sample_size=sample_size,
            )
    except Exception as e:
        logger.warning(f"retrieve_insights failed (degrading gracefully): {e}")
        return _EMPTY


async def _get_protocol_scores(
    session: Any, categories: list[str],
) -> dict[str, dict[str, float]]:
    """Get avg scores per protocol for given categories."""
    from ce_db.models.insights import ProtocolInsight

    stmt = (
        select(ProtocolInsight)
        .where(
            ProtocolInsight.question_category.in_(categories),
            ProtocolInsight.insight_type == "protocol_comparison",
        )
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()

    scores: dict[str, dict] = {}
    for row in rows:
        pk = row.protocol_key
        data = row.insight_json or {}
        if pk not in scores:
            scores[pk] = {"avg_score": data.get("avg_score", 0), "n": row.sample_size}
        else:
            existing = scores[pk]
            total_n = existing["n"] + row.sample_size
            existing["avg_score"] = (
                (existing["avg_score"] * existing["n"] + data.get("avg_score", 0) * row.sample_size)
                / total_n
            ) if total_n > 0 else 0
            existing["n"] = total_n
    return scores


async def _get_config_insight(
    session: Any, protocol_key: str, categories: list[str],
) -> dict | None:
    """Get config tuning insight for a specific protocol+categories."""
    from ce_db.models.insights import ProtocolInsight

    stmt = (
        select(ProtocolInsight)
        .where(
            ProtocolInsight.protocol_key == protocol_key,
            ProtocolInsight.question_category.in_(categories),
            ProtocolInsight.insight_type == "config_tuning",
        )
        .order_by(ProtocolInsight.confidence.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return row.insight_json if row else None


async def _get_best_contextual(
    session: Any, protocol_key: str, categories: list[str],
) -> Any | None:
    """Get highest-scored contextual insight across categories."""
    from ce_db.models.insights import ProtocolInsight

    stmt = (
        select(ProtocolInsight)
        .where(
            ProtocolInsight.protocol_key == protocol_key,
            ProtocolInsight.question_category.in_(categories),
            ProtocolInsight.insight_type == "contextual",
            ProtocolInsight.best_score.isnot(None),
        )
        .order_by(ProtocolInsight.best_score.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _pick_best(
    scores: dict[str, dict[str, float]], current_protocol: str,
) -> str | None:
    """Pick the best-performing protocol, or None if current is already best."""
    if not scores:
        return None
    best_key = max(scores, key=lambda k: scores[k]["avg_score"])
    if best_key == current_protocol:
        return None
    current_score = scores.get(current_protocol, {}).get("avg_score", 0)
    if scores[best_key]["avg_score"] - current_score > 0.3:
        return best_key
    return None
