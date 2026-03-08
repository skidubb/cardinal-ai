"""SynthesisEngine — extracts synthesis from protocols into a dedicated agent.

Dual-mode: use_agent=True routes through the Synthesizer meta-agent via
agent_complete(), False falls back to direct client.messages.create() for
backward compatibility during incremental migration.
"""

from __future__ import annotations

from protocols.config import THINKING_MODEL
from protocols.llm import agent_complete, extract_text


# Loaded lazily to avoid circular imports
_SYNTHESIZER_AGENT: dict | None = None


def _get_synthesizer_agent() -> dict:
    global _SYNTHESIZER_AGENT
    if _SYNTHESIZER_AGENT is None:
        from protocols.agents import META_AGENTS
        _SYNTHESIZER_AGENT = META_AGENTS["synthesizer"]
    return _SYNTHESIZER_AGENT


class SynthesisEngine:
    """Routes synthesis through a dedicated Synthesizer agent or direct LLM call.

    Args:
        client: Anthropic AsyncAnthropic client (used for direct-call fallback).
        thinking_model: Model string for synthesis (Opus-tier).
        thinking_budget: Token budget for extended thinking.
        use_agent: If True, route through Synthesizer meta-agent. If False,
                   use direct client.messages.create() (legacy behavior).
    """

    def __init__(
        self,
        client,
        thinking_model: str = THINKING_MODEL,
        thinking_budget: int = 10_000,
        use_agent: bool = True,
    ):
        self.client = client
        self.thinking_model = thinking_model
        self.thinking_budget = thinking_budget
        self.use_agent = use_agent

    async def synthesize(
        self,
        protocol_prompt: str,
        question: str,
        system_prompt: str | None = None,
    ) -> str:
        """Run synthesis via agent or direct LLM call.

        Args:
            protocol_prompt: The fully-formatted protocol-specific synthesis
                prompt (from each protocol's prompts.py). Passed as the user
                message — the Synthesizer agent's identity is its own system
                prompt.
            question: Original question (for tracing/context).
            system_prompt: Optional system prompt override for direct-call mode.
                Ignored when use_agent=True (agent uses its own system prompt).

        Returns:
            Synthesis text.
        """
        if self.use_agent:
            return await self._via_agent(protocol_prompt)
        return await self._direct(protocol_prompt, system_prompt)

    async def _via_agent(self, prompt: str) -> str:
        """Route through the Synthesizer meta-agent."""
        agent = _get_synthesizer_agent()
        return await agent_complete(
            agent=agent,
            fallback_model=self.thinking_model,
            messages=[{"role": "user", "content": prompt}],
            thinking_budget=self.thinking_budget,
            anthropic_client=self.client,
            no_tools=True,
        )

    async def _direct(self, prompt: str, system_prompt: str | None) -> str:
        """Legacy direct call — identical to current protocol behavior."""
        sys = system_prompt or "You are a strategic synthesizer producing actionable conclusions."
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
            system=sys,
            messages=[{"role": "user", "content": prompt}],
        )
        return extract_text(response)
