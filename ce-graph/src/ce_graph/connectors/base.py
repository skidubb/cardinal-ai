"""Connector framework base classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass
class SourceItem:
    """A discoverable item in a source system. Lightweight metadata only --
    not the full content. Used during discovery to build a work queue."""

    source_type: str            # e.g. "notion_page", "hubspot_company"
    identifier: str             # external ID
    title: str | None = None
    url: str | None = None
    last_modified: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Episode:
    """An ingest-ready episode. This is the unit of work the ingest script
    processes. Matches the JSON schema the ce-graph-backfill agent emits."""

    name: str
    body: str
    source_type: str
    source_id: str | None = None
    timestamp: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "body": self.body,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@runtime_checkable
class Connector(Protocol):
    """Connector protocol. Both direct-API and MCP-driven connectors implement this."""

    name: str
    requires_mcp: bool

    async def authenticate(self, config: dict[str, Any]) -> None:
        """Validate credentials. Raise on failure."""
        ...

    async def discover(self, since: datetime | None = None) -> list[SourceItem]:
        """List items in scope. ``since`` filters by last-modified."""
        ...

    async def fetch(self, item: SourceItem) -> Episode | None:
        """Pull full content for ``item`` and shape into an Episode.
        Return None to skip."""
        ...


class ConnectorRegistry:
    """Maps connector name -> Connector class. Used by the CLI and agent."""

    def __init__(self) -> None:
        self._connectors: dict[str, type] = {}

    def register(self, name: str, cls: type) -> None:
        self._connectors[name] = cls

    def get(self, name: str) -> type | None:
        return self._connectors.get(name)

    def list_names(self) -> list[str]:
        return sorted(self._connectors.keys())


__all__ = ["Connector", "ConnectorRegistry", "Episode", "SourceItem"]
