"""Tests for QA validation tool."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from csuite.tools.registry import _handle_qa_validate


@pytest.fixture
def mock_settings():
    return MagicMock()


@pytest.mark.asyncio
async def test_qa_validate_content_too_short(mock_settings):
    result = json.loads(
        await _handle_qa_validate({"content": "Short"}, mock_settings)
    )
    assert "error" in result
    assert "too short" in result["error"]


@pytest.mark.asyncio
async def test_qa_validate_single_tier():
    settings = MagicMock()
    content = "A" * 100  # Long enough

    mock_eval = MagicMock()
    mock_eval.to_dict.return_value = {
        "tier": "tier_1",
        "result": "approved",
        "issues": [],
        "feedback": "Approved - Tier 1",
    }
    mock_eval.result.value = "approved"

    with patch("csuite.tools.qa_protocol.QAPipeline") as mock_pipeline_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run_tier1_only = AsyncMock(return_value=mock_eval)
        mock_pipeline_cls.return_value = mock_pipeline

        result = json.loads(
            await _handle_qa_validate({"content": content, "tier": "1"}, settings)
        )

    assert "tier_1" in result
    assert result["overall_pass"] is True


@pytest.mark.asyncio
async def test_qa_validate_all_tiers():
    settings = MagicMock()
    content = "A" * 100

    mock_result = MagicMock()
    mock_result.to_dict.return_value = {
        "final_result": "approved",
        "total_cost": 0.01,
        "evaluations": [
            {"tier": "tier_1", "result": "approved"},
            {"tier": "tier_2", "result": "approved"},
        ],
    }

    with patch("csuite.tools.qa_protocol.QAPipeline") as mock_pipeline_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run = AsyncMock(return_value=mock_result)
        mock_pipeline_cls.return_value = mock_pipeline

        result = json.loads(
            await _handle_qa_validate({"content": content, "tier": "all"}, settings)
        )

    assert result["final_result"] == "approved"


@pytest.mark.asyncio
async def test_qa_validate_tier2_only():
    settings = MagicMock()
    content = "A" * 100

    mock_result = MagicMock()
    mock_result.to_dict.return_value = {
        "final_result": "revisions_needed",
        "total_cost": 0.005,
        "evaluations": [
            {"tier": "tier_1", "result": "approved"},
            {"tier": "tier_2", "result": "revisions_needed"},
        ],
    }

    with patch("csuite.tools.qa_protocol.QAPipeline") as mock_pipeline_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run_through_tier2 = AsyncMock(return_value=mock_result)
        mock_pipeline_cls.return_value = mock_pipeline

        result = json.loads(
            await _handle_qa_validate({"content": content, "tier": "2"}, settings)
        )

    assert result["final_result"] == "revisions_needed"


@pytest.mark.asyncio
async def test_qa_validate_with_context():
    settings = MagicMock()
    content = "A" * 100

    mock_result = MagicMock()
    mock_result.to_dict.return_value = {"final_result": "approved", "total_cost": 0.02, "evaluations": []}

    with patch("csuite.tools.qa_protocol.QAPipeline") as mock_pipeline_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run = AsyncMock(return_value=mock_result)
        mock_pipeline_cls.return_value = mock_pipeline

        result = json.loads(
            await _handle_qa_validate(
                {"content": content, "context": "CEO ODSC submission package"},
                settings,
            )
        )

    assert result["final_result"] == "approved"
    # Verify context was passed to AgentOutput
    call_args = mock_pipeline.run.call_args
    assert call_args[0][0].engagement_context == "CEO ODSC submission package"
