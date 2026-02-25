"""Centralized LLM dispatch — routes agent calls through LiteLLM or Anthropic SDK.

agent_complete() checks if an agent has a "model" field. If so, it uses LiteLLM's
acompletion (supporting OpenAI, Gemini, Anthropic, etc.). If not, it falls back to
the Anthropic SDK client passed by the orchestrator, preserving tracing.

Orchestration-model calls (dedup, ranking, scoring) should NOT use this module —
those are orchestrator-owned mechanical steps with no agent identity.
"""

from __future__ import annotations

import anthropic
import litellm


def _is_anthropic_model(model: str) -> bool:
    """Check if a LiteLLM model string targets Anthropic."""
    return model.startswith("anthropic/") or "claude" in model.lower()


async def agent_complete(
    agent: dict,
    fallback_model: str,
    messages: list[dict],
    thinking_budget: int = 10_000,
    max_tokens: int = 14_096,
    anthropic_client: anthropic.AsyncAnthropic | None = None,
    system: str | None = None,
) -> str:
    """Dispatch an agent call to LiteLLM or Anthropic SDK.

    Args:
        agent: Agent dict with "name", "system_prompt", and optional "model".
        fallback_model: Model to use when agent has no "model" field (Anthropic SDK path).
        messages: Chat messages [{"role": "user", "content": "..."}].
        thinking_budget: Token budget for extended thinking (Anthropic models only).
        max_tokens: Max output tokens.
        anthropic_client: Required for fallback path (no agent model).
        system: System prompt override. If None, uses agent["system_prompt"].

    Returns:
        Response text as a string.
    """
    system_prompt = system or agent.get("system_prompt", "")
    agent_model = agent.get("model")

    if agent_model:
        # LiteLLM path — agent owns its model
        litellm_messages = []
        if system_prompt:
            litellm_messages.append({"role": "system", "content": system_prompt})
        litellm_messages.extend(messages)

        kwargs: dict = {
            "model": agent_model,
            "messages": litellm_messages,
            "max_tokens": max_tokens,
        }

        if _is_anthropic_model(agent_model):
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

        response = await litellm.acompletion(**kwargs)
        return response.choices[0].message.content

    # Anthropic SDK fallback — orchestrator's model, preserves tracing
    if anthropic_client is None:
        raise ValueError(
            "anthropic_client is required when agent has no 'model' field"
        )

    response = await anthropic_client.messages.create(
        model=fallback_model,
        max_tokens=thinking_budget + 4096 if max_tokens == 14_096 else max_tokens,
        thinking={"type": "enabled", "budget_tokens": thinking_budget},
        system=system_prompt,
        messages=messages,
    )
    return extract_text(response)


def extract_text(response) -> str:
    """Extract text from an Anthropic SDK or LiteLLM response.

    Auto-detects format:
    - Anthropic SDK: response.content is a list of blocks with .text
    - LiteLLM/OpenAI: response.choices[0].message.content is a string
    """
    # Anthropic SDK response
    if hasattr(response, "content") and isinstance(response.content, list):
        parts = []
        for block in response.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts)

    # LiteLLM / OpenAI response
    if hasattr(response, "choices"):
        return response.choices[0].message.content

    return str(response)
