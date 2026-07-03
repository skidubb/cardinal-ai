"""Real backend implementations for the unified knowledge facade.

Each backend is guarded by its own lazy import so a slim environment
(no Pinecone client, no ce-db, no csuite) doesn't break the facade —
missing backends simply don't register.

The Pinecone backend uses integrated inference (server-side embedding)
so it works against Cardinal Element's 3072-dim indexes without the
caller needing to embed the query. The Postgres backend does a
best-effort text search across the `runs` table's synthesis + question
columns. The DuckDB backend queries the ExperienceLog.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from protocols.knowledge import Hit, SearchScope, register_backend


_log = logging.getLogger(__name__)


# Default index → namespaces mapping. Callers can override via
# SearchScope.pinecone_indexes and .pinecone_namespaces.
_DEFAULT_PINECONE_INDEXES: tuple[str, ...] = (
    "ce-gtm-knowledge",
    "ce-c-suite-learning",
    "multi-agent-kb",
)


# ---------------------------------------------------------------------------
# Pinecone
# ---------------------------------------------------------------------------

async def _pinecone_backend(query: str, scope: SearchScope) -> list[Hit]:
    """Query configured Pinecone indexes and return normalized hits."""
    try:
        from pinecone import Pinecone
    except ImportError:
        return []

    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        return []

    try:
        pc = Pinecone(api_key=api_key)
    except BaseException as e:  # noqa: BLE001 — pinecone can raise strange errors
        _log.debug("pinecone client init failed: %s", e)
        return []

    indexes = scope.pinecone_indexes or _DEFAULT_PINECONE_INDEXES
    namespaces = scope.pinecone_namespaces or ("",)
    per_query_k = max(1, scope.top_k)

    hits: list[Hit] = []
    for index_name in indexes:
        try:
            idx = pc.Index(index_name)
        except BaseException as e:  # noqa: BLE001
            _log.debug("pinecone open index %s failed: %s", index_name, e)
            continue

        for namespace in namespaces:
            try:
                # Integrated inference: server-side embedding.
                result = idx.search(
                    namespace=namespace,
                    query={"inputs": {"text": query}, "top_k": per_query_k},
                )
            except BaseException as e:  # noqa: BLE001
                _log.debug(
                    "pinecone search failed on %s / %s: %s",
                    index_name, namespace or "(default)", e,
                )
                continue

            for match in _extract_matches(result):
                text = str(match.get("text") or match.get("chunk_text") or "").strip()
                if not text:
                    continue
                try:
                    score = float(match.get("_score") or match.get("score") or 0.0)
                except (TypeError, ValueError):
                    score = 0.0
                metadata = match.get("metadata") if isinstance(match, dict) else None
                if not isinstance(metadata, dict):
                    metadata = {"id": match.get("_id") or match.get("id")}
                hits.append(
                    Hit(
                        text=text,
                        score=score,
                        source=f"pinecone:{index_name}"
                        + (f"/{namespace}" if namespace else ""),
                        metadata={**metadata, "index": index_name, "namespace": namespace},
                    )
                )
    return hits


def _extract_matches(result: Any) -> list[dict[str, Any]]:
    """Best-effort extractor for the different Pinecone SDK result shapes."""
    if isinstance(result, dict):
        result_obj = result.get("result")
        if isinstance(result_obj, dict):
            hits = result_obj.get("hits", [])
            if isinstance(hits, list):
                return [h for h in hits if isinstance(h, dict)]
        matches = result.get("matches")
        if isinstance(matches, list):
            return [m for m in matches if isinstance(m, dict)]
    hits_attr = getattr(result, "hits", None)
    if isinstance(hits_attr, list):
        return [h for h in hits_attr if isinstance(h, dict)]
    return []


# ---------------------------------------------------------------------------
# Postgres runs table
# ---------------------------------------------------------------------------

async def _runs_backend(query: str, scope: SearchScope) -> list[Hit]:
    """Search Postgres `runs` table for prior runs matching the query."""
    if not scope.include_runs:
        return []
    try:
        from ce_db import Run, get_session
    except ImportError:
        return []

    try:
        from sqlalchemy import or_, select

        pattern = f"%{query.strip()[:200]}%"
        async with get_session() as session:
            stmt = (
                select(Run)
                .where(
                    or_(
                        Run.question.ilike(pattern),
                        Run.result_summary.ilike(pattern),
                    )
                )
                .order_by(Run.completed_at.desc())
                .limit(scope.top_k)
            )
            rows = (await session.execute(stmt)).scalars().all()
    except BaseException as e:  # noqa: BLE001
        _log.debug("runs backend query failed: %s", e)
        return []

    hits: list[Hit] = []
    for run in rows:
        summary = (run.result_summary or run.question or "")[:1_000]
        if not summary.strip():
            continue
        hits.append(
            Hit(
                text=summary,
                score=_recency_score(run.completed_at),
                source=f"postgres:runs/{run.protocol_key}",
                metadata={
                    "run_id": str(getattr(run, "id", "")),
                    "protocol_key": run.protocol_key,
                    "question": (run.question or "")[:200],
                    "completed_at": str(getattr(run, "completed_at", "")),
                    "status": run.status,
                },
            )
        )
    return hits


def _recency_score(completed_at: Any) -> float:
    """Convert a datetime to a 0.5–1.0 score biased toward recency."""
    if completed_at is None:
        return 0.5
    try:
        import datetime as _dt

        if isinstance(completed_at, _dt.datetime):
            delta = _dt.datetime.now(completed_at.tzinfo or _dt.timezone.utc) - completed_at
            days = max(0.0, delta.total_seconds() / 86_400)
        else:
            return 0.5
    except BaseException:  # noqa: BLE001
        return 0.5
    # 0 days → 1.0, 30 days → ~0.75, 180 days → ~0.55, asymptote 0.5.
    return round(0.5 + 0.5 * (1.0 / (1.0 + days / 30.0)), 4)


# ---------------------------------------------------------------------------
# DuckDB ExperienceLog
# ---------------------------------------------------------------------------

async def _experience_backend(query: str, scope: SearchScope) -> list[Hit]:
    """Search the DuckDB ExperienceLog for lessons matching the query."""
    if not scope.include_experience:
        return []
    try:
        from csuite.learning.experience_log import ExperienceLog
    except ImportError:
        return []

    try:
        log = ExperienceLog()
    except BaseException as e:  # noqa: BLE001
        _log.debug("experience log open failed: %s", e)
        return []

    # Try a few plausible read APIs — the ExperienceLog interface has evolved.
    rows: list[dict[str, Any]] = []
    for method_name in ("search", "retrieve", "find_similar", "all"):
        method = getattr(log, method_name, None)
        if not callable(method):
            continue
        try:
            candidate = method(query, limit=scope.top_k) if method_name != "all" else method()
        except TypeError:
            try:
                candidate = method(query)
            except BaseException:  # noqa: BLE001
                continue
        except BaseException:  # noqa: BLE001
            continue
        rows = _normalize_experience_rows(candidate)
        if rows:
            break

    hits: list[Hit] = []
    for row in rows[: scope.top_k]:
        text = str(row.get("lesson") or row.get("text") or row.get("content") or "").strip()
        if not text:
            continue
        try:
            score = float(row.get("score", 0.7))
        except (TypeError, ValueError):
            score = 0.7
        hits.append(
            Hit(
                text=text,
                score=score,
                source="duckdb:experience",
                metadata={k: v for k, v in row.items() if k not in ("lesson", "text", "content")},
            )
        )
    return hits


def _normalize_experience_rows(candidate: Any) -> list[dict[str, Any]]:
    if candidate is None:
        return []
    if isinstance(candidate, list):
        return [c for c in candidate if isinstance(c, dict)]
    if hasattr(candidate, "to_dict"):
        try:
            data = candidate.to_dict(orient="records")
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
        except BaseException:  # noqa: BLE001
            pass
    return []


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_all() -> tuple[str, ...]:
    """Register the real backends. Returns the names that successfully registered.

    Idempotent — calling twice re-registers the same names. Missing libraries
    do not raise; the backend simply doesn't register.
    """
    registered: list[str] = []

    # Pinecone
    try:
        import pinecone  # noqa: F401
        if os.getenv("PINECONE_API_KEY"):
            register_backend("pinecone", _pinecone_backend)
            registered.append("pinecone")
    except ImportError:
        pass

    # Postgres runs
    try:
        import ce_db  # noqa: F401
        register_backend("runs", _runs_backend)
        registered.append("runs")
    except ImportError:
        pass

    # DuckDB experience log
    try:
        from csuite.learning.experience_log import ExperienceLog  # noqa: F401
        register_backend("experience", _experience_backend)
        registered.append("experience")
    except ImportError:
        pass

    return tuple(registered)
