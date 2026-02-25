"""Scoped Agent Context — filter shared context by agent role scope.

Agents with a `context_scope` field only see context blocks tagged with
matching scopes. Missing field = sees everything (backward compatible).
"""

from __future__ import annotations

SCOPE_TAGS = {"financial", "operational", "market", "technical", "hr", "strategic", "all"}

# Name-based scope inference fallback (used when agent dict lacks context_scope)
_NAME_SCOPE_MAP = {
    "financial": "financial", "cfo": "financial", "revenue": "financial", "cro": "financial",
    "technology": "technical", "cto": "technical",
    "marketing": "market", "cmo": "market",
    "operations": "operational", "coo": "operational",
}


def get_primary_scope(agent: dict) -> str:
    """Return the primary scope for an agent.

    Uses agent's context_scope field if present, otherwise falls back
    to name-based inference.
    """
    scopes = agent.get("context_scope")
    if scopes:
        return scopes[0]

    name_lower = agent.get("name", "").lower()
    for keyword, scope in _NAME_SCOPE_MAP.items():
        if keyword in name_lower:
            return scope
    return "all"


def build_context_blocks(rounds: list) -> list[dict]:
    """Build scoped context blocks from debate/negotiation rounds.

    Each argument's scope is read from its `scope` attribute (set at creation
    time from the agent's context_scope). Falls back to "all".
    """
    blocks = []
    for rnd in rounds:
        for arg in rnd.arguments:
            scope = getattr(arg, "scope", "all")
            blocks.append(tag_context(
                f"--- Round {rnd.round_number} ({rnd.round_type}) ---\n[{arg.name}]:\n{arg.content}",
                scope,
            ))
    return blocks


def tag_context(content: str, scope: str) -> dict:
    """Wrap content string with a scope tag."""
    return {"scope": scope, "content": content}


def filter_context_for_agent(agent: dict, context_blocks: list[dict]) -> str:
    """Filter context blocks by agent's scope.

    Args:
        agent: Agent dict, optionally with "context_scope": list[str].
        context_blocks: List of {"scope": str, "content": str} dicts.

    Returns:
        Concatenated content the agent is allowed to see.
    """
    scopes = agent.get("context_scope")

    # No scope defined = sees everything (backward compat)
    if not scopes:
        return "\n\n".join(block["content"] for block in context_blocks)

    allowed = set(scopes)

    # "all" scope = sees everything
    if "all" in allowed:
        return "\n\n".join(block["content"] for block in context_blocks)

    # Filter to matching scopes + "strategic" always included if agent has any scope
    filtered = []
    for block in context_blocks:
        block_scope = block.get("scope", "all")
        if block_scope == "all" or block_scope in allowed:
            filtered.append(block["content"])

    return "\n\n".join(filtered)
