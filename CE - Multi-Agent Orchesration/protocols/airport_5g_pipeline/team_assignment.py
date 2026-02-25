"""Dynamic Red/Blue/White team assignment based on Stage 3 constraint scores."""

from __future__ import annotations

import json
import re
from typing import Any

from dotenv import load_dotenv
load_dotenv()

import anthropic

from .prompts import TEAM_ASSIGNMENT_PROMPT


async def assign_teams(
    agents: list[dict[str, str]],
    constraint_table: str,
    negotiation_synthesis: str,
    model: str = "claude-haiku-4-5-20251001",
) -> dict[str, Any]:
    """Dynamically assign Red/Blue/White teams based on negotiation outcomes.

    Returns dict with keys: red_team, blue_team, white_team (lists of agent dicts),
    plus reasoning.
    """
    agents_block = "\n".join(
        f"- {a['name']}: {a.get('role', 'unknown')}" for a in agents
    )

    prompt = TEAM_ASSIGNMENT_PROMPT.format(
        constraint_table=constraint_table,
        negotiation_synthesis=negotiation_synthesis,
        agents_block=agents_block,
    )

    client = anthropic.AsyncAnthropic()
    resp = await client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    text = ""
    for block in resp.content:
        if hasattr(block, "text"):
            text = block.text
            break

    parsed = _parse_json(text)

    # Map agent names back to full agent dicts
    name_map = {a["name"]: a for a in agents}

    def _resolve(names: list[str]) -> list[dict]:
        return [name_map[n] for n in names if n in name_map]

    return {
        "red_team": _resolve(parsed.get("red_team", [])),
        "blue_team": _resolve(parsed.get("blue_team", [])),
        "white_team": _resolve(parsed.get("white_team", [])),
        "reasoning": parsed.get("reasoning", {}),
    }


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM output."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}
