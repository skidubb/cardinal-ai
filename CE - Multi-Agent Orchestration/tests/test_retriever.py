"""Tests for insight retriever — unit tests with mock DB."""

import pytest
from unittest.mock import patch

from protocols.learning.retriever import RunInsights, retrieve_insights


class TestRunInsights:
    def test_empty_insights_has_no_recommendations(self):
        insights = RunInsights(
            protocol_scores={},
            recommended_protocol=None,
            optimal_rounds=None,
            optimal_agents=None,
            thinking_budget=None,
            institutional_memory=None,
            confidence=0.0,
            sample_size=0,
        )
        assert not insights.has_recommendations

    def test_confident_insights_has_recommendations(self):
        insights = RunInsights(
            protocol_scores={"p06_triz": 4.2},
            recommended_protocol="p06_triz",
            optimal_rounds=3,
            optimal_agents=["ceo", "cfo"],
            thinking_budget=10000,
            institutional_memory="Past synthesis...",
            confidence=0.5,
            sample_size=5,
        )
        assert insights.has_recommendations

    def test_serializes_to_dict(self):
        insights = RunInsights(
            protocol_scores={}, recommended_protocol=None,
            optimal_rounds=None, optimal_agents=None, thinking_budget=None,
            institutional_memory=None, confidence=0.0, sample_size=0,
        )
        d = insights.model_dump()
        assert "protocol_scores" in d
        assert "confidence" in d


@pytest.mark.asyncio
async def test_retrieve_insights_graceful_on_db_failure():
    """When DB is unavailable, returns empty insights (not an exception)."""
    with patch("ce_db.session.get_session", side_effect=Exception("no db")):
        result = await retrieve_insights("p06_triz", "test question", ["innovation"])
    assert result.confidence == 0.0
    assert result.sample_size == 0
    assert result.institutional_memory is None
