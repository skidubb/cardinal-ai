"""Record protocol run outcomes for future learning."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select

logger = logging.getLogger(__name__)


async def record_learning(
    run_id: str | int | None,
    protocol_key: str,
    question: str,
    question_categories: list[str],
    eval_score: float | None,
    config: dict,
    synthesis_text: str,
    cost_summary: dict,
) -> None:
    """Store run outcome for future learning. Non-blocking."""
    try:
        from ce_db.session import get_session
        from ce_db.models.insights import ProtocolInsight, RunLearning

        async with get_session() as session:
            learning = RunLearning(
                run_id=str(run_id) if run_id else "unknown",
                protocol_key=protocol_key,
                question_categories=question_categories,
                eval_score=eval_score,
                config_json=config,
                cost_usd=cost_summary.get("total_usd", 0.0),
                synthesis_excerpt=synthesis_text[:2000] if synthesis_text else None,
            )
            session.add(learning)

            if eval_score is None:
                await session.commit()
                return

            for cat in question_categories:
                existing = await _get_contextual_insight_single(session, protocol_key, cat)
                if existing is None or eval_score > (existing.best_score or 0):
                    await _upsert_contextual_insight(
                        session, protocol_key, cat,
                        best_synthesis=synthesis_text[:3000] if synthesis_text else None,
                        best_score=eval_score,
                    )

            run_count = await _count_runs_since_last_compute(
                session, protocol_key, question_categories,
            )
            if run_count >= 5:
                await _recompute_insights(session, protocol_key, question_categories)

            await session.commit()
    except Exception as e:
        logger.warning(f"record_learning failed (non-blocking): {e}")


async def _get_contextual_insight_single(
    session: Any, protocol_key: str, category: str,
) -> Any | None:
    from ce_db.models.insights import ProtocolInsight

    stmt = select(ProtocolInsight).where(
        ProtocolInsight.protocol_key == protocol_key,
        ProtocolInsight.question_category == category,
        ProtocolInsight.insight_type == "contextual",
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _upsert_contextual_insight(
    session: Any,
    protocol_key: str,
    category: str,
    best_synthesis: str | None,
    best_score: float,
) -> None:
    from ce_db.models.insights import ProtocolInsight

    existing = await _get_contextual_insight_single(session, protocol_key, category)
    if existing:
        existing.best_synthesis = best_synthesis
        existing.best_score = best_score
        existing.computed_at = datetime.now(timezone.utc)
    else:
        session.add(ProtocolInsight(
            protocol_key=protocol_key,
            question_category=category,
            insight_type="contextual",
            insight_json={},
            confidence=0.0,
            sample_size=1,
            best_synthesis=best_synthesis,
            best_score=best_score,
            computed_at=datetime.now(timezone.utc),
        ))


async def _count_runs_since_last_compute(
    session: Any, protocol_key: str, categories: list[str],
) -> int:
    from ce_db.models.insights import ProtocolInsight, RunLearning

    last_compute_stmt = (
        select(func.max(ProtocolInsight.computed_at))
        .where(
            ProtocolInsight.protocol_key == protocol_key,
            ProtocolInsight.insight_type == "protocol_comparison",
        )
    )
    result = await session.execute(last_compute_stmt)
    last_computed = result.scalar_one_or_none()

    count_stmt = (
        select(func.count())
        .select_from(RunLearning)
        .where(RunLearning.protocol_key == protocol_key)
    )
    if last_computed:
        count_stmt = count_stmt.where(RunLearning.created_at > last_computed)
    result = await session.execute(count_stmt)
    return result.scalar_one()


async def _recompute_insights(
    session: Any, protocol_key: str, categories: list[str],
) -> None:
    """Recompute protocol_comparison and config_tuning insights."""
    from ce_db.models.insights import ProtocolInsight, RunLearning

    now = datetime.now(timezone.utc)

    for cat in categories:
        if cat == "unclassified":
            continue

        comparison_stmt = (
            select(
                RunLearning.protocol_key,
                func.avg(RunLearning.eval_score).label("avg_score"),
                func.count().label("n"),
            )
            .where(
                RunLearning.eval_score.isnot(None),
                RunLearning.question_categories.op("@>")(f'["{cat}"]'),
            )
            .group_by(RunLearning.protocol_key)
            .having(func.count() >= 3)
        )
        result = await session.execute(comparison_stmt)
        for row in result:
            sample_size = row.n
            await _upsert_insight(
                session,
                protocol_key=row.protocol_key,
                category=cat,
                insight_type="protocol_comparison",
                insight_json={"avg_score": float(row.avg_score), "n": sample_size},
                confidence=min(1.0, sample_size / 20),
                sample_size=sample_size,
                now=now,
            )

        config_stmt = (
            select(
                RunLearning.config_json["rounds"].as_string().label("rounds"),
                func.avg(RunLearning.eval_score).label("avg_score"),
                func.avg(RunLearning.cost_usd).label("avg_cost"),
                func.count().label("n"),
            )
            .where(
                RunLearning.protocol_key == protocol_key,
                RunLearning.eval_score.isnot(None),
                RunLearning.question_categories.op("@>")(f'["{cat}"]'),
            )
            .group_by(RunLearning.config_json["rounds"].as_string())
        )
        result = await session.execute(config_stmt)
        configs = {
            row.rounds: {"avg_score": float(row.avg_score), "avg_cost": float(row.avg_cost), "n": row.n}
            for row in result
        }

        if configs:
            best_rounds = max(configs, key=lambda k: configs[k]["avg_score"])
            total_n = sum(c["n"] for c in configs.values())
            await _upsert_insight(
                session,
                protocol_key=protocol_key,
                category=cat,
                insight_type="config_tuning",
                insight_json={
                    "optimal_rounds": int(best_rounds) if best_rounds and best_rounds != "None" else None,
                    "scores_by_rounds": configs,
                },
                confidence=min(1.0, total_n / 20),
                sample_size=total_n,
                now=now,
            )


async def _upsert_insight(
    session: Any, protocol_key: str, category: str,
    insight_type: str, insight_json: dict, confidence: float,
    sample_size: int, now: datetime,
) -> None:
    from ce_db.models.insights import ProtocolInsight

    stmt = select(ProtocolInsight).where(
        ProtocolInsight.protocol_key == protocol_key,
        ProtocolInsight.question_category == category,
        ProtocolInsight.insight_type == insight_type,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.insight_json = insight_json
        existing.confidence = confidence
        existing.sample_size = sample_size
        existing.computed_at = now
    else:
        session.add(ProtocolInsight(
            protocol_key=protocol_key,
            question_category=category,
            insight_type=insight_type,
            insight_json=insight_json,
            confidence=confidence,
            sample_size=sample_size,
            computed_at=now,
        ))
