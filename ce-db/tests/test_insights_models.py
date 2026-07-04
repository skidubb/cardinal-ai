"""Tests for ProtocolInsight and RunLearning models."""

from sqlalchemy import inspect

from ce_db.models import Base, ProtocolInsight, RunLearning


def test_protocol_insight_columns():
    mapper = inspect(ProtocolInsight)
    col_names = {c.key for c in mapper.columns}
    assert "protocol_key" in col_names
    assert "question_category" in col_names
    assert "insight_type" in col_names
    assert "insight_json" in col_names
    assert "confidence" in col_names
    assert "sample_size" in col_names
    assert "best_synthesis" in col_names
    assert "best_score" in col_names
    assert "computed_at" in col_names


def test_run_learning_columns():
    mapper = inspect(RunLearning)
    col_names = {c.key for c in mapper.columns}
    assert "run_id" in col_names
    assert "protocol_key" in col_names
    assert "question_categories" in col_names
    assert "eval_score" in col_names
    assert "config_json" in col_names
    assert "cost_usd" in col_names
    assert "synthesis_excerpt" in col_names


def test_protocol_insight_has_unique_constraint():
    constraints = ProtocolInsight.__table__.constraints
    unique_names = {c.name for c in constraints if hasattr(c, "name")}
    assert "uq_insights_lookup" in unique_names


def test_run_learning_has_gin_index():
    index_names = {idx.name for idx in RunLearning.__table__.indexes}
    assert "ix_run_learnings_categories" in index_names
