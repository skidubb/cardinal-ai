"""Tests for the hierarchical delegation primitive."""

from __future__ import annotations

import asyncio
import json

import pytest

from protocols import hierarchical
from protocols.hierarchical import (
    Decomposition,
    SubResult,
    SubTask,
    delegate,
    format_results_for_synthesis,
    merge_by_category,
    parse_decomposition,
    route_to_workers,
)


# ---------------------------------------------------------------------------
# parse_decomposition
# ---------------------------------------------------------------------------

def test_parse_happy_path() -> None:
    text = json.dumps({
        "rationale": "The question spans finance and regulation.",
        "sub_tasks": [
            {"category": "financial", "question": "What breaks if capital ratios fall?", "priority": 0.9},
            {"category": "regulatory", "question": "Which regs trigger at scale?", "priority": 0.7},
        ],
    })
    decomp = parse_decomposition(text)
    assert len(decomp.sub_tasks) == 2
    assert decomp.rationale.startswith("The question spans")
    assert decomp.sub_tasks[0].category == "financial"
    assert decomp.sub_tasks[0].priority == 0.9


def test_parse_skips_unknown_categories() -> None:
    text = json.dumps({
        "sub_tasks": [
            {"category": "financial", "question": "ok", "priority": 0.5},
            {"category": "astrology", "question": "not a real category", "priority": 0.5},
        ],
    })
    decomp = parse_decomposition(text)
    assert len(decomp.sub_tasks) == 1
    assert decomp.sub_tasks[0].category == "financial"


def test_parse_extended_categories() -> None:
    text = json.dumps({
        "sub_tasks": [{"category": "vibes", "question": "how does it feel", "priority": 0.5}],
    })
    decomp = parse_decomposition(text, allowed_categories=("vibes",))
    assert len(decomp.sub_tasks) == 1


def test_parse_clamps_priority() -> None:
    text = json.dumps({
        "sub_tasks": [
            {"category": "financial", "question": "q", "priority": 2.0},
            {"category": "financial", "question": "q", "priority": -1.0},
        ],
    })
    decomp = parse_decomposition(text)
    assert [t.priority for t in decomp.sub_tasks] == [1.0, 0.0]


def test_parse_malformed_returns_empty() -> None:
    assert parse_decomposition("").sub_tasks == []
    assert parse_decomposition("not json").sub_tasks == []
    assert parse_decomposition('{"sub_tasks": "not a list"}').sub_tasks == []


def test_parse_handles_markdown_fence() -> None:
    text = (
        "Here is the decomposition:\n"
        "```json\n"
        + json.dumps({"sub_tasks": [{"category": "financial", "question": "q", "priority": 0.5}]})
        + "\n```"
    )
    decomp = parse_decomposition(text)
    assert len(decomp.sub_tasks) == 1


# ---------------------------------------------------------------------------
# route_to_workers
# ---------------------------------------------------------------------------

def test_route_uses_context_scope_first() -> None:
    workers = [
        {"key": "cto", "name": "CTO", "context_scope": ["technical"]},
        {"key": "cfo", "name": "CFO", "context_scope": ["financial"]},
    ]
    sub_tasks = [
        SubTask(category="financial", question="q1"),
        SubTask(category="technical", question="q2"),
    ]
    routed = route_to_workers(sub_tasks, workers)
    assert routed[0][1]["name"] == "CFO"
    assert routed[1][1]["name"] == "CTO"


def test_route_falls_back_to_name_match() -> None:
    workers = [
        {"key": "regulatory-counsel", "name": "Regulatory Counsel"},
        {"key": "ceo", "name": "CEO"},
    ]
    sub_tasks = [SubTask(category="regulatory", question="q1")]
    routed = route_to_workers(sub_tasks, workers)
    assert routed[0][1]["name"] == "Regulatory Counsel"


def test_route_balances_load_when_no_match() -> None:
    workers = [
        {"key": "generalist-a", "name": "A"},
        {"key": "generalist-b", "name": "B"},
    ]
    sub_tasks = [
        SubTask(category="market", question="q1"),
        SubTask(category="market", question="q2"),
        SubTask(category="market", question="q3"),
    ]
    routed = route_to_workers(sub_tasks, workers)
    assigned = [r[1]["name"] for r in routed]
    assert assigned.count("A") >= 1 and assigned.count("B") >= 1


def test_route_empty_workers_returns_empty() -> None:
    assert route_to_workers([SubTask("financial", "q")], []) == []


# ---------------------------------------------------------------------------
# delegate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delegate_dispatches_and_collects() -> None:
    workers = [
        {"key": "cfo", "name": "CFO", "context_scope": ["financial"]},
        {"key": "cto", "name": "CTO", "context_scope": ["technical"]},
    ]
    decomp = Decomposition(sub_tasks=[
        SubTask("financial", "What breaks?", priority=0.9),
        SubTask("technical", "Where's the cliff?", priority=0.6),
    ])

    async def runner(st, worker):
        return f"{worker['name']} says: about {st.category}"

    results = await delegate(decomp, workers, runner)
    assert len(results) == 2
    assert all(r.succeeded for r in results)
    assert "CFO says" in results[0].response
    assert "CTO says" in results[1].response


@pytest.mark.asyncio
async def test_delegate_isolates_worker_failures() -> None:
    workers = [
        {"key": "a", "name": "A", "context_scope": ["financial"]},
        {"key": "b", "name": "B", "context_scope": ["technical"]},
    ]
    decomp = Decomposition(sub_tasks=[
        SubTask("financial", "q1"),
        SubTask("technical", "q2"),
    ])

    async def runner(st, worker):
        if worker["name"] == "A":
            raise RuntimeError("A broke")
        return "B is fine"

    results = await delegate(decomp, workers, runner)
    assert len(results) == 2
    failed = [r for r in results if not r.succeeded]
    assert len(failed) == 1
    assert "A broke" in failed[0].error


@pytest.mark.asyncio
async def test_delegate_respects_max_concurrent() -> None:
    workers = [{"key": f"w{i}", "name": f"W{i}"} for i in range(4)]
    decomp = Decomposition(sub_tasks=[
        SubTask("financial", f"q{i}", priority=0.5) for i in range(4)
    ])

    max_concurrent_seen = 0
    active = 0
    lock = asyncio.Lock()

    async def runner(st, worker):
        nonlocal active, max_concurrent_seen
        async with lock:
            active += 1
            max_concurrent_seen = max(max_concurrent_seen, active)
        await asyncio.sleep(0.01)
        async with lock:
            active -= 1
        return "ok"

    await delegate(decomp, workers, runner, max_concurrent=2)
    assert max_concurrent_seen <= 2


@pytest.mark.asyncio
async def test_delegate_empty_decomposition_returns_empty() -> None:
    async def runner(st, worker):
        return "should not be called"

    results = await delegate(Decomposition(), [{"key": "x", "name": "X"}], runner)
    assert results == []


# ---------------------------------------------------------------------------
# merge_by_category + format_results_for_synthesis
# ---------------------------------------------------------------------------

def _mk(category: str, worker: str, priority: float, response: str = "resp") -> SubResult:
    return SubResult(
        sub_task=SubTask(category=category, question=f"q-{category}", priority=priority),
        worker_name=worker,
        response=response,
    )


def test_merge_groups_by_category_and_ranks_by_priority() -> None:
    results = [
        _mk("financial", "CFO", 0.3),
        _mk("financial", "CEO", 0.9),
        _mk("technical", "CTO", 0.7),
    ]
    grouped = merge_by_category(results)
    assert set(grouped.keys()) == {"financial", "technical"}
    assert grouped["financial"][0].worker_name == "CEO"


def test_merge_drops_failed_results() -> None:
    good = _mk("financial", "CFO", 0.5)
    bad = SubResult(
        sub_task=SubTask("financial", "q"),
        worker_name="broken",
        response="",
        error="crashed",
    )
    grouped = merge_by_category([good, bad])
    assert len(grouped["financial"]) == 1
    assert grouped["financial"][0].worker_name == "CFO"


def test_format_results_empty() -> None:
    assert "no successful" in format_results_for_synthesis([]).lower()


def test_format_results_orders_categories_alphabetically() -> None:
    formatted = format_results_for_synthesis([
        _mk("technical", "CTO", 0.5),
        _mk("financial", "CFO", 0.5),
    ])
    assert formatted.index("## FINANCIAL") < formatted.index("## TECHNICAL")
