"""InteractionPattern schema and the 8 canonical agent coordination topologies.

These define HOW agents coordinate, separate from WHAT they do (primitives).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PatternType(str, Enum):
    """The 8 canonical interaction topologies."""
    SEQUENTIAL_HANDOFF = "sequential_handoff"
    DEBATE = "debate"
    HIERARCHICAL_DELEGATION = "hierarchical_delegation"
    CONSENSUS = "consensus"
    BLACKBOARD = "blackboard"
    AUCTION = "auction"
    ESCALATION_CHAIN = "escalation_chain"
    GENERATIVE_ADVERSARIAL = "generative_adversarial"
    OPEN_CONVERSATION = "open_conversation"  # 9th: the discovery mode


class AgentRole(BaseModel):
    """A role an agent can fill within an interaction pattern."""
    role_name: str
    description: str
    min_agents: int = 1
    max_agents: int = 1
    capabilities_required: list[str] = Field(default_factory=list)


class TerminationCondition(BaseModel):
    """When a pattern-based execution should stop."""
    max_rounds: int | None = None
    convergence_threshold: float | None = None
    cost_ceiling_usd: float | None = None
    time_limit_seconds: float | None = None


class InteractionPattern(BaseModel):
    """A reusable agent coordination topology.

    Defines the structural shape of how agents work together.
    Selected by L2 routing based on ProblemProfile.
    """
    pattern_type: PatternType
    name: str
    description: str
    agent_roles: list[AgentRole] = Field(default_factory=list)
    communication_rules: list[str] = Field(default_factory=list)
    termination: TerminationCondition = Field(default_factory=TerminationCondition)
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    best_for: list[str] = Field(default_factory=list)


# ── Seed patterns from existing protocol library ──────────────────────────────

SEQUENTIAL_HANDOFF = InteractionPattern(
    pattern_type=PatternType.SEQUENTIAL_HANDOFF,
    name="Sequential Handoff",
    description="Agent A completes a primitive, passes output to Agent B for the next.",
    agent_roles=[
        AgentRole(role_name="upstream", description="Completes initial work"),
        AgentRole(role_name="downstream", description="Builds on upstream output"),
    ],
    communication_rules=[
        "Output of each agent becomes input to the next",
        "No backtracking unless explicitly triggered",
    ],
    termination=TerminationCondition(max_rounds=1),
    strengths=["Low cost", "Clear accountability", "Easy to trace"],
    risks=["Upstream errors propagate without correction"],
    best_for=["Clean decomposition", "Low ambiguity", "Pipeline-shaped problems"],
)

DEBATE = InteractionPattern(
    pattern_type=PatternType.DEBATE,
    name="Debate",
    description="Two or more agents generate competing outputs, then a judge scores or reconciles.",
    agent_roles=[
        AgentRole(role_name="debater", description="Argues a position", min_agents=2, max_agents=6),
        AgentRole(role_name="judge", description="Evaluates and scores arguments"),
    ],
    communication_rules=[
        "Each round: all debaters respond in parallel",
        "Debaters see all prior arguments",
        "Judge scores or reconciles after each round",
    ],
    termination=TerminationCondition(max_rounds=5),
    strengths=["Robustness through adversarial testing", "Surfaces hidden assumptions"],
    risks=["Expensive", "Can stalemate without clear criteria"],
    best_for=["High ambiguity", "Adversarial evidence", "Need for robustness"],
)

HIERARCHICAL_DELEGATION = InteractionPattern(
    pattern_type=PatternType.HIERARCHICAL_DELEGATION,
    name="Hierarchical Delegation",
    description="A lead agent decomposes the problem, assigns subproblems to specialists, then synthesizes.",
    agent_roles=[
        AgentRole(role_name="lead", description="Decomposes and synthesizes"),
        AgentRole(role_name="specialist", description="Handles assigned subproblem", min_agents=2, max_agents=6),
    ],
    communication_rules=[
        "Lead decomposes first, then assigns",
        "Specialists work in parallel on assigned subproblems",
        "Lead synthesizes specialist outputs",
    ],
    termination=TerminationCondition(max_rounds=1),
    strengths=["Scales well", "Leverages specialization"],
    risks=["Lead becomes bottleneck", "Decomposition quality determines ceiling"],
    best_for=["Complex multi-part problems", "Domain specialization required"],
)

CONSENSUS = InteractionPattern(
    pattern_type=PatternType.CONSENSUS,
    name="Consensus",
    description="Multiple agents independently produce outputs, then iteratively converge through mutual critique.",
    agent_roles=[
        AgentRole(role_name="contributor", description="Produces output and critiques others", min_agents=3, max_agents=6),
    ],
    communication_rules=[
        "Round 1: independent outputs",
        "Round 2+: critique and revise based on peer outputs",
        "Converge when critiques become minor",
    ],
    termination=TerminationCondition(max_rounds=5, convergence_threshold=0.8),
    strengths=["High-quality for subjective tasks", "No single point of failure"],
    risks=["Groupthink", "Convergence to mediocrity", "High token cost"],
    best_for=["High-stakes decisions", "Subjective evaluation criteria"],
)

BLACKBOARD = InteractionPattern(
    pattern_type=PatternType.BLACKBOARD,
    name="Blackboard",
    description="Agents read from and write to a shared state, contributing asynchronously.",
    agent_roles=[
        AgentRole(role_name="contributor", description="Reads shared state, contributes when relevant", min_agents=2, max_agents=8),
    ],
    communication_rules=[
        "Shared state is visible to all agents",
        "Agents contribute when they have relevant input",
        "No enforced turn order",
    ],
    termination=TerminationCondition(max_rounds=10),
    strengths=["Handles loosely coupled subtasks", "Flexible"],
    risks=["Coordination overhead", "Stale reads", "Write conflicts"],
    best_for=["Loosely coupled subtasks", "Evolving problem definition"],
)

AUCTION = InteractionPattern(
    pattern_type=PatternType.AUCTION,
    name="Auction",
    description="Agents bid on subtasks based on self-assessed competence, router assigns based on bids.",
    agent_roles=[
        AgentRole(role_name="bidder", description="Bids on subtasks based on competence", min_agents=3, max_agents=10),
        AgentRole(role_name="auctioneer", description="Evaluates bids and assigns work"),
    ],
    communication_rules=[
        "Auctioneer announces subtasks",
        "Bidders submit competence scores and cost estimates",
        "Auctioneer assigns to best-fit bidder",
    ],
    termination=TerminationCondition(max_rounds=1),
    strengths=["Cost-efficient", "Self-organizing", "Load balancing"],
    risks=["Agents may overestimate competence", "Requires calibrated self-assessment"],
    best_for=["Heterogeneous agent capabilities", "Cost-sensitive routing"],
)

ESCALATION_CHAIN = InteractionPattern(
    pattern_type=PatternType.ESCALATION_CHAIN,
    name="Escalation Chain",
    description="Agent attempts a primitive, self-evaluates confidence, escalates if below threshold.",
    agent_roles=[
        AgentRole(role_name="first_responder", description="Cheap agent that tries first"),
        AgentRole(role_name="escalation_target", description="More capable agent for hard cases"),
    ],
    communication_rules=[
        "First responder attempts the task",
        "Self-evaluates confidence after attempt",
        "Escalates if confidence < threshold",
    ],
    termination=TerminationCondition(max_rounds=3),
    strengths=["Cost optimization", "Handles variable difficulty"],
    risks=["Poor self-assessment leads to silent failure or unnecessary escalation"],
    best_for=["Variable difficulty", "Cost optimization"],
)

GENERATIVE_ADVERSARIAL = InteractionPattern(
    pattern_type=PatternType.GENERATIVE_ADVERSARIAL,
    name="Generative Adversarial",
    description="One agent generates, another attacks/critiques, generator revises, cycle repeats.",
    agent_roles=[
        AgentRole(role_name="generator", description="Produces and revises output"),
        AgentRole(role_name="adversary", description="Attacks and critiques output"),
    ],
    communication_rules=[
        "Generator produces output",
        "Adversary attacks with specific critiques",
        "Generator revises based on critiques",
        "Cycle repeats until convergence or budget",
    ],
    termination=TerminationCondition(max_rounds=5),
    strengths=["High output quality", "Systematic improvement"],
    risks=["Adversary becomes predictable", "Generator learns to game"],
    best_for=["Critical output quality", "High failure cost", "Creative tasks"],
)

OPEN_CONVERSATION = InteractionPattern(
    pattern_type=PatternType.OPEN_CONVERSATION,
    name="Open Conversation",
    description="Agents converse freely within boundary constraints. Structure is emergent.",
    agent_roles=[
        AgentRole(role_name="participant", description="Self-selects contributions", min_agents=2, max_agents=6),
    ],
    communication_rules=[
        "No enforced turn order",
        "Agents speak when they have signal",
        "Challenge proposals with evidence, not repetition",
        "Name uncertainty explicitly",
    ],
    termination=TerminationCondition(max_rounds=40, cost_ceiling_usd=5.0, time_limit_seconds=300),
    strengths=["Discovery mode", "Handles novel problems", "Emergent coordination"],
    risks=["Expensive", "May not converge", "Requires good boundary design"],
    best_for=["Novel problems", "High ambiguity", "Pattern discovery"],
)

# Registry of all canonical patterns
PATTERN_REGISTRY: dict[PatternType, InteractionPattern] = {
    PatternType.SEQUENTIAL_HANDOFF: SEQUENTIAL_HANDOFF,
    PatternType.DEBATE: DEBATE,
    PatternType.HIERARCHICAL_DELEGATION: HIERARCHICAL_DELEGATION,
    PatternType.CONSENSUS: CONSENSUS,
    PatternType.BLACKBOARD: BLACKBOARD,
    PatternType.AUCTION: AUCTION,
    PatternType.ESCALATION_CHAIN: ESCALATION_CHAIN,
    PatternType.GENERATIVE_ADVERSARIAL: GENERATIVE_ADVERSARIAL,
    PatternType.OPEN_CONVERSATION: OPEN_CONVERSATION,
}
