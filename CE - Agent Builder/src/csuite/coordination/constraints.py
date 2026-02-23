"""
Constraint models, extraction, storage, and validation.

Constraints flow between agents during negotiation rounds.
Hard constraints must be satisfied; soft constraints are preferred.
"""

from __future__ import annotations

import json
import logging
import re
from enum import StrEnum
from typing import Any

import anthropic
from pydantic import BaseModel, Field

from csuite.config import get_settings

logger = logging.getLogger(__name__)


class ConstraintType(StrEnum):
    BUDGET = "budget"
    TIMELINE = "timeline"
    RESOURCE = "resource"
    COMPLIANCE = "compliance"
    STRATEGIC = "strategic"
    TECHNICAL = "technical"
    OPERATIONAL = "operational"


class ConstraintStrength(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class Constraint(BaseModel):
    """A constraint declared by an agent that peers must respect."""

    source_role: str
    constraint_type: ConstraintType
    description: str
    value: str = ""
    strength: ConstraintStrength = ConstraintStrength.HARD
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConstraintStore:
    """In-memory constraint store for a single event/negotiation."""

    def __init__(self) -> None:
        self.constraints: list[Constraint] = []

    def add(self, constraint: Constraint) -> None:
        self.constraints.append(constraint)

    def add_many(self, constraints: list[Constraint]) -> None:
        self.constraints.extend(constraints)

    def get_for_role(self, role: str) -> list[Constraint]:
        """Get constraints declared BY a specific role."""
        return [c for c in self.constraints if c.source_role == role]

    def get_peer_constraints(self, role: str) -> list[Constraint]:
        """Get constraints declared by OTHER roles (what this role must respect)."""
        return [c for c in self.constraints if c.source_role != role]

    def get_hard_constraints(self) -> list[Constraint]:
        return [c for c in self.constraints if c.strength == ConstraintStrength.HARD]

    def format_for_prompt(self, exclude_role: str = "") -> str:
        """Format all constraints for injection into agent prompts."""
        relevant = self.get_peer_constraints(exclude_role) if exclude_role else self.constraints
        if not relevant:
            return "_No constraints declared yet._"

        lines = []
        for c in relevant:
            strength_tag = "[HARD]" if c.strength == ConstraintStrength.HARD else "[SOFT]"
            lines.append(
                f"- {strength_tag} **{c.source_role.upper()}** ({c.constraint_type.value}): "
                f"{c.description}"
                + (f" — Value: {c.value}" if c.value else "")
            )
        return "\n".join(lines)


EXTRACTION_PROMPT = """\
Extract constraints from the following executive response. A constraint is a \
requirement, limit, or condition that other executives' plans must respect.

Return a JSON array of constraint objects. Each object must have:
- "constraint_type": one of: budget, timeline, resource, compliance, \
strategic, technical, operational
- "description": clear statement of the constraint
- "value": specific numeric or measurable value if applicable ("" if none)
- "strength": "hard" if non-negotiable, "soft" if preferred but flexible

If no constraints are found, return an empty array: []

Example:
[{{"constraint_type": "budget", "description": "Max 15% of revenue", \
"value": "15%", "strength": "hard"}}]

Executive role: {role}
Response:
{response}

Return ONLY the JSON array, no other text.
"""


class ConstraintExtractor:
    """Extracts Constraint objects from agent responses using a Haiku call."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def extract(self, role: str, response: str) -> list[Constraint]:
        """Extract constraints from an agent's response text."""
        try:
            result = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                temperature=0.0,
                messages=[{
                    "role": "user",
                    "content": EXTRACTION_PROMPT.format(role=role, response=response[:3000]),
                }],
            )
            text = result.content[0].text.strip()
            # Extract JSON array from response
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if not match:
                return []
            items = json.loads(match.group())
            constraints = []
            for item in items:
                constraints.append(Constraint(
                    source_role=role,
                    constraint_type=ConstraintType(item.get("constraint_type", "strategic")),
                    description=item.get("description", ""),
                    value=item.get("value", ""),
                    strength=ConstraintStrength(item.get("strength", "soft")),
                ))
            return constraints
        except Exception:
            logger.warning("Constraint extraction failed for %s", role, exc_info=True)
            return []


VALIDATION_PROMPT = """\
Given the following plan from {role} and the constraints it must satisfy, \
check which constraints are satisfied and which are violated.

Plan:
{plan}

Constraints to check:
{constraints}

Return a JSON object with:
- "satisfied": array of constraint descriptions that ARE satisfied
- "violated": array of objects with "description" and "reason" for violations
- "overall_feasible": boolean — true if all HARD constraints are satisfied

Return ONLY the JSON object, no other text.
"""


class ConstraintValidator:
    """Validates whether an agent's plan satisfies declared constraints."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def validate(
        self, role: str, plan: str, constraints: list[Constraint]
    ) -> dict[str, Any]:
        """Check if a plan satisfies the given constraints.

        Returns dict with keys: satisfied, violated, overall_feasible.
        """
        if not constraints:
            return {"satisfied": [], "violated": [], "overall_feasible": True}

        constraint_text = "\n".join(
            f"- [{c.strength.value.upper()}] {c.source_role.upper()} ({c.constraint_type.value}): "
            f"{c.description}" + (f" — {c.value}" if c.value else "")
            for c in constraints
        )

        try:
            result = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                temperature=0.0,
                messages=[{
                    "role": "user",
                    "content": VALIDATION_PROMPT.format(
                        role=role, plan=plan[:3000], constraints=constraint_text
                    ),
                }],
            )
            text = result.content[0].text.strip()
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return {"satisfied": [], "violated": [], "overall_feasible": True}
            return json.loads(match.group())
        except Exception:
            logger.warning("Constraint validation failed for %s", role, exc_info=True)
            return {"satisfied": [], "violated": [], "overall_feasible": True}
