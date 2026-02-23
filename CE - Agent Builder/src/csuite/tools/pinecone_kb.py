"""
Pinecone Knowledge Base client for C-Suite agents.

Searches the ce-gtm-knowledge index using Pinecone's integrated inference
(text query in, results out — no local embedding model needed).
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Namespace routing per agent role
# Updated to match actual populated namespaces in ce-gtm-knowledge index (23K+ records)
ROLE_NAMESPACE_MAP: dict[str, list[str]] = {
    "ceo": ["lennys-podcast", "consulting", "revenue-architecture", "general-gtm", "ai-gtm"],
    "cfo": ["revenue-architecture", "general-gtm", "consulting", "topline-podcast"],
    "cto": ["ai-gtm", "general-gtm", "revenue-architecture", "lennys-podcast"],
    "cmo": ["demand-gen", "market-analysis", "general-gtm", "ai-gtm", "topline-podcast"],
    "coo": ["consulting", "general-gtm", "revenue-architecture", "lennys-podcast"],
    "cpo": ["cro-school", "meddic", "lennys-podcast", "general-gtm", "revenue-architecture"],
    "cro": [
        "cro-school", "meddic", "topline-podcast",
        "ai-gtm", "revenue-architecture", "demand-gen",
    ],
}

ALL_NAMESPACES = [
    "lennys-podcast", "topline-podcast", "ai-gtm", "demand-gen",
    "cro-school", "meddic", "consulting", "revenue-architecture",
    "general-gtm", "market-analysis",
]


async def search_knowledge(
    api_key: str,
    index_host: str,
    query: str,
    role: str = "",
    namespace: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Search the GTM knowledge base.

    Uses Pinecone's integrated inference — sends text query directly.

    Args:
        api_key: Pinecone API key
        index_host: Pinecone index host URL
        query: Search query text
        role: Agent role for namespace routing (ignored if namespace given)
        namespace: Explicit namespace override
        top_k: Number of results to return (max 10)
    """
    from pinecone import Pinecone

    top_k = min(max(top_k, 1), 10)
    pc = Pinecone(api_key=api_key)
    index = pc.Index(host=index_host)

    # Determine which namespaces to search
    if namespace and namespace in ALL_NAMESPACES:
        namespaces = [namespace]
    else:
        namespaces = ROLE_NAMESPACE_MAP.get(role.lower(), ["general-gtm"])

    # Search each namespace and collect results
    all_results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for ns in namespaces:
        try:
            response = index.search(
                namespace=ns,
                query={"top_k": top_k, "inputs": {"text": query}},
            )
            for hit in response.get("result", {}).get("hits", []):
                rid = hit.get("_id", "")
                if rid in seen_ids:
                    continue
                seen_ids.add(rid)
                fields = hit.get("fields", {})
                all_results.append({
                    "text": fields.get("text", ""),
                    "source_file": fields.get("source_file", ""),
                    "source_folder": fields.get("source_folder", ""),
                    "namespace": ns,
                    "score": hit.get("_score", 0.0),
                })
        except Exception:
            logger.warning("Pinecone search failed for namespace %s", ns, exc_info=True)

    # Sort by score descending and return top_k
    all_results.sort(key=lambda r: r["score"], reverse=True)
    return all_results[:top_k]


async def handle_pinecone_search(tool_input: dict[str, Any], settings: Any) -> str:
    """Tool handler for pinecone_search_knowledge."""
    if not settings.pinecone_api_key or not settings.pinecone_index_host:
        return json.dumps({"error": "Pinecone not configured (missing API key or index host)"})

    query = tool_input.get("query", "")
    if not query:
        return json.dumps({"error": "query is required"})

    role = tool_input.get("_agent_role", "")
    namespace = tool_input.get("namespace")
    top_k = tool_input.get("top_k", 5)

    try:
        results = await search_knowledge(
            api_key=settings.pinecone_api_key,
            index_host=settings.pinecone_index_host,
            query=query,
            role=role,
            namespace=namespace,
            top_k=int(top_k),
        )
        return json.dumps({"results": results, "count": len(results)})
    except Exception as e:
        logger.warning("Pinecone search failed: %s", e, exc_info=True)
        return json.dumps({"error": f"Pinecone search failed: {str(e)[:200]}"})
