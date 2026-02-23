"""Preference tracker — records user feedback and builds preference context."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from csuite.config import get_settings

# Lazy-loaded global
_store: Any = None


def _get_store() -> Any:
    global _store
    if _store is None:
        from csuite.storage import DuckDBStore
        settings = get_settings()
        _store = DuckDBStore(db_path=settings.duckdb_path)
    return _store


DEFAULT_PREFS: dict[str, Any] = {
    "communication_style": [],
    "framework_preferences": [],
    "risk_tolerance": "",
    "corrections": [],
}


class PreferenceTracker:
    """Tracks per-role user preferences from feedback, backed by DuckDB."""

    def __init__(self, base_dir: Path | None = None) -> None:
        # base_dir kept for signature compat but unused with DuckDB
        pass

    def _load(self, role: str) -> dict[str, Any]:
        db = _get_store()
        data = db.load_preferences(role)
        if data is None:
            import copy
            return copy.deepcopy(DEFAULT_PREFS)
        return data

    def _save(self, role: str, data: dict[str, Any]) -> None:
        db = _get_store()
        db.save_preferences(role, data)

    def record_feedback(
        self,
        role: str,
        feedback_type: str,
        detail: str = "",
        *,
        session_id: str = "",
        message_index: int = -1,
    ) -> None:
        """Record a feedback event."""
        data = self._load(role)
        entry = {
            "type": feedback_type,
            "detail": detail,
            "session_id": session_id,
            "message_index": message_index,
            "timestamp": datetime.now().isoformat(),
        }

        if feedback_type == "correction":
            corrections = data.get("corrections", [])
            corrections.append(entry)
            data["corrections"] = corrections[-30:]
        elif feedback_type == "preference":
            prefs = data.get("framework_preferences", [])
            prefs.append(detail)
            data["framework_preferences"] = prefs[-20:]
        else:
            feedback_list = data.get("feedback", [])
            feedback_list.append(entry)
            data["feedback"] = feedback_list[-50:]

        self._save(role, data)

    def get_preference_context(self, role: str) -> str:
        """Return formatted preference string for prompt injection."""
        data = self._load(role)
        parts: list[str] = []

        corrections = data.get("corrections", [])
        if corrections:
            parts.append("Corrections from user:")
            for c in corrections[-10:]:
                parts.append(f"  - {c.get('detail', '')}")

        prefs = data.get("framework_preferences", [])
        if prefs:
            parts.append("Framework/approach preferences:")
            for p in prefs[-10:]:
                parts.append(f"  - {p}")

        risk = data.get("risk_tolerance")
        if risk:
            parts.append(f"Risk tolerance: {risk}")

        styles = data.get("communication_style", [])
        if styles:
            parts.append(f"Communication style: {', '.join(styles[-5:])}")

        return "\n".join(parts)
