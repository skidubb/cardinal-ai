"""Pluggable connector framework for tenant data sources.

A Connector knows how to:
1. Authenticate against a source (HubSpot, Notion, Granola, Drive, Slack, etc.)
2. Discover items in scope (companies, pages, meetings, files, messages)
3. Fetch each item and convert to an Episode for graph ingest

Two connector flavors:
- **Direct API** -- pure Python, runs anywhere (e.g. HubSpot via hubspot-api-client).
- **MCP-driven** -- runs inside Claude Code via the ce-graph-backfill agent.

Both produce the same Episode shape so the ingest path is unified.
"""

from ce_graph.connectors.base import Connector, ConnectorRegistry, Episode, SourceItem

REGISTRY = ConnectorRegistry()

__all__ = ["Connector", "ConnectorRegistry", "Episode", "SourceItem", "REGISTRY"]
