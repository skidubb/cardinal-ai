"""Extract storable memories from agent responses using a lightweight Claude call."""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from csuite.config import get_settings

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = (
    "Extract key decisions, facts, and analysis conclusions from this response.\n"
    "Return a JSON array of objects, each with:\n"
    '- "memory_type": one of "decision", "analysis", "fact"\n'
    '- "summary": a one-sentence summary (max 200 chars)\n'
    '- "content": the relevant excerpt (max 500 chars)\n\n'
    "Only extract items worth remembering for future conversations. "
    "If nothing is notable, return [].\n"
    "Respond with ONLY the JSON array, no markdown fences."
)


def extract_memories(
    response_text: str,
    role: str,
) -> list[dict[str, Any]]:
    """Extract storable memories from an agent response.

    Uses Haiku for cost efficiency.
    """
    settings = get_settings()
    if not settings.memory_enabled:
        return []

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        prompt = (
            f"Agent role: {role}\n\n"
            f"Response:\n{response_text[:3000]}\n\n"
            f"{EXTRACTION_PROMPT}"
        )
        result = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            temperature=0.0,
            system="You extract structured memories from executive advisor responses.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = result.content[0].text.strip()
        memories = json.loads(text)
        if isinstance(memories, list):
            return memories  # type: ignore[no-any-return]
        return []
    except Exception:
        logger.warning("Memory extraction failed", exc_info=True)
        return []
