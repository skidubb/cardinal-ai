"""Tests for the real knowledge backends.

Live queries need live Pinecone/Postgres/DuckDB, so the tests here focus on:
- Registration behavior (which backends register when libraries are/aren't present)
- Adapter shape (result-parsing across the different Pinecone SDK response shapes)
- Scope respect (backends that only fire when the scope opts them in)
- Failure isolation (a broken backend doesn't break the facade)
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from protocols import knowledge, knowledge_backends
from protocols.knowledge import Hit, SearchScope


@pytest.fixture(autouse=True)
def clean_backends():
    original = dict(knowledge._backends)
    yield
    knowledge._backends.clear()
    knowledge._backends.update(original)


# ---------------------------------------------------------------------------
# Runs backend
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_runs_backend_no_op_without_include_runs() -> None:
    hits = await knowledge_backends._runs_backend("q", SearchScope(include_runs=False))
    assert hits == []


@pytest.mark.asyncio
async def test_runs_backend_no_op_without_ce_db(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    # If ce_db is somehow installed in this env, temporarily hide it.
    monkeypatch.setitem(sys.modules, "ce_db", None)
    hits = await knowledge_backends._runs_backend("q", SearchScope(include_runs=True))
    assert hits == []


# ---------------------------------------------------------------------------
# Experience backend
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_experience_backend_no_op_without_scope() -> None:
    hits = await knowledge_backends._experience_backend("q", SearchScope(include_experience=False))
    assert hits == []


# ---------------------------------------------------------------------------
# Pinecone match extractor — the most brittle part
# ---------------------------------------------------------------------------

def test_extract_matches_new_shape_result_dict() -> None:
    payload = {
        "result": {
            "hits": [
                {"_id": "a", "_score": 0.9, "fields": {"text": "hello"}, "text": "hello"},
                {"_id": "b", "_score": 0.5, "text": "world"},
            ]
        }
    }
    matches = knowledge_backends._extract_matches(payload)
    assert len(matches) == 2
    assert matches[0]["_id"] == "a"


def test_extract_matches_legacy_matches_key() -> None:
    payload = {"matches": [{"id": "x", "score": 0.7, "metadata": {"text": "old shape"}}]}
    matches = knowledge_backends._extract_matches(payload)
    assert len(matches) == 1
    assert matches[0]["id"] == "x"


def test_extract_matches_object_with_hits_attr() -> None:
    obj = SimpleNamespace(hits=[{"_id": "y", "score": 0.4, "text": "attr shape"}])
    matches = knowledge_backends._extract_matches(obj)
    assert len(matches) == 1


def test_extract_matches_bad_input_returns_empty() -> None:
    assert knowledge_backends._extract_matches(None) == []
    assert knowledge_backends._extract_matches(42) == []
    assert knowledge_backends._extract_matches({"result": "not a dict"}) == []


# ---------------------------------------------------------------------------
# Recency scoring — used by runs backend
# ---------------------------------------------------------------------------

def test_recency_score_recent_close_to_one() -> None:
    import datetime as _dt

    now = _dt.datetime.now(_dt.timezone.utc)
    score = knowledge_backends._recency_score(now)
    assert 0.9 < score <= 1.0


def test_recency_score_old_approaches_half() -> None:
    import datetime as _dt

    old = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=365)
    score = knowledge_backends._recency_score(old)
    assert 0.5 <= score < 0.55


def test_recency_score_none_returns_neutral() -> None:
    assert knowledge_backends._recency_score(None) == 0.5


def test_recency_score_bad_type_returns_neutral() -> None:
    assert knowledge_backends._recency_score("not a datetime") == 0.5


# ---------------------------------------------------------------------------
# Experience row normalization
# ---------------------------------------------------------------------------

def test_normalize_experience_list_of_dicts() -> None:
    rows = knowledge_backends._normalize_experience_rows([
        {"lesson": "a"}, {"text": "b"}, "not a dict",
    ])
    assert len(rows) == 2


def test_normalize_experience_none_returns_empty() -> None:
    assert knowledge_backends._normalize_experience_rows(None) == []


def test_normalize_experience_dataframe_like_object() -> None:
    class FakeDF:
        def to_dict(self, orient=None):
            return [{"lesson": "a"}, {"lesson": "b"}]

    rows = knowledge_backends._normalize_experience_rows(FakeDF())
    assert len(rows) == 2


# ---------------------------------------------------------------------------
# register_all — safe to call, idempotent
# ---------------------------------------------------------------------------

def test_register_all_returns_tuple() -> None:
    registered = knowledge_backends.register_all()
    assert isinstance(registered, tuple)
    # Every name that registered corresponds to a callable in the facade.
    for name in registered:
        assert callable(knowledge._backends[name])


def test_register_all_is_idempotent() -> None:
    first = set(knowledge_backends.register_all())
    second = set(knowledge_backends.register_all())
    assert first == second


# ---------------------------------------------------------------------------
# End-to-end: facade with a fake pinecone-shaped backend, no live libs needed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_facade_returns_hits_from_fake_pinecone(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_pinecone(q: str, scope: SearchScope) -> list[Hit]:
        return [
            Hit(text="A", score=0.9, source="pinecone:ce-gtm-knowledge"),
            Hit(text="B", score=0.5, source="pinecone:multi-agent-kb"),
        ]

    knowledge._backends.clear()
    knowledge.register_backend("pinecone", fake_pinecone)

    hits = await knowledge.search("what's our GTM story?", SearchScope(top_k=5))
    assert [h.text for h in hits] == ["A", "B"]
    formatted = knowledge.format_hits_for_prompt(hits)
    assert "A" in formatted and "B" in formatted
