"""ConversationRuntime — manages open agent conversations with boundaries.

The runtime holds a ConversationThread, enforces boundaries, handles
turn opportunities, checks convergence signals, and parses performatives.
This is the in-memory Phase 1 implementation.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from coordination.conversation.messages import (
    AgentMessage,
    ConversationBoundaries,
    Performative,
)

logger = logging.getLogger(__name__)


class ConversationState(BaseModel):
    """Current state of a conversation, visible to agents."""
    turn_number: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    elapsed_seconds: float = 0.0
    active_agents: list[str] = Field(default_factory=list)
    convergence_signals: int = 0
    divergence_signals: int = 0
    is_converged: bool = False
    is_terminated: bool = False
    termination_reason: str | None = None


class ConversationThread(BaseModel):
    """Ordered list of AgentMessages — the full conversation trace."""
    thread_id: str
    messages: list[AgentMessage] = Field(default_factory=list)
    boundaries: ConversationBoundaries = Field(default_factory=ConversationBoundaries)

    def add_message(self, message: AgentMessage) -> None:
        message.thread_id = self.thread_id
        self.messages.append(message)

    def get_messages_by_sender(self, sender: str) -> list[AgentMessage]:
        return [m for m in self.messages if m.sender == sender]

    def get_messages_by_performative(self, performative: Performative) -> list[AgentMessage]:
        return [m for m in self.messages if m.performative == performative]

    def get_proposal_chain(self, proposal_id: str) -> list[AgentMessage]:
        """Get all messages in a proposal/response chain."""
        chain = []
        for m in self.messages:
            if m.message_id == proposal_id or m.in_reply_to == proposal_id:
                chain.append(m)
        return chain

    @property
    def turn_count(self) -> int:
        return len(self.messages)

    @property
    def total_tokens(self) -> int:
        return sum(int(m.metadata.get("tokens", 0)) for m in self.messages)

    @property
    def total_cost(self) -> float:
        return sum(m.token_cost for m in self.messages)

    @property
    def unique_contributors(self) -> set[str]:
        return {m.sender for m in self.messages if m.performative != Performative.ABSTAIN}


class ConversationRuntime:
    """Manages an open agent conversation with boundary enforcement.

    Responsibilities:
    - Enforce hard boundaries (turns, tokens, cost, time)
    - Track convergence/divergence signals
    - Detect termination conditions
    - Provide state to agents for turn decisions
    - Parse performatives for structured analysis
    """

    def __init__(
        self,
        thread_id: str,
        boundaries: ConversationBoundaries | None = None,
        agent_pool: list[str] | None = None,
    ):
        self.thread = ConversationThread(
            thread_id=thread_id,
            boundaries=boundaries or ConversationBoundaries(),
        )
        self.agent_pool = agent_pool or []
        self._start_time = time.time()
        self._convergence_agents: set[str] = set()
        self._divergence_agents: set[str] = set()
        self._abstained_agents: set[str] = set()
        self._escalation_flags: list[AgentMessage] = []

    def get_state(self) -> ConversationState:
        """Get current conversation state for agent context."""
        elapsed = time.time() - self._start_time
        is_converged, reason = self._check_convergence()
        is_terminated, term_reason = self._check_termination()

        return ConversationState(
            turn_number=self.thread.turn_count,
            total_tokens_used=self.thread.total_tokens,
            total_cost_usd=self.thread.total_cost,
            elapsed_seconds=elapsed,
            active_agents=[a for a in self.agent_pool if a not in self._abstained_agents],
            convergence_signals=len(self._convergence_agents),
            divergence_signals=len(self._divergence_agents),
            is_converged=is_converged,
            is_terminated=is_terminated or is_converged,
            termination_reason=term_reason or reason,
        )

    def accept_message(self, message: AgentMessage) -> tuple[bool, str | None]:
        """Accept a message into the thread. Returns (accepted, rejection_reason).

        Enforces boundaries and updates convergence tracking.
        """
        # Check hard boundaries
        state = self.get_state()
        if state.is_terminated:
            return False, f"Conversation terminated: {state.termination_reason}"

        if self.thread.turn_count >= self.thread.boundaries.max_turns:
            return False, "Max turns reached"

        if state.elapsed_seconds >= self.thread.boundaries.max_wall_time_seconds:
            return False, "Wall time limit reached"

        if state.total_cost_usd >= self.thread.boundaries.cost_ceiling_usd:
            return False, "Cost ceiling reached"

        # Accept the message
        self.thread.add_message(message)

        # Update convergence tracking
        if message.is_convergence_signal:
            self._convergence_agents.add(message.sender)
            self._divergence_agents.discard(message.sender)
        elif message.is_divergence_signal:
            self._divergence_agents.add(message.sender)
            self._convergence_agents.discard(message.sender)
        elif message.performative == Performative.ABSTAIN:
            self._abstained_agents.add(message.sender)
        elif message.performative == Performative.ESCALATE:
            self._escalation_flags.append(message)

        return True, None

    def _check_convergence(self) -> tuple[bool, str | None]:
        """Check if convergence threshold is met."""
        active = [a for a in self.agent_pool if a not in self._abstained_agents]
        if not active:
            return False, None

        threshold = self.thread.boundaries.convergence_threshold
        ratio = len(self._convergence_agents) / len(active)
        if ratio >= threshold:
            return True, f"Convergence: {len(self._convergence_agents)}/{len(active)} agents signaled done"
        return False, None

    def _check_termination(self) -> tuple[bool, str | None]:
        """Check if any hard boundary is hit."""
        state_elapsed = time.time() - self._start_time

        if self.thread.turn_count >= self.thread.boundaries.max_turns:
            return True, "Max turns reached"
        if state_elapsed >= self.thread.boundaries.max_wall_time_seconds:
            return True, "Wall time limit reached"
        if self.thread.total_cost >= self.thread.boundaries.cost_ceiling_usd:
            return True, "Cost ceiling reached"
        return False, None

    def detect_negotiation_loops(self, max_depth: int = 3) -> list[str]:
        """Detect counter-propose chains that haven't resolved."""
        loops = []
        proposals = self.thread.get_messages_by_performative(Performative.PROPOSE)
        for proposal in proposals:
            chain = self.thread.get_proposal_chain(proposal.message_id)
            counter_count = sum(
                1 for m in chain if m.performative == Performative.COUNTER_PROPOSE
            )
            if counter_count >= max_depth:
                loops.append(
                    f"Negotiation loop on proposal {proposal.message_id}: "
                    f"{counter_count} counter-proposals without resolution"
                )
        return loops

    def get_agent_stats(self) -> dict[str, dict[str, Any]]:
        """Get per-agent statistics for calibration and analysis."""
        stats: dict[str, dict[str, Any]] = {}
        for agent_id in self.agent_pool:
            messages = self.thread.get_messages_by_sender(agent_id)
            stats[agent_id] = {
                "message_count": len(messages),
                "avg_confidence": (
                    sum(m.confidence for m in messages) / len(messages)
                    if messages else 0.0
                ),
                "performative_counts": {},
                "total_cost": sum(m.token_cost for m in messages),
                "abstained": agent_id in self._abstained_agents,
                "signaled_convergence": agent_id in self._convergence_agents,
            }
            for m in messages:
                perf = m.performative.value
                stats[agent_id]["performative_counts"][perf] = (
                    stats[agent_id]["performative_counts"].get(perf, 0) + 1
                )
        return stats

    def get_escalation_flags(self) -> list[AgentMessage]:
        """Get all escalation messages for human review."""
        return list(self._escalation_flags)

    def to_trace(self) -> dict[str, Any]:
        """Export full conversation trace for RunRecord logging."""
        return {
            "thread_id": self.thread.thread_id,
            "turn_count": self.thread.turn_count,
            "total_tokens": self.thread.total_tokens,
            "total_cost": self.thread.total_cost,
            "elapsed_seconds": time.time() - self._start_time,
            "unique_contributors": list(self.thread.unique_contributors),
            "convergence_agents": list(self._convergence_agents),
            "divergence_agents": list(self._divergence_agents),
            "abstained_agents": list(self._abstained_agents),
            "escalation_count": len(self._escalation_flags),
            "negotiation_loops": self.detect_negotiation_loops(),
            "agent_stats": self.get_agent_stats(),
            "messages": [m.model_dump() for m in self.thread.messages],
            "boundaries": self.thread.boundaries.model_dump(),
        }
