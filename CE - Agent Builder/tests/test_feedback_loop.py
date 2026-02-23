"""Tests for the closed-loop learning module."""

from csuite.learning.feedback_loop import (
    ApprovalGate,
    ArtifactScore,
    FeedbackStore,
    SelfEvaluator,
)


def test_artifact_score_model():
    score = ArtifactScore(
        event_type="strategy_meeting",
        agent_role="cfo",
        dimensions={"clarity": 4.0, "actionability": 3.5, "grounding": 4.5, "coherence": 4.0},
        overall=4.1,
    )
    assert score.event_type == "strategy_meeting"
    assert score.dimensions["clarity"] == 4.0
    assert score.overall == 4.1
    assert score.approved is None
    assert len(score.artifact_id) == 12


def test_artifact_score_defaults():
    score = ArtifactScore()
    assert score.event_type == ""
    assert score.agent_role == ""
    assert score.dimensions == {}
    assert score.overall == 0.0


def test_feedback_store_disabled():
    """FeedbackStore gracefully degrades when Pinecone not configured."""
    store = FeedbackStore()
    # In test env, Pinecone is likely not configured
    if not store.enabled:
        assert store.store_score(ArtifactScore(), "test") is False
        assert store.retrieve_exemplars("test") == []
        assert store.record_approval("x", True) is False


def test_approval_gate():
    """ApprovalGate wraps FeedbackStore approval methods."""
    gate = ApprovalGate()
    # In test env without Pinecone, these should return False gracefully
    if not gate.store.enabled:
        assert gate.approve("test-id") is False
        assert gate.reject("test-id") is False
