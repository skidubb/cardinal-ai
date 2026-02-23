"""Experience log — persistent lessons learned per agent role."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from csuite.config import get_settings

CORRECTION_PATTERNS = re.compile(
    r"(?i)(no,?\s+actually|that'?s wrong|don'?t recommend|incorrect|not what I|stop suggesting|"
    r"never use|wrong approach|bad advice|please don'?t)"
)

# Lazy-loaded global
_store: Any = None


def _get_store() -> Any:
    global _store
    if _store is None:
        from csuite.storage import DuckDBStore
        settings = get_settings()
        _store = DuckDBStore(db_path=settings.duckdb_path)
    return _store


class ExperienceLog:
    """Append-only lesson log with rotating window, backed by DuckDB."""

    MAX_LESSONS = 50

    def __init__(self, base_dir: Path | None = None) -> None:
        # base_dir kept for signature compat but unused with DuckDB
        pass

    def add_lesson(self, role: str, lesson_text: str) -> None:
        """Append a timestamped lesson."""
        db = _get_store()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        db.add_lesson(role=role, lesson=lesson_text, timestamp=timestamp)

    def get_lessons(self, role: str, limit: int = 50) -> str:
        """Return most recent lessons as a string for prompt injection."""
        db = _get_store()
        rows = db.get_lessons(role=role, limit=limit)
        if not rows:
            return ""
        return "\n".join(f"- [{ts}] {lesson}" for ts, lesson in reversed(rows))

    @staticmethod
    def detect_correction(user_message: str) -> bool:
        """Check if a user message contains correction patterns."""
        return bool(CORRECTION_PATTERNS.search(user_message))
