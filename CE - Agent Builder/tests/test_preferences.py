"""Tests for preference tracker — uses DuckDB fixture."""

import pytest

import csuite.learning.preferences as _pref_mod
from csuite.learning.preferences import PreferenceTracker


@pytest.fixture(autouse=True)
def _isolate_pref_store(duckdb_store):
    """Force all preference tests to use the fresh duckdb_store."""
    _pref_mod._store = duckdb_store
    yield
    _pref_mod._store = None


class TestPreferenceTracker:
    def test_record_correction(self):
        pt = PreferenceTracker()
        pt.record_feedback("cfo", "correction", detail="Don't recommend Canva")
        ctx = pt.get_preference_context("cfo")
        assert "Don't recommend Canva" in ctx

    def test_record_preference(self):
        pt = PreferenceTracker()
        pt.record_feedback("cmo", "preference", detail="Use MEDDPICC framework")
        ctx = pt.get_preference_context("cmo")
        assert "MEDDPICC" in ctx

    def test_record_generic_feedback(self):
        pt = PreferenceTracker()
        pt.record_feedback("ceo", "style", detail="Be more concise")
        ctx = pt.get_preference_context("ceo")
        assert isinstance(ctx, str)

    def test_empty_context(self):
        pt = PreferenceTracker()
        ctx = pt.get_preference_context("cpo")
        assert ctx == ""

    def test_corrections_capped_at_30(self):
        pt = PreferenceTracker()
        for i in range(35):
            pt.record_feedback("cfo", "correction", detail=f"Correction {i}")
        data = pt._load("cfo")
        assert len(data["corrections"]) <= 30

    def test_preferences_separated_by_role(self):
        pt = PreferenceTracker()
        pt.record_feedback("cfo", "correction", detail="CFO note")
        pt.record_feedback("cto", "correction", detail="CTO note")
        cfo_ctx = pt.get_preference_context("cfo")
        cto_ctx = pt.get_preference_context("cto")
        assert "CFO note" in cfo_ctx
        assert "CTO note" not in cfo_ctx
        assert "CTO note" in cto_ctx
