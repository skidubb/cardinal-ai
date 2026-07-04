"""Tests for post-run learning recorder — unit tests with mock DB."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from protocols.learning.recorder import record_learning


@pytest.mark.asyncio
async def test_record_learning_graceful_on_db_failure():
    """When DB is unavailable, logs warning and returns None."""
    with patch("ce_db.session.get_session", side_effect=Exception("no db")):
        result = await record_learning(
            run_id=uuid.uuid4(),
            protocol_key="p06_triz",
            question="test",
            question_categories=["innovation"],
            eval_score=4.0,
            config={"rounds": 3},
            synthesis_text="Great synthesis",
            cost_summary={"total_usd": 1.0},
        )
    assert result is None


@pytest.mark.asyncio
async def test_record_learning_stores_without_score():
    """Runs with eval_score=None are stored but don't update best synthesis."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("ce_db.session.get_session", return_value=mock_session):
        await record_learning(
            run_id=uuid.uuid4(),
            protocol_key="p06_triz",
            question="test",
            question_categories=["innovation"],
            eval_score=None,
            config={},
            synthesis_text="Some output",
            cost_summary={"total_usd": 0.5},
        )
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called()
