"""Shared Blackboard — communal state store for coordination protocols.

Externalized, versioned, role-scoped state. Agents write intelligence;
blackboard owns state; orchestrator owns flow.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from protocols.scoping import filter_context_for_agent, tag_context


@dataclass
class BlackboardEntry:
    entry_id: str
    topic: str
    author: str
    stage: str
    content: Any
    metadata: dict
    version: int
    timestamp: float


class Blackboard:
    """Append-only communal state store with role-scoped reads and watcher callbacks."""

    def __init__(self, protocol_id: str, scoping_rules: dict | None = None):
        self.protocol_id = protocol_id
        self.scoping_rules = scoping_rules or {}
        self._entries: list[BlackboardEntry] = []
        self._watchers: list[Callable[[BlackboardEntry], None]] = []
        self._version_counters: dict[str, int] = {}
        self._start_time = time.time()

    # --- Agent interface ---

    def write(
        self,
        topic: str,
        content: Any,
        author: str,
        stage: str,
        metadata: dict | None = None,
    ) -> BlackboardEntry:
        """Append an immutable entry. Fires all watcher callbacks synchronously."""
        version = self._version_counters.get(topic, 0) + 1
        self._version_counters[topic] = version

        entry = BlackboardEntry(
            entry_id=uuid.uuid4().hex[:12],
            topic=topic,
            author=author,
            stage=stage,
            content=content,
            metadata=metadata or {},
            version=version,
            timestamp=time.time(),
        )
        self._entries.append(entry)

        for cb in self._watchers:
            cb(entry)

        return entry

    def read(self, topic: str, reader: dict | None = None) -> list[BlackboardEntry]:
        """Read all entries for a topic, filtered by reader's scope if provided."""
        entries = [e for e in self._entries if e.topic == topic]
        if reader is None:
            return entries
        return self._filter_by_scope(entries, reader)

    def read_latest(self, topic: str, reader: dict | None = None) -> BlackboardEntry | None:
        """Read the most recent entry for a topic."""
        entries = self.read(topic, reader)
        return entries[-1] if entries else None

    # --- Orchestrator interface (read-only observation) ---

    def on_write(self, callback: Callable[[BlackboardEntry], None]) -> None:
        """Register a watcher callback fired on every write."""
        self._watchers.append(callback)

    def has_topic(self, topic: str) -> bool:
        return any(e.topic == topic for e in self._entries)

    def topics(self) -> set[str]:
        return {e.topic for e in self._entries}

    def stages_completed(self) -> set[str]:
        """Stage names that have at least one write."""
        return {e.stage for e in self._entries}

    def conflicts(self, topic: str) -> list[tuple[BlackboardEntry, BlackboardEntry]] | None:
        """Detect 2+ agents writing same topic+stage with different content."""
        by_stage: dict[str, list[BlackboardEntry]] = {}
        for e in self._entries:
            if e.topic == topic:
                by_stage.setdefault(e.stage, []).append(e)

        pairs = []
        for stage_entries in by_stage.values():
            if len(stage_entries) < 2:
                continue
            for i in range(len(stage_entries)):
                for j in range(i + 1, len(stage_entries)):
                    a, b = stage_entries[i], stage_entries[j]
                    if a.author != b.author and a.content != b.content:
                        pairs.append((a, b))
        return pairs if pairs else None

    def resource_signals(self) -> dict:
        """Aggregated token usage and wall-clock elapsed."""
        total_input = 0
        total_output = 0
        for e in self._entries:
            usage = e.metadata.get("token_usage", {})
            total_input += usage.get("input_tokens", 0)
            total_output += usage.get("output_tokens", 0)
        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "elapsed_seconds": round(time.time() - self._start_time, 3),
            "entry_count": len(self._entries),
        }

    # --- Governance ---

    def snapshot(self) -> dict:
        """Full serializable state for audit."""
        return {
            "protocol_id": self.protocol_id,
            "timestamp": time.time(),
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "topic": e.topic,
                    "author": e.author,
                    "stage": e.stage,
                    "content": e.content,
                    "metadata": e.metadata,
                    "version": e.version,
                    "timestamp": e.timestamp,
                }
                for e in self._entries
            ],
            "resource_signals": self.resource_signals(),
        }

    def to_jsonl(self, path: Path) -> None:
        """Append-only event log of all writes."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            for e in self._entries:
                line = {
                    "type": "blackboard_write",
                    "entry_id": e.entry_id,
                    "topic": e.topic,
                    "author": e.author,
                    "stage": e.stage,
                    "content": e.content if isinstance(e.content, str) else str(e.content)[:500],
                    "metadata": e.metadata,
                    "version": e.version,
                    "timestamp": e.timestamp,
                }
                f.write(json.dumps(line) + "\n")

    # --- Internal ---

    def _filter_by_scope(
        self, entries: list[BlackboardEntry], reader: dict
    ) -> list[BlackboardEntry]:
        """Use scoping.py logic to filter entries by reader's context_scope."""
        scopes = reader.get("context_scope")
        if not scopes:
            return entries  # no scope = sees everything

        allowed = set(scopes)
        if "all" in allowed:
            return entries

        # Check scoping_rules for author-based scope tags
        filtered = []
        for e in entries:
            entry_scope = e.metadata.get("scope", "all")
            if entry_scope == "all" or entry_scope in allowed:
                filtered.append(e)
            elif e.author == "system":
                filtered.append(e)  # system entries always visible
        return filtered
