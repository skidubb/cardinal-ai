"""Pre/post run hooks for protocol learning layer."""

from __future__ import annotations

import logging
import uuid as uuid_mod
from typing import Any

from anthropic import AsyncAnthropic

from protocols.learning.classifier import classify_question
from protocols.learning.recorder import record_learning
from protocols.learning.retriever import RunInsights, retrieve_insights

logger = logging.getLogger(__name__)


async def pre_run_hook(
    client: AsyncAnthropic,
    protocol_key: str,
    question: str,
    agents: list[Any],
    user_config: dict,
) -> tuple[dict, list[str]]:
    """Pre-run: classify, retrieve insights, inject into agents."""
    try:
        categories = await classify_question(client, question)
        insights = await retrieve_insights(protocol_key, question, categories)

        if insights.recommended_protocol and insights.recommended_protocol != protocol_key:
            logger.info(
                f"[Learning] {insights.recommended_protocol} scored "
                f"{insights.protocol_scores.get(insights.recommended_protocol, '?'):.1f} avg "
                f"vs {protocol_key} at "
                f"{insights.protocol_scores.get(protocol_key, '?')} "
                f"for {categories} (n={insights.sample_size})"
            )

        updated_config = dict(user_config)
        if insights.confidence > 0.6:
            if insights.optimal_rounds and not user_config.get("rounds"):
                updated_config["rounds"] = insights.optimal_rounds
                logger.info(f"[Learning] Auto-set rounds={insights.optimal_rounds}")

        if insights.institutional_memory:
            for agent in agents:
                if hasattr(agent, "institutional_memory"):
                    agent.institutional_memory = insights.institutional_memory

        return updated_config, categories
    except Exception as e:
        logger.warning(f"pre_run_hook failed (degrading): {e}")
        return dict(user_config), ["unclassified"]


async def post_run_hook(
    run_id: str | int | None,
    protocol_key: str,
    question: str,
    question_categories: list[str],
    eval_score: float | None,
    config: dict,
    synthesis_text: str,
    cost_summary: dict,
) -> None:
    """Post-run: record learning. Non-blocking."""
    try:
        await record_learning(
            run_id=run_id,
            protocol_key=protocol_key,
            question=question,
            question_categories=question_categories,
            eval_score=eval_score,
            config=config,
            synthesis_text=synthesis_text,
            cost_summary=cost_summary,
        )
    except Exception as e:
        logger.warning(f"post_run_hook failed (non-blocking): {e}")
