"""Tests for the unified knowledge search facade."""

from __future__ import annotations

import pytest

from protocols import knowledge
from protocols.knowledge import Hit, SearchScope


@pytest.fixture(autouse=True)
def clean_backends():
    """Snapshot and restore the module-level backend registry each test."""
    original = dict(knowledge._backends)
    yield
    knowledge._backends.clear()
    knowledge._backends.update(original)


@pytest.mark.asyncio
async def test_no_backends_returns_empty() -> None:
    knowledge._backends.clear()
    hits = await knowledge.search("anything", SearchScope(top_k=5))
    assert hits == []


@pytest.mark.asyncio
async def test_empty_query_returns_empty() -> None:
    async def _backend(q, scope):
        return [Hit(text="should not be reached", score=1.0, source="test")]

    knowledge._backends.clear()
    knowledge.register_backend("test", _backend)
    assert await knowledge.search("   ", SearchScope()) == []


@pytest.mark.asyncio
async def test_hits_merged_and_ranked_by_score() -> None:
    async def backend_a(q, scope):
        return [Hit(text="A1", score=0.9, source="A"), Hit(text="A2", score=0.3, source="A")]

    async def backend_b(q, scope):
        return [Hit(text="B1", score=0.75, source="B")]

    knowledge._backends.clear()
    knowledge.register_backend("a", backend_a)
    knowledge.register_backend("b", backend_b)

    hits = await knowledge.search("q", SearchScope(top_k=10))
    assert [h.text for h in hits] == ["A1", "B1", "A2"]


@pytest.mark.asyncio
async def test_top_k_caps_result_count() -> None:
    async def backend_a(q, scope):
        return [Hit(text=f"a{i}", score=1.0 - i * 0.1, source="A") for i in range(5)]

    knowledge._backends.clear()
    knowledge.register_backend("a", backend_a)

    hits = await knowledge.search("q", SearchScope(top_k=3))
    assert len(hits) == 3


@pytest.mark.asyncio
async def test_min_score_filter() -> None:
    async def backend_a(q, scope):
        return [Hit(text="hi", score=0.9, source="A"), Hit(text="lo", score=0.2, source="A")]

    knowledge._backends.clear()
    knowledge.register_backend("a", backend_a)

    hits = await knowledge.search("q", SearchScope(min_score=0.5, top_k=10))
    assert [h.text for h in hits] == ["hi"]


@pytest.mark.asyncio
async def test_backend_failure_is_isolated() -> None:
    async def good(q, scope):
        return [Hit(text="ok", score=0.8, source="good")]

    async def crashes(q, scope):
        raise RuntimeError("boom")

    knowledge._backends.clear()
    knowledge.register_backend("good", good)
    knowledge.register_backend("bad", crashes)

    hits = await knowledge.search("q", SearchScope())
    assert [h.text for h in hits] == ["ok"]


@pytest.mark.asyncio
async def test_backend_returning_non_list_is_dropped() -> None:
    async def wrong(q, scope):
        return "not a list"  # type: ignore[return-value]

    knowledge._backends.clear()
    knowledge.register_backend("wrong", wrong)
    hits = await knowledge.search("q", SearchScope())
    assert hits == []


def test_format_hits_empty() -> None:
    assert "no relevant" in knowledge.format_hits_for_prompt([]).lower()


def test_format_hits_orders_and_truncates() -> None:
    hits = [
        Hit(text="First relevant fact.", score=0.9, source="A"),
        Hit(text="Second fact.", score=0.7, source="B"),
    ]
    formatted = knowledge.format_hits_for_prompt(hits)
    assert "First relevant fact" in formatted
    assert "Second fact" in formatted
    assert formatted.index("First relevant") < formatted.index("Second fact")


def test_registered_backends_exposes_names() -> None:
    knowledge._backends.clear()
    knowledge.register_backend("mock", lambda q, scope: [])  # type: ignore[arg-type]
    assert "mock" in knowledge.registered_backends()
