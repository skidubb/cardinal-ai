"""Marker connectors for MCP-driven sources.

These don't run from Python -- they're handled by the ``ce-graph-backfill``
Claude Code agent which has access to the MCP tools. Registering them here
lets the CLI list them and validate config without trying to instantiate
a Python client.
"""

from __future__ import annotations

from typing import Any

from ce_graph.connectors.base import Episode, SourceItem


class _MCPMarker:
    """Base class for MCP-driven connectors. All methods raise."""

    name: str = "mcp_marker"
    requires_mcp = True

    async def authenticate(self, config: dict[str, Any]) -> None:
        raise NotImplementedError(
            f"Connector '{self.name}' is MCP-driven. Run the ce-graph-backfill "
            f"agent inside Claude Code; it has access to the MCP tools."
        )

    async def discover(self, since: Any = None) -> list[SourceItem]:
        raise NotImplementedError(self.authenticate.__doc__)

    async def fetch(self, item: SourceItem) -> Episode | None:
        raise NotImplementedError(self.authenticate.__doc__)


class NotionConnector(_MCPMarker):
    name = "notion"


class GranolaConnector(_MCPMarker):
    name = "granola"


class GoogleDriveConnector(_MCPMarker):
    name = "google_drive"


class SlackConnector(_MCPMarker):
    name = "slack"


class GmailConnector(_MCPMarker):
    name = "gmail"


def register(registry: Any) -> None:
    registry.register("notion", NotionConnector)
    registry.register("granola", GranolaConnector)
    registry.register("google_drive", GoogleDriveConnector)
    registry.register("slack", SlackConnector)
    registry.register("gmail", GmailConnector)


__all__ = [
    "NotionConnector",
    "GranolaConnector",
    "GoogleDriveConnector",
    "SlackConnector",
    "GmailConnector",
    "register",
]
