"""Knowledge base endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter, Query, UploadFile, File

from api.tool_registry import ROLE_KB_NAMESPACES

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _build_namespace_list() -> list[dict]:
    """Build namespace list from role mappings + Pinecone stats if available."""
    ns_roles: dict[str, list[str]] = {}
    for role, namespaces in ROLE_KB_NAMESPACES.items():
        for ns in namespaces:
            if ns not in ns_roles:
                ns_roles[ns] = []
            ns_roles[ns].append(role)

    result = [
        {"name": ns, "vector_count": None, "assigned_roles": sorted(roles)}
        for ns, roles in sorted(ns_roles.items())
    ]

    try:
        from pinecone import Pinecone

        api_key = os.getenv("PINECONE_API_KEY", "")
        if api_key:
            pc = Pinecone(api_key=api_key)
            index_name = os.getenv("PINECONE_INDEX", "ce-gtm-knowledge")
            idx = pc.Index(index_name)
            stats = idx.describe_index_stats()
            ns_stats = stats.get("namespaces", {})
            for item in result:
                ns_data = ns_stats.get(item["name"])
                if ns_data:
                    item["vector_count"] = ns_data.get("vector_count", 0)
            for ns_name, ns_data in ns_stats.items():
                if not any(r["name"] == ns_name for r in result):
                    result.append({
                        "name": ns_name,
                        "vector_count": ns_data.get("vector_count", 0),
                        "assigned_roles": [],
                    })
    except Exception:
        pass

    return result


@router.get("/namespaces")
def list_namespaces() -> list[dict]:
    return _build_namespace_list()


@router.get("/namespaces/{ns}/search")
def search_namespace(ns: str, q: str = Query(..., min_length=1)):
    try:
        from pinecone import Pinecone

        api_key = os.getenv("PINECONE_API_KEY", "")
        if not api_key:
            return {"results": [], "error": "PINECONE_API_KEY not configured"}

        pc = Pinecone(api_key=api_key)
        index_name = os.getenv("PINECONE_INDEX", "ce-gtm-knowledge")
        idx = pc.Index(index_name)

        results = idx.search(
            namespace=ns,
            query={"top_k": 5, "inputs": {"text": q}},
        )

        return {
            "results": [
                {
                    "id": match.get("id", ""),
                    "score": round(match.get("score", 0), 4),
                    "text_preview": (
                        match.get("metadata", {}).get("text", "")
                        or match.get("metadata", {}).get("content", "")
                    )[:500],
                    "metadata": {
                        k: v
                        for k, v in match.get("metadata", {}).items()
                        if k not in ("text", "content")
                    },
                }
                for match in results.get("matches", [])
            ]
        }
    except Exception as e:
        return {"results": [], "error": str(e)}


@router.get("/namespaces/{ns}/stats")
def namespace_stats(ns: str):
    try:
        from pinecone import Pinecone

        api_key = os.getenv("PINECONE_API_KEY", "")
        if not api_key:
            return {"vector_count": None}

        pc = Pinecone(api_key=api_key)
        index_name = os.getenv("PINECONE_INDEX", "ce-gtm-knowledge")
        idx = pc.Index(index_name)
        stats = idx.describe_index_stats()
        ns_data = stats.get("namespaces", {}).get(ns, {})
        return {"vector_count": ns_data.get("vector_count", 0)}
    except Exception:
        return {"vector_count": None}


@router.post("/namespaces/{ns}/upload")
async def upload_to_namespace(ns: str, file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename or "unknown"
    size = len(content)
    return {
        "status": "received",
        "filename": filename,
        "size_bytes": size,
        "namespace": ns,
        "message": f"File '{filename}' ({size} bytes) received. Chunking and embedding pipeline not yet implemented.",
    }
