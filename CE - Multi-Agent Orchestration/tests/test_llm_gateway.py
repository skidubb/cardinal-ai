"""Tests for the gateway branch in protocols/llm.py — llm_complete() routing."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from protocols.llm import llm_complete


def _fake_litellm_response(content: str = "ok"):
    """Minimal LiteLLM-shaped response: .choices[0].message.content + .usage."""
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    usage = SimpleNamespace(input_tokens=10, output_tokens=5)
    return SimpleNamespace(choices=[choice], usage=usage)


@pytest.mark.asyncio
async def test_llm_complete_routes_gateway_model_to_litellm():
    fake_response = _fake_litellm_response("ok")
    with patch(
        "protocols.llm.litellm.acompletion", new=AsyncMock(return_value=fake_response)
    ) as mock_acompletion:
        result = await llm_complete(
            client=None,
            agent_name="test-agent",
            model="deepseek-v4-flash",
            max_tokens=100,
            messages=[{"role": "user", "content": "hi"}],
            system="sys",
        )

    mock_acompletion.assert_called_once()
    call_kwargs = mock_acompletion.call_args.kwargs
    assert call_kwargs["model"] == "vercel_ai_gateway/deepseek/deepseek-v4-flash"
    assert call_kwargs["messages"][0] == {"role": "system", "content": "sys"}
    assert result == "ok"


@pytest.mark.asyncio
async def test_llm_complete_anthropic_model_does_not_hit_gateway():
    fake_message = SimpleNamespace(content=[SimpleNamespace(text="anthropic reply")])
    fake_response = SimpleNamespace(
        content=[SimpleNamespace(text="anthropic reply")],
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        ),
    )
    del fake_message  # unused; kept for clarity of what a real Message looks like

    client = SimpleNamespace(
        messages=SimpleNamespace(create=AsyncMock(return_value=fake_response))
    )

    with patch(
        "protocols.llm.litellm.acompletion", new=AsyncMock()
    ) as mock_acompletion:
        result = await llm_complete(
            client=client,
            agent_name="test-agent",
            model="claude-opus-4-7",
            max_tokens=100,
            messages=[{"role": "user", "content": "hi"}],
            system="sys",
        )

    mock_acompletion.assert_not_called()
    client.messages.create.assert_called_once()
    assert result == "anthropic reply"
