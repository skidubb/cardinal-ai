"""Cardinal Element entity types for the knowledge graph.

These are Pydantic models that double as Graphiti node schemas. Every node
carries a ``source`` reference for provenance and ``valid_from`` / ``valid_to``
fields for temporal validity (managed by Graphiti).

Design principle: model the consulting practice, not generic agent memory.
Every entity here exists because a C-Suite agent needs to query it.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EngagementType(str, Enum):
    AUDIT = "audit"
    IMPLEMENTATION = "implementation"
    ADVISORY = "advisory"
    RETAINER = "retainer"
    DISCOVERY = "discovery"


class EngagementStatus(str, Enum):
    PROSPECTING = "prospecting"
    PROPOSED = "proposed"
    ACTIVE = "active"
    COMPLETED = "completed"
    LOST = "lost"
    PAUSED = "paused"


class ClientStatus(str, Enum):
    PROSPECT = "prospect"
    ACTIVE = "active"
    PAST = "past"
    DISQUALIFIED = "disqualified"


class CorrectionScope(str, Enum):
    """What a correction attaches to."""
    GLOBAL = "global"
    CLIENT = "client"
    ENGAGEMENT = "engagement"
    PROTOCOL = "protocol"
    AGENT = "agent"
    DECISION = "decision"


class SourceType(str, Enum):
    GRANOLA_TRANSCRIPT = "granola_transcript"
    NOTION_PAGE = "notion_page"
    SLACK_MESSAGE = "slack_message"
    EMAIL_THREAD = "email_thread"
    CLI_SESSION = "cli_session"
    WEB_UI_SESSION = "web_ui_session"
    PROTOCOL_RUN = "protocol_run"
    MANUAL_ENTRY = "manual_entry"


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class GraphNode(BaseModel):
    """Base for all graph nodes. Carries Graphiti temporal fields."""

    id: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    summary: str | None = Field(
        default=None,
        description="Single-sentence summary used by Graphiti for retrieval.",
    )

    class Config:
        use_enum_values = True


# ---------------------------------------------------------------------------
# Core domain entities
# ---------------------------------------------------------------------------


class Vertical(GraphNode):
    """Industry vertical. Used for cross-engagement pattern matching."""

    name: str = Field(..., description="e.g. 'B2B SaaS', 'Professional Services', 'Fintech'")
    description: str | None = None


class Client(GraphNode):
    """A Cardinal Element client (or prospect)."""

    name: str = Field(..., description="Legal or working name, normalized lowercase for lookup")
    display_name: str | None = None
    vertical: str | None = Field(None, description="Reference to Vertical.name")
    size: Literal["startup", "growth", "mid_market", "enterprise"] | None = None
    status: ClientStatus = ClientStatus.PROSPECT
    website: str | None = None
    notes: str | None = None


class Person(GraphNode):
    """A human contact (at a client, partner, or internal team)."""

    name: str
    email: str | None = None
    role: str | None = Field(None, description="Job title at time of contact")
    client_name: str | None = Field(
        None, description="Client they belong to, if any"
    )
    notes: str | None = None


class Engagement(GraphNode):
    """A single client engagement (audit, implementation, etc.)."""

    name: str = Field(..., description="Human-readable engagement name")
    client_name: str = Field(..., description="Reference to Client.name")
    type: EngagementType
    status: EngagementStatus = EngagementStatus.PROSPECTING
    started_at: datetime | None = None
    ended_at: datetime | None = None
    value_usd: float | None = Field(None, description="Engagement value in USD")
    primary_contact: str | None = Field(None, description="Reference to Person.name")
    objective: str | None = Field(None, description="What success looks like")
    outcome: str | None = Field(None, description="What actually happened (post-engagement)")


class Protocol(GraphNode):
    """One of the 55 coordination protocols. Seeded from the codebase."""

    code: str = Field(..., description="e.g. 'P04', 'P0a'")
    name: str = Field(..., description="e.g. 'Multi-Round Debate'")
    category: str = Field(
        ...,
        description="adversarial | debate | forecasting | decomposition | "
        "prioritization | routing | sense_making | estimation | meta",
    )
    methodology: str | None = Field(
        None, description="Source methodology / academic origin"
    )
    cost_tier: Literal["low", "medium", "high"] = "medium"
    min_agents: int = 1
    max_agents: int = 8


class Agent(GraphNode):
    """A C-Suite executive or sub-agent role."""

    key: str = Field(..., description="Kebab-case agent key, e.g. 'cfo', 'gtm-vp-sales'")
    title: str = Field(..., description="Display title")
    layer: Literal["c_suite", "direct_report", "functional"] = "functional"
    reports_to: str | None = Field(None, description="Parent agent key (for hierarchy)")
    description: str | None = None


class Decision(GraphNode):
    """A decision, recommendation, or output from a protocol run."""

    summary: str = Field(..., description="One-line summary of what was decided")
    rationale: str | None = Field(None, description="Why this decision")
    engagement_name: str | None = None
    protocol_code: str | None = Field(None, description="Which protocol produced this")
    agent_keys: list[str] = Field(
        default_factory=list, description="Agents that contributed"
    )
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    eval_score: float | None = Field(None, description="Post-hoc eval score, 0-5")
    decided_at: datetime | None = None


class Deliverable(GraphNode):
    """Anything produced for or shown to a client."""

    name: str
    type: Literal["audit_report", "blueprint", "deck", "memo", "model", "other"] = "memo"
    engagement_name: str | None = None
    file_path: str | None = None
    delivered_at: datetime | None = None


class Correction(GraphNode):
    """A correction Scott (or anyone) gave that should change future behavior.

    THIS IS THE KILLER NODE. Corrections attach to a scope (Client, Protocol,
    Agent, Decision, or globally). Every future agent action that touches
    that scope reads applicable corrections first.
    """

    text: str = Field(..., description="The correction itself, in natural language")
    scope: CorrectionScope
    target_id: str | None = Field(
        None,
        description="ID of the scoped entity (Client.name, Protocol.code, "
        "Agent.key, Decision.id). None for GLOBAL.",
    )
    given_by: str = Field("scott", description="Who gave the correction")
    reason: str | None = Field(None, description="Why this correction exists")
    given_at: datetime | None = None


class Lesson(GraphNode):
    """A generalization derived from one or more decisions/outcomes."""

    statement: str = Field(..., description="The lesson, generalized")
    derived_from_decision_ids: list[str] = Field(default_factory=list)
    applies_to_vertical: str | None = None
    applies_to_engagement_type: EngagementType | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)


class Source(GraphNode):
    """Provenance for any fact or node. Where did this come from?"""

    type: SourceType
    identifier: str = Field(
        ..., description="External ID: notion page id, granola meeting id, etc."
    )
    url: str | None = None
    captured_at: datetime | None = None
    title: str | None = None


# ---------------------------------------------------------------------------
# Edge type constants (for Cypher queries)
# ---------------------------------------------------------------------------


class EdgeType:
    """Canonical edge labels used in Cypher queries."""

    FOR_CLIENT = "FOR_CLIENT"
    USED_PROTOCOL = "USED_PROTOCOL"
    MADE_BY = "MADE_BY"
    IN_ENGAGEMENT = "IN_ENGAGEMENT"
    USING_PROTOCOL = "USING_PROTOCOL"
    PRODUCED = "PRODUCED"
    APPLIES_TO = "APPLIES_TO"
    GIVEN_BY = "GIVEN_BY"
    DERIVED_FROM = "DERIVED_FROM"
    APPLIES_TO_VERTICAL = "APPLIES_TO_VERTICAL"
    APPLIES_TO_ENGAGEMENT_TYPE = "APPLIES_TO_ENGAGEMENT_TYPE"
    SOURCED_FROM = "SOURCED_FROM"
    CONTACT_AT = "CONTACT_AT"
    REPORTS_TO = "REPORTS_TO"
    SUPERSEDED_BY = "SUPERSEDED_BY"


__all__ = [
    "Agent",
    "Client",
    "ClientStatus",
    "Correction",
    "CorrectionScope",
    "Decision",
    "Deliverable",
    "EdgeType",
    "Engagement",
    "EngagementStatus",
    "EngagementType",
    "GraphNode",
    "Lesson",
    "Person",
    "Protocol",
    "Source",
    "SourceType",
    "Vertical",
]
