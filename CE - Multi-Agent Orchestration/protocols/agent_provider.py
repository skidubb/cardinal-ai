"""Dual-mode agent provider — research (lightweight dicts) or production (ServerAgent).

Research mode: Agents are plain dicts with name + system_prompt. Requires explicit opt-in via
    set_agent_mode("research") or AGENT_MODE=research env var.
Production mode: Default. Agents are ServerAgent instances with direct Anthropic API calls,
    native tool-use, Pinecone memory, and DuckDB learning. No subprocess spawning.

Usage:
    from protocols.agent_provider import set_agent_mode, get_agent_mode

    # Production is the default — no configuration needed
    agents = build_production_agents(["ceo", "cfo"])

    # Research mode requires explicit opt-in
    set_agent_mode("research")  # or set AGENT_MODE=research env var
"""

from __future__ import annotations

import json
import logging
from typing import Any

from protocols.server_agent import ServerAgent

logger = logging.getLogger(__name__)

_agent_mode: str = "production"


def set_agent_mode(mode: str) -> None:
    """Set the global agent mode ('research' or 'production')."""
    global _agent_mode
    if mode not in ("research", "production"):
        raise ValueError(
            f"Invalid agent mode: {mode}. Must be 'research' or 'production'."
        )
    _agent_mode = mode


def get_agent_mode() -> str:
    """Get the current agent mode."""
    return _agent_mode


def _load_db_overrides(keys: list[str]) -> dict[str, dict]:
    """Load per-agent overrides from the Agent table.

    Returns a dict keyed by agent key containing only fields that are set:
    model, temperature, system_prompt, tools, kb_namespaces, max_tokens, name,
    and the prompt-extra fields (frameworks, deliverable_template,
    communication_style, personality, constraints) used by ``_compose_prompt``.
    Missing keys or DB unavailability resolve to an empty dict so callers fall
    back to defaults.
    """
    try:
        from sqlmodel import Session, select
        from api.database import engine
        from api.models import Agent as AgentModel
    except Exception:
        return {}

    overrides: dict[str, dict] = {}
    try:
        with Session(engine) as session:
            stmt = select(AgentModel).where(AgentModel.key.in_(keys))  # type: ignore[attr-defined]
            rows = list(session.execute(stmt).scalars())
            for row in rows:
                entry: dict[str, Any] = {}
                if row.model:
                    entry["model"] = row.model
                entry["temperature"] = row.temperature
                if row.system_prompt:
                    entry["system_prompt"] = row.system_prompt
                if row.name:
                    entry["name"] = row.name
                if row.max_tokens:
                    entry["max_tokens"] = row.max_tokens

                for field_name, json_field, default in (
                    ("tools", "tools_json", "[]"),
                    ("kb_namespaces", "kb_namespaces_json", "[]"),
                    ("frameworks", "frameworks_json", "[]"),
                    ("constraints", "constraints_json", "[]"),
                ):
                    raw = getattr(row, json_field, None)
                    if raw and raw != default:
                        try:
                            entry[field_name] = json.loads(raw)
                        except (TypeError, ValueError):
                            logger.debug(
                                "Skipping unparseable %s for agent %s",
                                json_field,
                                row.key,
                            )

                if row.deliverable_template:
                    entry["deliverable_template"] = row.deliverable_template
                if row.communication_style:
                    entry["communication_style"] = row.communication_style
                if row.personality:
                    entry["personality"] = row.personality

                overrides[row.key] = entry
    except Exception as exc:
        logger.debug("DB agent override lookup failed: %s", exc, exc_info=True)
    return overrides


def _compose_prompt(entry: dict[str, Any]) -> str | None:
    """Assemble a full system prompt from a DB override entry.

    Mirrors the prompt assembly previously done in the deprecated
    ``api/runner.py:_resolve_agents`` — base system_prompt plus optional
    frameworks / deliverable template / communication style / personality /
    constraints sections. Returns None when the entry has no system_prompt
    (the caller then falls back to the builtin role prompt).
    """
    base = entry.get("system_prompt")
    if not base:
        return None

    assembled = base

    frameworks = entry.get("frameworks")
    if frameworks:
        assembled += "\n\n## Analytical Frameworks\n"
        for fw in frameworks:
            assembled += (
                f"\n### {fw.get('name', '')}\n{fw.get('description', '')}\n"
                f"**When to use:** {fw.get('when_to_use', '')}\n"
            )

    deliverable_template = entry.get("deliverable_template")
    if deliverable_template:
        assembled += f"\n\n## Deliverable Template\n{deliverable_template}"

    communication_style = entry.get("communication_style")
    if communication_style:
        assembled += f"\n\n## Communication Style\n{communication_style}"

    personality = entry.get("personality")
    if personality:
        assembled += f"\n\n## Personality\n{personality}"

    constraints = entry.get("constraints")
    if constraints:
        assembled += "\n\n## Constraints\n" + "\n".join(f"- {c}" for c in constraints)

    return assembled


def build_production_agents(
    keys: list[str], model: str = "claude-opus-4-7"
) -> list[ServerAgent]:
    """Build production agents using ServerAgent (direct Anthropic API + tools).

    Each agent gets:
    - Rich system prompt from Agent Builder (70+ roles), or a DB override
    - Per-role tool schemas with full agentic tool loop, or a DB override
    - Pinecone memory, DuckDB experience logs (graceful degradation)
    - Real token-level cost tracking from API responses
    - DB-level overrides for model, temperature, prompt, tools, kb_namespaces,
      max_tokens, and display name (when present)

    No subprocess spawning — works in Docker, Railway, any server environment.
    """
    keys_lower = [k.lower() for k in keys]
    overrides = _load_db_overrides(keys_lower)

    agents: list[ServerAgent] = []

    for key_lower in keys_lower:
        ov = overrides.get(key_lower, {})
        agent_model = ov.get("model") or model
        agent_temp = ov.get("temperature")
        agent = ServerAgent(
            role=key_lower,
            model=agent_model,
            temperature=agent_temp,
            system_prompt=_compose_prompt(ov),
            tool_names=ov.get("tools"),
            kb_namespaces=ov.get("kb_namespaces"),
            max_tokens=ov.get("max_tokens"),
            display_name=ov.get("name"),
        )
        agents.append(agent)
        logger.info(
            "Production agent created: %s (%s) model=%s temperature=%s",
            key_lower,
            agent.name,
            agent_model,
            agent_temp,
        )

    return agents
