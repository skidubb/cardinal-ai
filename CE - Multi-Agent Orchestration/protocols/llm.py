"""Centralized LLM dispatch — routes agent calls through LiteLLM or Anthropic SDK.

agent_complete() checks if an agent has a "model" field. If so, it uses LiteLLM's
acompletion (supporting OpenAI, Gemini, Anthropic, etc.). If not, it falls back to
the Anthropic SDK client passed by the orchestrator, preserving tracing.

Orchestration-model calls (dedup, ranking, scoring) should NOT use this module —
those are orchestrator-owned mechanical steps with no agent identity.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from contextvars import ContextVar
from typing import Any, Callable, Coroutine

import anthropic
import litellm

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

_RETRY_DELAYS = (1.0, 2.0, 4.0)  # seconds before each retry attempt


def _is_retryable(exc: BaseException) -> bool:
    """Return True for transient API errors that warrant a retry."""
    if isinstance(exc, (
        anthropic.RateLimitError,
        anthropic.APIConnectionError,
    )):
        return True
    if isinstance(exc, anthropic.APIStatusError) and exc.status_code >= 500:
        return True
    try:
        import litellm.exceptions as _lx
        if isinstance(exc, _lx.RateLimitError):
            return True
    except (ImportError, AttributeError):
        pass
    return False


async def _retry_api_call(
    coro_fn: Callable[..., Coroutine[Any, Any, Any]],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Call ``coro_fn(*args, **kwargs)`` with up to 3 retries on transient errors.

    Backoff schedule: 1 s, 2 s, 4 s — each with up to 0.5 s of random jitter.
    Logs a WARNING before each retry. Re-raises on non-retryable errors or after
    all retries are exhausted.
    """
    last_exc: BaseException | None = None
    for attempt, delay in enumerate((*_RETRY_DELAYS, None)):  # 4 total attempts
        try:
            return await coro_fn(*args, **kwargs)
        except BaseException as exc:
            if not _is_retryable(exc):
                raise
            last_exc = exc
            if delay is None:
                break  # retries exhausted — fall through to re-raise
            jitter = random.uniform(0.0, 0.5)
            wait = delay + jitter
            _log.warning(
                "API call failed (attempt %d/4, retrying in %.1fs): %s: %s",
                attempt + 1,
                wait,
                type(exc).__name__,
                exc,
            )
            await asyncio.sleep(wait)
    raise last_exc  # type: ignore[misc]


# Context-propagated event queue for live tool visibility
_event_queue: ContextVar[asyncio.Queue | None] = ContextVar("_event_queue", default=None)

# Context-propagated no_tools flag — protocol-level tool disable
_no_tools: ContextVar[bool] = ContextVar("_no_tools", default=False)

# Context-propagated cost tracker — optional, zero overhead when unset
_cost_tracker: ContextVar[Any] = ContextVar("_cost_tracker", default=None)


def set_no_tools(val: bool) -> None:
    _no_tools.set(val)


def get_no_tools() -> bool:
    return _no_tools.get()


def set_event_queue(q: asyncio.Queue) -> None:
    _event_queue.set(q)


def get_event_queue() -> asyncio.Queue | None:
    return _event_queue.get()


def set_cost_tracker(tracker: Any) -> None:
    """Attach a ProtocolCostTracker to the current context. Pass None to clear."""
    _cost_tracker.set(tracker)


def get_cost_tracker() -> Any:
    """Return the active ProtocolCostTracker, or None if unset."""
    return _cost_tracker.get()


def _record_usage(model: str, response: Any, agent_name: str | None = None) -> None:
    """Extract token counts from an API response and forward to the active tracker.

    Also records a Langfuse generation span if tracing is active.
    """
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    input_tokens = getattr(usage, "input_tokens", 0) or 0
    output_tokens = getattr(usage, "output_tokens", 0) or 0
    # cache_read_input_tokens is Anthropic SDK's attribute name for prompt-cache hits
    cached_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0

    tracker = _cost_tracker.get()
    if tracker is not None:
        tracker.track(model, input_tokens, output_tokens, cached_tokens)

    # Langfuse generation span (no-op if not configured)
    try:
        from protocols.langfuse_tracing import record_generation
        record_generation(model, input_tokens, output_tokens, cached_tokens, agent_name)
    except ImportError:
        pass


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
    # Production agent detection: if agent has chat(), use it directly
    if hasattr(agent, "chat") and callable(agent.chat):
        user_msg = messages[-1]["content"] if messages else ""
        return await agent.chat(user_msg)

    effective_no_tools = no_tools or _no_tools.get()
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

        if _is_anthropic_model(agent_model) and thinking_budget > 0:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

        if not effective_no_tools and tools:
            kwargs["tools"] = tools

        response = await _retry_api_call(litellm.acompletion, **kwargs)
        _record_usage(agent_model, response, agent_name=agent.get("name"))
        return response.choices[0].message.content

    # Anthropic SDK fallback — orchestrator's model, preserves tracing
    if anthropic_client is None:
        raise ValueError(
            "anthropic_client is required when agent has no 'model' field"
        )

    # Resolve tools: explicit param > agent-level schemas > agent tool key strings
    if not effective_no_tools:
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
        "system": system_prompt,
        "messages": messages,
    }
    if thinking_budget > 0:
        create_kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
    else:
        create_kwargs["thinking"] = {"type": "disabled"}
    if effective_tools:
        create_kwargs["tools"] = effective_tools

    response = await _retry_api_call(anthropic_client.messages.create, **create_kwargs)
    _record_usage(fallback_model, response, agent_name=agent.get("name"))

    # If no tools or no tool_use in response, return text directly
    if not effective_tools or response.stop_reason != "tool_use":
        return extract_text(response)

    # Agentic tool loop
    from api.tool_executor import execute_tool, MAX_TOOL_ITERATIONS

    agent_name = agent.get("name", "unknown")
    eq = get_event_queue()

    loop_messages = list(messages)
    for iteration in range(MAX_TOOL_ITERATIONS):
        loop_messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                # Push tool_call event
                if eq is not None:
                    input_summary = json.dumps(block.input)[:500] if block.input else "{}"
                    await eq.put({
                        "event": "tool_call",
                        "agent_name": agent_name,
                        "tool_name": block.name,
                        "tool_input": input_summary,
                        "iteration": iteration,
                    })

                result, elapsed_ms = await execute_tool(block.name, block.input)

                # Push tool_result event
                if eq is not None:
                    await eq.put({
                        "event": "tool_result",
                        "agent_name": agent_name,
                        "tool_name": block.name,
                        "result_preview": result[:500],
                        "elapsed_ms": round(elapsed_ms, 1),
                        "iteration": iteration,
                    })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        if not tool_results:
            break

        loop_messages.append({"role": "user", "content": tool_results})

        response = await _retry_api_call(
            anthropic_client.messages.create,
            **{**create_kwargs, "messages": loop_messages},
        )
        _record_usage(fallback_model, response, agent_name=agent.get("name"))

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


log = logging.getLogger(__name__)


def gather_with_exceptions(*coros_or_futures):
    """Like asyncio.gather but with return_exceptions=True and exception filtering.

    Returns only successful results; logs warnings for failures.
    Use when partial results are acceptable (most parallel agent queries).
    """
    return asyncio.gather(*coros_or_futures, return_exceptions=True)


def filter_exceptions(results: list, label: str = "gather") -> list:
    """Filter exceptions from gather_with_exceptions results, logging warnings."""
    good = []
    for r in results:
        if isinstance(r, BaseException):
            log.warning("%s: agent failed: %s", label, r)
        else:
            good.append(r)
    return good


def parse_json_array(text: str) -> list[dict]:
    """Extract a JSON array from LLM output that may contain markdown fences.

    Handles truncated JSON by attempting repair (closing brackets/braces).
    """
    import re

    text = text.strip()
    # Try to find JSON array between markdown fences
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    # Fallback: find the first [ ... ] in the text
    if not text.startswith("["):
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start : end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Attempt truncation repair: close open strings/objects/arrays
        repaired = text.rstrip()
        if repaired.endswith(","):
            repaired = repaired[:-1]
        open_braces = repaired.count("{") - repaired.count("}")
        open_brackets = repaired.count("[") - repaired.count("]")
        repaired += "}" * max(0, open_braces)
        repaired += "]" * max(0, open_brackets)
        if repaired.count('"') % 2 == 1:
            repaired += '"'
            open_braces = repaired.count("{") - repaired.count("}")
            open_brackets = repaired.count("[") - repaired.count("]")
            repaired += "}" * max(0, open_braces)
            repaired += "]" * max(0, open_brackets)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            raise ValueError(f"Cannot parse JSON array (len={len(text)}): {text[:200]}...")


def parse_json_object(text: str) -> dict:
    """Extract the first JSON object from text."""
    import re

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}
