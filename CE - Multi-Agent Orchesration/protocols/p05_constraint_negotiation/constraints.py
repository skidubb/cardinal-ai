"""Constraint extraction and management for P5: Constraint Negotiation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum

import anthropic


class ConstraintType(str, Enum):
    BUDGET = "budget"
    TIMELINE = "timeline"
    RESOURCE = "resource"
    TECHNICAL = "technical"
    REGULATORY = "regulatory"
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"


class ConstraintStrength(str, Enum):
    HARD = "hard"  # Must be satisfied — non-negotiable
    SOFT = "soft"  # Preferred but can be traded


@dataclass
class Constraint:
    source_role: str
    constraint_type: str
    description: str
    value: str
    strength: str  # "hard" or "soft"


@dataclass
class ConstraintStore:
    """Stores and queries constraints across negotiation rounds."""

    constraints: list[Constraint] = field(default_factory=list)

    def add(self, constraint: Constraint) -> None:
        self.constraints.append(constraint)

    def add_many(self, constraints: list[Constraint]) -> None:
        self.constraints.extend(constraints)

    def get_peer_constraints(self, exclude_role: str) -> list[Constraint]:
        """Get all constraints except those from the specified role."""
        return [c for c in self.constraints if c.source_role != exclude_role]

    def get_hard_constraints(self) -> list[Constraint]:
        return [c for c in self.constraints if c.strength == "hard"]

    def format_for_prompt(self, exclude_role: str | None = None) -> str:
        """Format constraints for inclusion in a prompt."""
        items = (
            self.get_peer_constraints(exclude_role)
            if exclude_role
            else self.constraints
        )
        if not items:
            return "(No constraints declared yet.)"

        lines = []
        for c in items:
            strength_label = "HARD (non-negotiable)" if c.strength == "hard" else "SOFT (preferred)"
            lines.append(
                f"- [{c.source_role}] [{strength_label}] {c.constraint_type}: "
                f"{c.description} (value: {c.value})"
            )
        return "\n".join(lines)


CONSTRAINT_EXTRACTION_PROMPT = """\
Extract constraints from the following proposal. A constraint is a specific \
requirement, limit, or condition that the author insists on.

For each constraint, provide:
- "source_role": the role name of the author (given below)
- "constraint_type": one of budget, timeline, resource, technical, regulatory, strategic, operational
- "description": what the constraint requires
- "value": the specific threshold, deadline, or metric (or "N/A" if qualitative)
- "strength": "hard" if non-negotiable/must-have, "soft" if preferred/flexible

Output as a JSON array. If no constraints found, output [].

AUTHOR ROLE: {role_name}

PROPOSAL TEXT:
{proposal_text}"""


class ConstraintExtractor:
    """Extracts constraints from agent proposals using a fast model."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        self.model = model
        self.client = anthropic.AsyncAnthropic()

    async def extract(self, role_name: str, proposal_text: str) -> list[Constraint]:
        """Extract constraints from a single proposal."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": CONSTRAINT_EXTRACTION_PROMPT.format(
                    role_name=role_name, proposal_text=proposal_text
                ),
            }],
        )
        data = _parse_json_array(response.content[0].text)
        return [
            Constraint(
                source_role=item.get("source_role", role_name),
                constraint_type=item.get("constraint_type", "strategic"),
                description=item.get("description", ""),
                value=item.get("value", "N/A"),
                strength=item.get("strength", "soft"),
            )
            for item in data
        ]


def _parse_json_array(text: str) -> list[dict]:
    """Extract a JSON array from LLM output that may contain markdown fences."""
    text = text.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    if not text.startswith("["):
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start : end + 1]
    return json.loads(text)
