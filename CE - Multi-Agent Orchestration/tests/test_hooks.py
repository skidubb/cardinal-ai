"""Tests for pre/post run hooks."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from protocols.learning.hooks import pre_run_hook, post_run_hook


@pytest.mark.asyncio
async def test_pre_run_hook_returns_categories():
    with patch("protocols.learning.hooks.classify_question", return_value=["innovation"]), \
         patch("protocols.learning.hooks.retrieve_insights") as mock_retrieve:
        mock_retrieve.return_value = MagicMock(
            recommended_protocol=None,
            confidence=0.0,
            institutional_memory=None,
            optimal_rounds=None,
        )
        config, cats = await pre_run_hook(
            client=AsyncMock(),
            protocol_key="p06_triz",
            question="How to innovate?",
            agents=[],
            user_config={},
        )
    assert cats == ["innovation"]


@pytest.mark.asyncio
async def test_pre_run_hook_injects_memory_into_agents():
    mock_agent = MagicMock()
    mock_agent.institutional_memory = None

    with patch("protocols.learning.hooks.classify_question", return_value=["strategy"]), \
         patch("protocols.learning.hooks.retrieve_insights") as mock_retrieve:
        mock_retrieve.return_value = MagicMock(
            recommended_protocol=None,
            confidence=0.8,
            institutional_memory="Past synthesis text",
            optimal_rounds=None,
            protocol_scores={},
            sample_size=10,
        )
        _, _ = await pre_run_hook(
            client=AsyncMock(),
            protocol_key="p04_multi_round_debate",
            question="Strategy question",
            agents=[mock_agent],
            user_config={},
        )
    assert mock_agent.institutional_memory == "Past synthesis text"


@pytest.mark.asyncio
async def test_post_run_hook_graceful_on_failure():
    with patch("protocols.learning.hooks.record_learning", side_effect=Exception("boom")):
        await post_run_hook(
            run_id=uuid.uuid4(),
            protocol_key="p06_triz",
            question="test",
            question_categories=["innovation"],
            eval_score=4.0,
            config={},
            synthesis_text="",
            cost_summary={},
        )
