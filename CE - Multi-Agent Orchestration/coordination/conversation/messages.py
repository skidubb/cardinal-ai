"""Agent communication protocol — FIPA-inspired performatives and AgentMessage.

Every agent message is wrapped in a performative: a declaration of what
the message is doing, not just what it says. This gives the runtime
structured envelopes it can parse, route, log, and reason about.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Performative(str, Enum):
    """FIPA-inspired performative types for agent communication."""

    # Proposals and requests
    PROPOSE = "propose"                        # "I suggest we do X"
    CALL_FOR_PROPOSAL = "call_for_proposal"    # "I need capability X. Who can handle it?"
    REQUEST = "request"                        # "I am asking a specific agent to do X"

    # Responses
    ACCEPT = "accept"                          # "I will do what was proposed/requested"
    REFUSE = "refuse"                          # "I cannot or should not do this"
    COUNTER_PROPOSE = "counter_propose"        # "I reject but offer an alternative"

    # Information sharing
    INFORM = "inform"                          # "Here is information, no action required"
    QUERY = "query"                            # "I need information"

    # Coordination signals
    SIGNAL_CONVERGENCE = "signal_convergence"  # "I believe we've reached an answer"
    SIGNAL_DIVERGENCE = "signal_divergence"    # "We have NOT converged, here's why"
    ESCALATE = "escalate"                      # "This exceeds agent capabilities"

    # Agent actions (CE AGENTS-specific layer above performatives)
    CONTRIBUTE = "contribute"                  # Generic contribution
    CHALLENGE = "challenge"                    # Dispute with reasoning
    SUPPORT = "support"                        # Endorse with evidence
    SYNTHESIZE = "synthesize"                  # Propose summary of conversation state
    REFRAME = "reframe"                        # Suggest different approach
    RECRUIT = "recruit"                        # Request a capability join
    ABSTAIN = "abstain"                        # "I have nothing useful to add"
    SIGNAL_DONE = "signal_done"               # "The conversation has a sufficient answer"
    SIGNAL_STUCK = "signal_stuck"             # "We are not making progress"


class AgentMessage(BaseModel):
    """A single message in an agent conversation.

    Every message has a structured performative envelope that the
    ConversationRuntime can parse, plus the natural language content.
    """
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)

    # Who
    sender: str                                # Agent ID
    addressee: str | None = None               # Specific agent, or None for broadcast

    # What
    performative: Performative
    content: str                               # Natural language body
    reason: str | None = None                  # Required for refuse, signal_divergence, escalate

    # Threading
    in_reply_to: str | None = None             # message_id this responds to
    thread_id: str | None = None               # Conversation-level thread

    # Confidence and metadata
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    token_cost: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_convergence_signal(self) -> bool:
        return self.performative in (
            Performative.SIGNAL_CONVERGENCE,
            Performative.SIGNAL_DONE,
        )

    @property
    def is_divergence_signal(self) -> bool:
        return self.performative in (
            Performative.SIGNAL_DIVERGENCE,
            Performative.SIGNAL_STUCK,
        )

    @property
    def is_coordination_signal(self) -> bool:
        return self.performative in (
            Performative.SIGNAL_CONVERGENCE,
            Performative.SIGNAL_DIVERGENCE,
            Performative.SIGNAL_DONE,
            Performative.SIGNAL_STUCK,
            Performative.ESCALATE,
            Performative.ABSTAIN,
        )

    @property
    def is_broadcast(self) -> bool:
        return self.addressee is None


class ConversationBoundaries(BaseModel):
    """Hard and soft limits for an open agent conversation."""

    # Hard limits (enforced by runtime)
    max_turns: int = 40
    max_tokens: int = 50000
    max_wall_time_seconds: float = 300.0
    cost_ceiling_usd: float = 5.0

    # Quality gates
    success_criteria: str = ""
    minimum_confidence: float = 0.7

    # Participation rules
    max_active_agents: int = 6
    minimum_contributions: int = 1

    # Convergence
    convergence_threshold: float = 0.6  # Fraction of agents that must signal done

    # Norms (soft guidance injected into agent prompts)
    norms: list[str] = Field(default_factory=lambda: [
        "Challenge proposals with evidence, not repetition",
        "If you agree with a previous statement, add new information or stay silent",
        "Name your uncertainty explicitly",
        "If the conversation is stuck, propose a decomposition or reframe",
    ])
