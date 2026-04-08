"""Classify questions into categories for insight matching."""

from __future__ import annotations

import json
import logging
import re

from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

QUESTION_CATEGORIES = [
    "innovation",
    "pricing",
    "risk",
    "strategy",
    "operations",
    "growth",
    "talent",
    "technology",
    "financial",
]

_CATEGORIES_STR = ", ".join(QUESTION_CATEGORIES)


async def classify_question(
    client: AsyncAnthropic,
    question: str,
    model: str = "claude-haiku-4-5-20251001",
) -> list[str]:
    """Classify question into 1-2 categories using Haiku. ~$0.001/call."""
    try:
        from protocols.llm import llm_complete

        response = await llm_complete(
            client,
            agent_name="classifier",
            model=model,
            messages=[{
                "role": "user",
                "content": (
                    f"Classify this business question into 1-2 categories.\n"
                    f"Categories: {_CATEGORIES_STR}\n\n"
                    f"Question: {question}\n\n"
                    f'Return ONLY a JSON array: ["category1"] or ["category1", "category2"]'
                ),
            }],
            max_tokens=50,
        )
        return _parse_categories(response)
    except Exception as e:
        logger.warning(f"classify_question failed: {e}")
        return ["unclassified"]


def _parse_categories(raw: str) -> list[str]:
    """Parse classifier response. Handles JSON, markdown fences, invalid categories."""
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            valid = [c for c in parsed if c in QUESTION_CATEGORIES]
            return valid if valid else ["unclassified"]
    except (json.JSONDecodeError, TypeError):
        pass
    return ["unclassified"]
