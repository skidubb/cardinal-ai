"""Hierarchical delegation primitive — coordinator → typed sub-tasks → workers.

Cardinal Element's protocols were audited as B− on subagent orchestration
because delegation was flat: `asyncio.gather` over a fixed agent list, one
identical prompt per agent. Hierarchical delegation adds a layer: a
coordinator agent inspects the question, decomposes it into typed
sub-tasks, and each sub-task is dispatched to a specialized worker.

This module provides the primitive so any protocol can adopt the pattern
without reinventing the coordinator loop. Sub-tasks are typed by category
(e.g. "financial", "regulatory", "technical") so the same worker pool can
handle different problems with different decompositions.

Pure helpers (parse decomposition, route to workers, merge sub-results) are
in this module. The coordinator LLM call is a single `llm_complete` and
lives in the caller's orchestrator — this module doesn't own an LLM
client, so it stays importable in slim environments.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


# Canonical sub-task categories. Protocols can extend this list, but the
# canonical set covers the fragility axes P48 needs plus general categories.
DEFAULT_SUB_TASK_CATEGORIES: tuple[str, ...] = (
    "financial",
    "regulatory",
    "technical",
    "operational",
    "market",
    "strategic",
    "supply-chain",
    "reputational",
)


@dataclass(slots=True)
class SubTask:
    """One typed sub-question emitted by the coordinator."""

    category: str
    question: str
    priority: float = 0.5  # 0–1, coordinator's estimate of importance

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "question": self.question,
            "priority": round(self.priority, 3),
        }


@dataclass(slots=True)
class SubResult:
    """One worker's response to a single sub-task."""

    sub_task: SubTask
    worker_name: str
    response: str
    error: str = ""

    @property
    def succeeded(self) -> bool:
        return not self.error and bool(self.response.strip())

    def as_dict(self) -> dict[str, Any]:
        return {
            "sub_task": self.sub_task.as_dict(),
            "worker_name": self.worker_name,
            "response": self.response,
            "error": self.error,
        }


@dataclass(slots=True)
class Decomposition:
    """The coordinator's output — a list of typed sub-tasks + rationale."""

    sub_tasks: list[SubTask] = field(default_factory=list)
    rationale: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "sub_tasks": [t.as_dict() for t in self.sub_tasks],
            "rationale": self.rationale,
        }


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_decomposition(
    text: str,
    *,
    allowed_categories: tuple[str, ...] = DEFAULT_SUB_TASK_CATEGORIES,
) -> Decomposition:
    """Parse a coordinator's JSON output into a Decomposition. Never raises.

    Expected shape:
        {
          "rationale": "one-paragraph justification",
          "sub_tasks": [
            {"category": "financial", "question": "...", "priority": 0.8},
            ...
          ]
        }

    Sub-tasks with unknown categories, empty questions, or invalid priorities
    are silently dropped. If the whole payload is malformed, returns an
    empty Decomposition — the caller can then fall back to non-hierarchical
    behavior.
    """
    payload = _extract_json_object(text)
    if not isinstance(payload, dict):
        return Decomposition()

    rationale = str(payload.get("rationale", "")).strip()
    raw_tasks = payload.get("sub_tasks", [])
    if not isinstance(raw_tasks, list):
        return Decomposition(rationale=rationale)

    allowed = {c.lower() for c in allowed_categories}
    sub_tasks: list[SubTask] = []
    for item in raw_tasks:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category", "")).strip().lower()
        question = str(item.get("question", "")).strip()
        if not category or not question:
            continue
        if allowed and category not in allowed:
            continue
        try:
            priority = float(item.get("priority", 0.5))
        except (TypeError, ValueError):
            priority = 0.5
        priority = max(0.0, min(1.0, priority))
        sub_tasks.append(
            SubTask(category=category, question=question, priority=priority)
        )
    return Decomposition(sub_tasks=sub_tasks, rationale=rationale)


def _extract_json_object(text: str) -> Any:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def route_to_workers(
    sub_tasks: list[SubTask],
    workers: list[dict],
    *,
    default_scope_key: str = "context_scope",
) -> list[tuple[SubTask, dict]]:
    """Assign each sub-task to the best-matching worker.

    Matching rules, in order:
      1. If a worker's `context_scope` list contains the sub-task category,
         it's a hit.
      2. If a worker's `key` or `name` contains the category as a substring,
         it's a hit.
      3. Otherwise the sub-task rotates through the worker pool by index so
         load is balanced.

    Sub-tasks are returned in the same order they came in — callers can
    reorder by priority if desired.
    """
    if not workers:
        return []

    def _score(worker: dict, sub_task: SubTask) -> int:
        scopes = {str(s).strip().lower() for s in worker.get(default_scope_key, [])}
        if sub_task.category in scopes:
            return 2
        haystack = (str(worker.get("key", "")) + " " + str(worker.get("name", ""))).lower()
        if sub_task.category in haystack:
            return 1
        return 0

    assignments: list[tuple[SubTask, dict]] = []
    rotation_index = 0
    for st in sub_tasks:
        ranked = sorted(workers, key=lambda w: _score(w, st), reverse=True)
        best = ranked[0]
        best_score = _score(best, st)
        if best_score == 0:
            best = workers[rotation_index % len(workers)]
            rotation_index += 1
        assignments.append((st, best))
    return assignments


# ---------------------------------------------------------------------------
# Delegation loop — abstract over the LLM callable
# ---------------------------------------------------------------------------

# A worker-run callable: (sub_task, worker) -> awaitable str.
# Callers own the LLM call — this module stays LLM-agnostic.
WorkerRunner = Callable[[SubTask, dict], Awaitable[str]]


async def delegate(
    decomposition: Decomposition,
    workers: list[dict],
    runner: WorkerRunner,
    *,
    max_concurrent: int | None = None,
) -> list[SubResult]:
    """Dispatch every sub-task in the decomposition to a worker in parallel.

    Failures are contained: a worker exception becomes an errored SubResult,
    other results still return. Semaphore-limited when `max_concurrent` is
    set (default: unlimited).
    """
    assignments = route_to_workers(decomposition.sub_tasks, workers)
    if not assignments:
        return []

    semaphore = asyncio.Semaphore(max_concurrent) if max_concurrent else None

    async def _run(pair: tuple[SubTask, dict]) -> SubResult:
        sub_task, worker = pair

        async def _call() -> SubResult:
            try:
                response = await runner(sub_task, worker)
                return SubResult(
                    sub_task=sub_task,
                    worker_name=worker.get("name", worker.get("key", "worker")),
                    response=response,
                )
            except Exception as e:  # noqa: BLE001
                return SubResult(
                    sub_task=sub_task,
                    worker_name=worker.get("name", worker.get("key", "worker")),
                    response="",
                    error=f"{type(e).__name__}: {e}",
                )

        if semaphore is None:
            return await _call()
        async with semaphore:
            return await _call()

    return await asyncio.gather(*(_run(pair) for pair in assignments))


# ---------------------------------------------------------------------------
# Merging — group by category, rank by priority
# ---------------------------------------------------------------------------

def merge_by_category(results: list[SubResult]) -> dict[str, list[SubResult]]:
    """Group successful results by their sub-task category."""
    grouped: dict[str, list[SubResult]] = {}
    for r in results:
        if r.succeeded:
            grouped.setdefault(r.sub_task.category, []).append(r)
    for category, items in grouped.items():
        items.sort(key=lambda r: r.sub_task.priority, reverse=True)
    return grouped


def format_results_for_synthesis(results: list[SubResult]) -> str:
    """Render worker results as a compact block for the coordinator's next step."""
    grouped = merge_by_category(results)
    if not grouped:
        return "(no successful sub-task responses)"
    lines: list[str] = []
    for category in sorted(grouped.keys()):
        lines.append(f"\n## {category.upper()}")
        for r in grouped[category]:
            lines.append(f"\n### {r.worker_name} (priority={round(r.sub_task.priority, 2)})")
            lines.append(f"Sub-question: {r.sub_task.question}")
            lines.append(f"Response:\n{r.response}")
    return "\n".join(lines).strip()
