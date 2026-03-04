"""Process-wide Pinecone index provider.

Single shared connection, thread-safe lazy initialization.
"""

import threading
from typing import Any

from csuite.config import get_settings

_lock = threading.Lock()
_index: Any = None


def get_pinecone_index() -> Any:
    """Return the shared Pinecone Index singleton (thread-safe)."""
    global _index
    if _index is None:
        with _lock:
            if _index is None:
                from pinecone import Pinecone

                settings = get_settings()
                if not settings.pinecone_api_key or not settings.pinecone_learning_index_host:
                    raise RuntimeError("Pinecone learning index not configured")
                pc = Pinecone(api_key=settings.pinecone_api_key)
                _index = pc.Index(host=settings.pinecone_learning_index_host)
    return _index
