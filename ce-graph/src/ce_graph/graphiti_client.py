"""Graphiti integration backed by FalkorDB -- tenant-scoped.

Each tenant maps to a separate FalkorDB graph (strongest isolation).
Use ``GraphClient.for_tenant("acme")`` to get a client bound to that tenant.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from ce_shared.env import find_and_load_dotenv

from ce_graph.tenancy import TenantConfig, current_tenant, load_tenant

logger = logging.getLogger(__name__)


class GraphClient:
    """High-level Graphiti client -- tenant-scoped.

    Use ``await GraphClient.for_tenant("acme")`` to get a connected client
    bound to the ``acme`` tenant's graph.
    """

    def __init__(
        self,
        falkor_url: str | None = None,
        graph_name: str | None = None,
        llm_model: str | None = None,
        tenant: TenantConfig | None = None,
    ) -> None:
        find_and_load_dotenv()
        self.falkor_url = falkor_url or os.environ.get(
            "FALKORDB_URL", "redis://localhost:6379"
        )
        self.tenant = tenant
        self.graph_name = graph_name or (tenant.graph_name if tenant else None) or os.environ.get(
            "FALKORDB_GRAPH_NAME", "cardinal_element"
        )
        self.llm_model = llm_model or os.environ.get(
            "GRAPH_LLM_MODEL", "claude-haiku-4-5-20251001"
        )
        self._graphiti: Any | None = None

    @classmethod
    async def connect(cls, **kwargs: Any) -> "GraphClient":
        """Connect to the env-default graph. Prefer ``for_tenant`` for explicit tenancy."""
        client = cls(**kwargs)
        await client._init_graphiti()
        return client

    @classmethod
    async def for_tenant(cls, slug: str | None = None, **kwargs: Any) -> "GraphClient":
        """Connect scoped to ``slug`` (or the env-derived current tenant)."""
        tenant = load_tenant(slug or current_tenant())
        client = cls(tenant=tenant, **kwargs)
        await client._init_graphiti()
        logger.info("GraphClient bound to tenant=%s graph=%s", tenant.slug, tenant.graph_name)
        return client

    async def _init_graphiti(self) -> None:
        from graphiti_core import Graphiti
        from graphiti_core.driver.falkordb_driver import FalkorDriver
        from graphiti_core.llm_client.anthropic_client import AnthropicClient
        from graphiti_core.llm_client.config import LLMConfig

        without_scheme = self.falkor_url.removeprefix("redis://")
        host, _, port = without_scheme.partition(":")
        driver = FalkorDriver(
            host=host or "localhost",
            port=int(port or 6379),
            database=self.graph_name,
        )
        llm_config = LLMConfig(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            model=self.llm_model,
            small_model=self.llm_model,
        )
        llm_client = AnthropicClient(config=llm_config)
        self._graphiti = Graphiti(graph_driver=driver, llm_client=llm_client)
        await self._graphiti.build_indices_and_constraints()

    @property
    def graphiti(self) -> Any:
        if self._graphiti is None:
            raise RuntimeError(
                "GraphClient not initialised. Use `await GraphClient.for_tenant(slug)`."
            )
        return self._graphiti

    async def add_episode(
        self,
        name: str,
        body: str,
        source_type: str = "manual_entry",
        source_id: str | None = None,
        timestamp: datetime | None = None,
    ) -> Any:
        from graphiti_core.nodes import EpisodeType

        return await self.graphiti.add_episode(
            name=name,
            episode_body=body,
            source=EpisodeType.text,
            source_description=f"{source_type}:{source_id or name}",
            reference_time=timestamp or datetime.now(timezone.utc),
        )

    async def search(self, query: str, limit: int = 10) -> list[Any]:
        return await self.graphiti.search(query=query, num_results=limit)

    async def find_decisions_for_client(self, client_name: str, limit: int = 20) -> list[Any]:
        return await self.search(
            f"decisions, recommendations, and outcomes for client {client_name}",
            limit=limit,
        )

    async def find_corrections_for_scope(
        self, scope: str, target: str | None = None
    ) -> list[Any]:
        q = f"corrections that apply to {scope}"
        if target:
            q += f" {target}"
        return await self.search(q, limit=50)

    async def find_lessons_for_vertical(self, vertical: str, limit: int = 20) -> list[Any]:
        return await self.search(
            f"lessons learned and patterns from engagements in the {vertical} vertical",
            limit=limit,
        )

    async def close(self) -> None:
        if self._graphiti is not None:
            await self._graphiti.close()
            self._graphiti = None


__all__ = ["GraphClient"]
