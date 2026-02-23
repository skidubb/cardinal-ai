"""Pinecone-backed memory store for agent institutional memory.

Uses the ce-c-suite-learning index with integrated inference
(text in, results out — no local embedding model needed).
Each agent role maps to a Pinecone namespace.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from csuite.config import get_settings

logger = logging.getLogger(__name__)

# Lazy-loaded Pinecone index
_index: Any = None


def _get_index() -> Any:
    """Lazy-load Pinecone index for the learning store."""
    global _index
    if _index is None:
        from pinecone import Pinecone

        settings = get_settings()
        if not settings.pinecone_api_key or not settings.pinecone_learning_index_host:
            raise RuntimeError("Pinecone learning index not configured")
        pc = Pinecone(api_key=settings.pinecone_api_key)
        _index = pc.Index(host=settings.pinecone_learning_index_host)
    return _index


class MemoryStore:
    """Semantic memory store backed by Pinecone integrated inference."""

    VALID_TYPES = {"decision", "analysis", "feedback", "fact"}

    def __init__(self) -> None:
        settings = get_settings()
        self.enabled = settings.memory_enabled and bool(
            settings.pinecone_api_key and settings.pinecone_learning_index_host
        )

    def store(
        self,
        role: str,
        content: str,
        memory_type: str,
        *,
        session_id: str = "",
        summary: str = "",
    ) -> bool:
        """Store a memory record in Pinecone. Returns True on success."""
        if not self.enabled:
            return False
        try:
            index = _get_index()
            record_id = f"{role}-{int(time.time() * 1000)}"
            record = {
                "_id": record_id,
                "text": content[:2000],
                "summary": summary or content[:200],
                "memory_type": memory_type,
                "session_id": session_id,
                "timestamp": int(time.time()),
            }
            index.upsert_records(namespace=role, records=[record])
            return True
        except Exception:
            logger.warning("Failed to store memory", exc_info=True)
            return False

    def retrieve(self, role: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Query semantic memory via Pinecone integrated inference."""
        if not self.enabled:
            return []
        try:
            index = _get_index()
            response = index.search(
                namespace=role,
                query={"top_k": min(max(top_k, 1), 10), "inputs": {"text": query}},
            )
            results = []
            for hit in response.get("result", {}).get("hits", []):
                fields = hit.get("fields", {})
                results.append({
                    "content": fields.get("text", ""),
                    "summary": fields.get("summary", ""),
                    "memory_type": fields.get("memory_type", ""),
                    "timestamp": fields.get("timestamp", 0),
                    "score": hit.get("_score", 0.0),
                })
            return results
        except Exception:
            logger.warning("Failed to retrieve memories", exc_info=True)
            return []
