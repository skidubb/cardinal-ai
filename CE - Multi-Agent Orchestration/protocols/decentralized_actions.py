"""Shared action models and deterministic aggregation helpers for decentralized protocols.

Decentralized protocols in P53-P57 share a common contract:
- Agents emit structured actions (bid / vote / delegate / contribute / halt / reinforce / explore / estimate)
  as JSON responses.
- The orchestrator parses them into these dataclasses and writes them verbatim to the Blackboard.
- Aggregation (winner selection, delegation resolution, variance, pheromone dominance)
  happens via deterministic math in this module - no LLM judgment.

If the orchestrator ever calls an LLM to "pick the best" or "synthesize across contributions,"
that protocol does not meet the four-dimension decentralization bar. This module exists
precisely so that aggregation can stay mechanical.
"""

from __future__ import annotations

import json
import re
import statistics
import uuid
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Structured action dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Bid:
    agent: str
    task_id: str
    fit_score: float
    confidence: float
    cost_estimate: int
    approach: str


@dataclass
class Vote:
    agent: str
    ranking: list[str]


@dataclass
class Delegation:
    agent: str
    to: str
    topic: str


@dataclass
class Contribution:
    agent: str
    topic: str
    content: str
    relevance: float


@dataclass
class Halt:
    agent: str
    reason: str


@dataclass
class Estimate:
    agent: str
    value: float
    confidence: float
    reasoning: str


@dataclass
class Reinforce:
    agent: str
    path_id: str
    refinement: str


@dataclass
class Explore:
    agent: str
    path_id: str
    description: str


@dataclass
class MalformedAction:
    agent: str
    raw: str
    error: str


# ---------------------------------------------------------------------------
# Action parsers — each returns the dataclass OR MalformedAction, never raises
# ---------------------------------------------------------------------------


def _safe_json(text: str) -> dict | None:
    """Best-effort JSON extraction. Returns dict or None; never raises."""
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None
        return None


def parse_bid(agent: str, text: str) -> Bid | MalformedAction:
    data = _safe_json(text)
    if not data or data.get("action") != "bid":
        return MalformedAction(agent=agent, raw=text[:500], error="not a bid action")
    try:
        return Bid(
            agent=agent,
            task_id=str(data["task_id"]),
            fit_score=float(data.get("fit_score", 0.5)),
            confidence=float(data.get("confidence", 0.5)),
            cost_estimate=int(data.get("cost_estimate", 1)),
            approach=str(data.get("approach", "")),
        )
    except (KeyError, ValueError, TypeError) as e:
        return MalformedAction(agent=agent, raw=text[:500], error=f"bid parse: {e}")


def parse_vote_or_delegate(agent: str, text: str) -> Vote | Delegation | MalformedAction:
    data = _safe_json(text)
    if not data:
        return MalformedAction(agent=agent, raw=text[:500], error="not JSON")
    action = data.get("action")
    if action == "vote":
        ranking = data.get("ranking", [])
        if not isinstance(ranking, list) or not ranking:
            return MalformedAction(agent=agent, raw=text[:500], error="vote missing ranking")
        return Vote(agent=agent, ranking=[str(x) for x in ranking])
    if action == "delegate":
        to = data.get("to")
        if not to:
            return MalformedAction(agent=agent, raw=text[:500], error="delegate missing 'to'")
        return Delegation(agent=agent, to=str(to), topic=str(data.get("topic", "")))
    return MalformedAction(agent=agent, raw=text[:500], error=f"unknown action {action!r}")


def parse_contribution_or_halt(
    agent: str, text: str
) -> Contribution | Halt | MalformedAction:
    data = _safe_json(text)
    if not data:
        return MalformedAction(agent=agent, raw=text[:500], error="not JSON")
    action = data.get("action")
    if action == "contribute":
        return Contribution(
            agent=agent,
            topic=str(data.get("topic", "general")),
            content=str(data.get("content", "")),
            relevance=float(data.get("relevance", 0.5)),
        )
    if action == "halt":
        return Halt(agent=agent, reason=str(data.get("reason", "")))
    return MalformedAction(agent=agent, raw=text[:500], error=f"unknown action {action!r}")


def parse_estimate(agent: str, text: str) -> Estimate | MalformedAction:
    data = _safe_json(text)
    if not data:
        return MalformedAction(agent=agent, raw=text[:500], error="not JSON")
    try:
        return Estimate(
            agent=agent,
            value=float(data["value"]),
            confidence=float(data.get("confidence", 0.5)),
            reasoning=str(data.get("reasoning", "")),
        )
    except (KeyError, ValueError, TypeError) as e:
        return MalformedAction(agent=agent, raw=text[:500], error=f"estimate parse: {e}")


def parse_stigmergic_action(
    agent: str, text: str
) -> Reinforce | Explore | Halt | MalformedAction:
    data = _safe_json(text)
    if not data:
        return MalformedAction(agent=agent, raw=text[:500], error="not JSON")
    action = data.get("action")
    if action == "reinforce":
        path_id = data.get("path_id")
        if not path_id:
            return MalformedAction(agent=agent, raw=text[:500], error="reinforce missing path_id")
        return Reinforce(
            agent=agent, path_id=str(path_id), refinement=str(data.get("refinement", ""))
        )
    if action == "explore":
        return Explore(
            agent=agent,
            path_id=uuid.uuid4().hex[:10],
            description=str(data.get("description", "")),
        )
    if action == "halt":
        return Halt(agent=agent, reason=str(data.get("reason", "")))
    return MalformedAction(agent=agent, raw=text[:500], error=f"unknown action {action!r}")


# ---------------------------------------------------------------------------
# Deterministic aggregation helpers
# ---------------------------------------------------------------------------


def hungarian_assign(bids: list[Bid], tasks: list[str]) -> dict[str, str]:
    """Assign each task to its highest-fit bidder, with no agent getting more than one task
    unless there are more tasks than agents.

    Greedy fit-maximizing assignment. Not the full Hungarian algorithm (which is O(n^3))
    but deterministic and sufficient when tasks/agents are small (<10).

    Returns {task_id: agent_name}. Tasks with no bids are omitted.
    """
    if not bids or not tasks:
        return {}

    bids_by_task: dict[str, list[Bid]] = {t: [] for t in tasks}
    for b in bids:
        if b.task_id in bids_by_task:
            bids_by_task[b.task_id].append(b)

    for t in tasks:
        bids_by_task[t].sort(key=lambda b: (-b.fit_score, b.cost_estimate, b.agent))

    awards: dict[str, str] = {}
    agents_taken: set[str] = set()

    ordered_tasks = sorted(
        tasks,
        key=lambda t: -(bids_by_task[t][0].fit_score if bids_by_task[t] else 0.0),
    )

    n_tasks = len(tasks)
    n_agents = len({b.agent for b in bids})
    allow_multi = n_tasks > n_agents

    for t in ordered_tasks:
        for candidate in bids_by_task[t]:
            if candidate.agent in agents_taken and not allow_multi:
                continue
            awards[t] = candidate.agent
            agents_taken.add(candidate.agent)
            break

    return awards


def resolve_delegations(
    votes: list[Vote], delegations: list[Delegation]
) -> tuple[dict[str, Vote], dict[str, list[str]]]:
    """Resolve delegation chains to effective votes.

    Returns (effective_votes_by_agent, delegate_weight) where:
      - effective_votes_by_agent: {agent_name: Vote they ultimately cast (own or via chain)}
      - delegate_weight: {agent_name: [list of agents whose votes they carry, including themselves]}

    Cycles → affected agents abstain (dropped from effective_votes).
    Chain ending at a non-voter → abstain.
    """
    direct_voters = {v.agent: v for v in votes}
    delegations_by_agent = {d.agent: d for d in delegations}

    effective: dict[str, Vote] = {}
    chains: dict[str, list[str]] = {}

    for a, vote in direct_voters.items():
        effective[a] = vote
        chains.setdefault(a, []).append(a)

    for source_agent, d in delegations_by_agent.items():
        visited = [source_agent]
        current = d.to
        terminal_voter: str | None = None
        while True:
            if current in visited:
                terminal_voter = None
                break
            visited.append(current)
            if current in direct_voters:
                terminal_voter = current
                break
            if current in delegations_by_agent:
                current = delegations_by_agent[current].to
                continue
            terminal_voter = None
            break

        if terminal_voter is None:
            continue

        effective[source_agent] = direct_voters[terminal_voter]
        chains.setdefault(terminal_voter, []).append(source_agent)

    return effective, chains


def weighted_borda(
    effective_votes: dict[str, Vote], options: list[str]
) -> list[tuple[str, float]]:
    """Compute Borda scores from resolved votes, one weight per voter (delegation-weighted).

    Each agent's Vote contributes (n - rank_index) points to each option they ranked.
    Returns [(option_id, score), ...] sorted descending. Deterministic on ties by option_id.
    """
    if not effective_votes or not options:
        return [(o, 0.0) for o in options]

    n = len(options)
    scores: dict[str, float] = {o: 0.0 for o in options}

    for vote in effective_votes.values():
        for idx, opt in enumerate(vote.ranking):
            if opt in scores:
                scores[opt] += n - idx

    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def confidence_weighted_mean(estimates: list[Estimate]) -> float:
    """Weighted mean of estimate values using confidence as weight.

    Falls back to simple mean if all confidences are zero.
    """
    if not estimates:
        return 0.0
    total_weight = sum(max(e.confidence, 0.0) for e in estimates)
    if total_weight == 0.0:
        return sum(e.value for e in estimates) / len(estimates)
    return sum(e.value * max(e.confidence, 0.0) for e in estimates) / total_weight


def population_variance(estimates: list[Estimate]) -> float:
    """Population variance over estimate values. Returns 0.0 for <2 estimates."""
    if len(estimates) < 2:
        return 0.0
    return statistics.pvariance(e.value for e in estimates)


def pheromone_decay(
    pheromones: dict[str, float], decay_rate: float = 0.85
) -> dict[str, float]:
    """Multiply every pheromone by decay_rate. Pure function."""
    return {pid: p * decay_rate for pid, p in pheromones.items()}


def pheromone_dominance(pheromones: dict[str, float]) -> float:
    """Share of total pheromone held by the top path. 0.0 if map empty."""
    if not pheromones:
        return 0.0
    total = sum(pheromones.values())
    if total <= 0.0:
        return 0.0
    return max(pheromones.values()) / total


def top_k_by_pheromone(
    pheromones: dict[str, float], k: int = 3
) -> list[tuple[str, float]]:
    """Return the top-k (path_id, pheromone) tuples in descending order."""
    return sorted(pheromones.items(), key=lambda kv: (-kv[1], kv[0]))[:k]


# ---------------------------------------------------------------------------
# Utility — agent name resolution
# ---------------------------------------------------------------------------


def agent_name(agent: Any) -> str:
    """Resolve agent display name from dict or object."""
    if isinstance(agent, dict):
        return str(agent.get("name", "unknown"))
    return str(getattr(agent, "name", "unknown"))
