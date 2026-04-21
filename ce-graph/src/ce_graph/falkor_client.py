"""Thin FalkorDB connection wrapper -- tenant-scoped.

Each tenant gets its own FalkorDB graph (strongest isolation, no cross-tenant
queries possible). Pass ``tenant_slug`` to scope all operations.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from falkordb import FalkorDB

from ce_graph.tenancy import TenantConfig, current_tenant, load_tenant

DEFAULT_GRAPH_NAME = "cardinal_element"


class FalkorClient:
    """Lightweight wrapper around the FalkorDB Python SDK -- tenant-scoped.

    Use ``FalkorClient.for_tenant("imagine-wireless")`` to get a client
    bound to that tenant's graph.
    """

    def __init__(
        self,
        url: str | None = None,
        graph_name: str | None = None,
        tenant: TenantConfig | None = None,
    ) -> None:
        self.url = url or os.environ.get("FALKORDB_URL", "redis://localhost:6379")
        self.tenant = tenant
        self.graph_name = graph_name or (tenant.graph_name if tenant else None) or os.environ.get(
            "FALKORDB_GRAPH_NAME", DEFAULT_GRAPH_NAME
        )
        self._db: FalkorDB | None = None

    @classmethod
    def for_tenant(cls, slug: str | None = None, url: str | None = None) -> "FalkorClient":
        """Construct a client scoped to ``slug`` (or the env-derived current tenant)."""
        tenant = load_tenant(slug or current_tenant())
        return cls(url=url, tenant=tenant)

    def connect(self) -> FalkorDB:
        if self._db is None:
            if self.url.startswith("redis://"):
                without_scheme = self.url.removeprefix("redis://")
                host, _, port = without_scheme.partition(":")
                self._db = FalkorDB(host=host or "localhost", port=int(port or 6379))
            else:
                self._db = FalkorDB.from_url(self.url)
        return self._db

    @property
    def graph(self):
        return self.connect().select_graph(self.graph_name)

    def query(self, cypher: str, params: dict[str, Any] | None = None) -> Any:
        return self.graph.query(cypher, params or {})

    def list_indexes(self) -> list[str]:
        result = self.query("CALL db.indexes()")
        return [row[0] for row in result.result_set]

    def ensure_indexes(self) -> None:
        for label, prop in [
            ("Client", "name"),
            ("Engagement", "name"),
            ("Protocol", "code"),
            ("Agent", "key"),
            ("Decision", "id"),
            ("Correction", "scope"),
            ("Source", "identifier"),
        ]:
            try:
                self.query(f"CREATE INDEX FOR (n:{label}) ON (n.{prop})")
            except Exception:
                pass

    def drop_graph(self) -> None:
        try:
            self.graph.delete()
        except Exception:
            pass

    @asynccontextmanager
    async def session(self):
        try:
            yield self
        finally:
            pass


__all__ = ["FalkorClient", "DEFAULT_GRAPH_NAME"]
