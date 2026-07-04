"""HubSpot connector -- direct API path for entity bootstrap.

Pulls Companies + Contacts + Deals as the seed entities for a tenant's
graph. This is the first thing to run for any new customer -- it creates
the Client / Person / Engagement nodes that everything else hangs off.

Requires:
    pip install hubspot-api-client
    HUBSPOT_PRIVATE_APP_TOKEN in env (per-tenant)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from ce_graph.connectors.base import Episode, SourceItem


class HubSpotConnector:
    """HubSpot connector. SDK is sync; we wrap every call in ``asyncio.to_thread``
    so we don't block the event loop during pagination of large CRMs."""

    name = "hubspot"
    requires_mcp = False

    def __init__(self) -> None:
        self._client: Any = None
        self._token: str | None = None

    async def authenticate(self, config: dict[str, Any]) -> None:
        import os
        token_env = config.get("token_env", "HUBSPOT_PRIVATE_APP_TOKEN")
        token = os.environ.get(token_env)
        if not token:
            raise RuntimeError(f"HubSpot token env var '{token_env}' is empty")
        try:
            from hubspot import HubSpot  # type: ignore
        except ImportError as e:
            raise RuntimeError("Install: pip install hubspot-api-client") from e
        self._client = HubSpot(access_token=token)
        self._token = token
        # Sanity check off-thread to avoid blocking the loop
        await asyncio.to_thread(self._client.crm.owners.owners_api.get_page, limit=1)

    async def discover(self, since: datetime | None = None) -> list[SourceItem]:
        if self._client is None:
            raise RuntimeError("Call authenticate() first")
        items: list[SourceItem] = []
        for company in await asyncio.to_thread(self._collect, "companies"):
            items.append(SourceItem(
                source_type="hubspot_company",
                identifier=str(company.id),
                title=company.properties.get("name"),
                metadata=company.properties,
            ))
        for contact in await asyncio.to_thread(self._collect, "contacts"):
            full = " ".join(
                p for p in [
                    contact.properties.get("firstname"),
                    contact.properties.get("lastname"),
                ] if p
            ).strip() or contact.properties.get("email", "(no name)")
            items.append(SourceItem(
                source_type="hubspot_contact",
                identifier=str(contact.id),
                title=full,
                metadata=contact.properties,
            ))
        for deal in await asyncio.to_thread(self._collect, "deals"):
            items.append(SourceItem(
                source_type="hubspot_deal",
                identifier=str(deal.id),
                title=deal.properties.get("dealname"),
                metadata=deal.properties,
            ))
        return items

    def _collect(self, object_type: str) -> list[Any]:
        """Collect all items of ``object_type`` synchronously. Called via to_thread."""
        api = getattr(self._client.crm, object_type).basic_api
        out: list[Any] = []
        after: str | None = None
        while True:
            page = api.get_page(limit=100, after=after)
            out.extend(page.results)
            if page.paging is None:
                break
            after = page.paging.next.after
        return out

    async def fetch(self, item: SourceItem) -> Episode | None:
        title = item.title or item.identifier
        body_lines = [
            f"HubSpot {item.source_type.removeprefix('hubspot_')}: {title}",
            f"ID: {item.identifier}",
            "",
        ]
        for k, v in (item.metadata or {}).items():
            if v not in (None, "", []):
                body_lines.append(f"{k}: {v}")
        return Episode(
            name=f"hubspot :: {item.source_type.removeprefix('hubspot_')} :: {title}",
            body="\n".join(body_lines),
            source_type=item.source_type,
            source_id=item.identifier,
            timestamp=item.last_modified or datetime.now(timezone.utc),
        )


def register(registry: Any) -> None:
    registry.register("hubspot", HubSpotConnector)


__all__ = ["HubSpotConnector", "register"]
