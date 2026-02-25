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
    tools: list[dict] | None = None,
    no_tools: bool = False,
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
        tools: Anthropic tool schemas to pass to the model.
        no_tools: If True, strip all tools for clean mechanical execution.

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

        if not no_tools and tools:
            kwargs["tools"] = tools

        response = await litellm.acompletion(**kwargs)
        return response.choices[0].message.content

    # Anthropic SDK fallback — orchestrator's model, preserves tracing
    if anthropic_client is None:
        raise ValueError(
            "anthropic_client is required when agent has no 'model' field"
        )

    # Resolve tools: explicit param > agent-level schemas > agent tool key strings
    if not no_tools:
        effective_tools = tools
        if not effective_tools:
            effective_tools = agent.get("tools_schemas")
        if not effective_tools and agent.get("tools"):
            try:
                from csuite.tools.schemas import ALL_TOOL_SCHEMAS
                effective_tools = [
                    ALL_TOOL_SCHEMAS[t] for t in agent["tools"] if t in ALL_TOOL_SCHEMAS
                ]
            except ImportError:
                effective_tools = None
    else:
        effective_tools = None

    create_kwargs = {
        "model": fallback_model,
        "max_tokens": thinking_budget + 4096 if max_tokens == 14_096 else max_tokens,
        "thinking": {"type": "enabled", "budget_tokens": thinking_budget},
        "system": system_prompt,
        "messages": messages,
    }
    if effective_tools:
        create_kwargs["tools"] = effective_tools

    response = await anthropic_client.messages.create(**create_kwargs)

    # If no tools or no tool_use in response, return text directly
    if not effective_tools or response.stop_reason != "tool_use":
        return extract_text(response)

    # Agentic tool loop
    from api.tool_executor import execute_tool, MAX_TOOL_ITERATIONS

    loop_messages = list(messages)
    for iteration in range(MAX_TOOL_ITERATIONS):
        loop_messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = await execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        if not tool_results:
            break

        loop_messages.append({"role": "user", "content": tool_results})

        response = await anthropic_client.messages.create(**{
            **create_kwargs,
            "messages": loop_messages,
        })

        if response.stop_reason != "tool_use":
            break

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
