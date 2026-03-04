"""Process-wide DuckDB connection provider.

Single shared connection, thread-safe lazy initialization.
"""

import threading
from typing import Any

from csuite.config import get_settings

_lock = threading.Lock()
_store: Any = None


def get_db() -> Any:
    """Return the shared DuckDBStore singleton (thread-safe)."""
    global _store
    if _store is None:
        with _lock:
            if _store is None:  # Double-checked locking
                from csuite.storage.duckdb_store import DuckDBStore

                settings = get_settings()
                _store = DuckDBStore(db_path=settings.duckdb_path)
    return _store
