"""Unified knowledge access — one search interface over Pinecone + Postgres + DuckDB.

Cardinal Element writes to five persistence surfaces (Pinecone memory,
Pinecone GTM knowledge, Pinecone academic papers, Postgres runs table,
DuckDB ExperienceLog). Every consumer that needed knowledge historically
had to know which store to hit and how to translate a query for each.

This module provides `search(query, scope) -> list[Hit]` — one interface,
pluggable backends. Consumers say what they want; the facade routes.

Backends are lazily imported so a slim environment (no Pinecone client,
no ce-db) doesn't break the import. Missing backends are logged and
silently skipped — never raise.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Hit:
    """One search result — normalized across every backend."""

    text: str
    score: float
    source: str  # "pinecone:ce-gtm-knowledge", "postgres:runs", "duckdb:experience", …
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "score": round(self.score, 4),
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class SearchScope:
    """Which stores + namespaces to search. Sensible defaults; override per call."""

    # Which Pinecone indexes to hit. Empty tuple means "all configured".
    pinecone_indexes: tuple[str, ...] = ()
    # Which namespaces within each index. Empty means "all in that index".
    pinecone_namespaces: tuple[str, ...] = ()
    # Whether to query Postgres runs table.
    include_runs: bool = False
    # Whether to query the DuckDB experience log.
    include_experience: bool = False
    # Only return hits above this score threshold.
    min_score: float = 0.0
    # Total cap across all backends.
    top_k: int = 10


# ---------------------------------------------------------------------------
# Backend registry
# ---------------------------------------------------------------------------

# A backend callable: (query, scope) -> list[Hit]. Awaitable so async backends
# fit the same signature; sync backends can just wrap their result.
Backend = Callable[[str, SearchScope], Awaitable[list[Hit]]]

_backends: dict[str, Backend] = {}


def register_backend(name: str, backend: Backend) -> None:
    """Register a backend under a short name (e.g. "pinecone", "runs")."""
    _backends[name] = backend


def registered_backends() -> tuple[str, ...]:
    """Names of currently-registered backends."""
    return tuple(_backends.keys())


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def search(query: str, scope: SearchScope | None = None) -> list[Hit]:
    """Search all applicable backends and return merged, ranked hits.

    Never raises. A backend that fails is logged and dropped; results from
    other backends still return. If no backend is registered or all fail,
    returns [].
    """
    if not query.strip():
        return []
    scope = scope or SearchScope(
        include_runs=False, include_experience=False, top_k=10
    )

    all_hits: list[Hit] = []
    for name, backend in _backends.items():
        try:
            hits = await backend(query, scope)
        except BaseException as e:  # noqa: BLE001 — best-effort, catch Rust panics too
            _log.debug("knowledge backend %s failed: %s", name, e, exc_info=True)
            continue
        if not isinstance(hits, list):
            _log.debug("knowledge backend %s returned non-list: %r", name, type(hits))
            continue
        for h in hits:
            if isinstance(h, Hit) and h.score >= scope.min_score:
                all_hits.append(h)

    all_hits.sort(key=lambda h: h.score, reverse=True)
    return all_hits[: scope.top_k]


# ---------------------------------------------------------------------------
# Prompt injection helper — the common consumer shape
# ---------------------------------------------------------------------------

def format_hits_for_prompt(hits: list[Hit], max_chars: int = 3_000) -> str:
    """Render hits as a compact prompt block. Truncates once max_chars is hit."""
    if not hits:
        return "(no relevant knowledge retrieved)"
    lines = ["Relevant knowledge (source | score | excerpt):"]
    total = len(lines[0])
    for h in hits:
        excerpt = h.text.strip().replace("\n", " ")[:220]
        line = f"  [{h.source} | {round(h.score, 2)}] {excerpt}"
        if total + len(line) > max_chars:
            lines.append(f"  … {len(hits) - lines.index(line) + 1} more truncated")
            break
        lines.append(line)
        total += len(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Reference stub backends — replaced by real implementations when the underlying
# libraries are available. Left here so the facade is usable end-to-end even
# in slim environments (tests, headless CI).
# ---------------------------------------------------------------------------

async def _noop_backend(_query: str, _scope: SearchScope) -> list[Hit]:
    return []


def _register_default_backends() -> None:
    """Register best-effort backends. Each guards its own imports.

    Intentionally does NOT raise if a library is missing — the facade must
    remain usable with zero backends registered.
    """

    # Pinecone backend — only registers if the client library is available and
    # a key is set. Actual namespace routing is defined in Agent Builder's
    # `csuite/memory` module; this stub is a placeholder consumers can override.
    try:
        import os

        if os.getenv("PINECONE_API_KEY"):
            register_backend("pinecone", _noop_backend)
    except Exception:
        pass

    # Runs backend — Postgres via ce-db. Only registers if ce-db is importable.
    try:
        import ce_db  # noqa: F401

        register_backend("runs", _noop_backend)
    except ImportError:
        pass

    # Experience log — DuckDB. Only registers if the module is present.
    try:
        from csuite.learning.experience_log import ExperienceLog  # noqa: F401

        register_backend("experience", _noop_backend)
    except ImportError:
        pass


_register_default_backends()
