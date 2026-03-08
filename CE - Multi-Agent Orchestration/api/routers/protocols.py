"""Protocol endpoints."""

from __future__ import annotations

import importlib
import inspect
import re

from fastapi import APIRouter, HTTPException

from api.manifest import get_protocol_manifest

router = APIRouter(prefix="/api/protocols", tags=["protocols"])


@router.get("")
def list_protocols() -> list[dict]:
    return get_protocol_manifest()


@router.get("/{key}/stages")
def get_protocol_stages(key: str):
    """Extract stage information from a protocol's orchestrator."""
    manifest = get_protocol_manifest()
    proto = next((p for p in manifest if p["key"] == key), None)
    if not proto:
        raise HTTPException(status_code=404, detail=f"Protocol '{key}' not found")

    protocol_id = proto["protocol_id"]

    # Try to import the orchestrator module
    mod = None
    # Build candidate module paths from protocol_id and key
    candidates = [
        f"protocols.{key}.orchestrator",
    ]
    # Also try protocol_id prefix patterns (e.g., p06_triz)
    if protocol_id:
        candidates.append(f"protocols.{protocol_id}_{key.replace(protocol_id + '_', '')}.orchestrator")
        candidates.append(f"protocols.{key.lstrip('p').lstrip('0123456789').lstrip('_')}.orchestrator")

    for pattern in candidates:
        try:
            mod = importlib.import_module(pattern)
            break
        except (ImportError, ModuleNotFoundError):
            continue

    if mod is None:
        return _fallback_stages(proto)

    # Look for orchestrator class
    orch_class = None
    for name, obj in inspect.getmembers(mod, inspect.isclass):
        if "orchestrator" in name.lower() or "protocol" in name.lower():
            orch_class = obj
            break

    if orch_class is None:
        return _fallback_stages(proto)

    # Try to extract stages from the run method's source
    try:
        source = inspect.getsource(orch_class)
        stages = _extract_stages_from_source(source)
        # For multi-round protocols, the fallback produces a richer diagram than a
        # bare "run_round + synthesize" extraction. Prefer fallback when extraction is thin.
        supports_rounds = proto.get("supports_rounds", False)
        if stages and (len(stages) > 2 or not supports_rounds):
            return {"protocol_id": protocol_id, "protocol_name": proto["name"], "stages": stages}
    except (OSError, TypeError):
        pass

    return _fallback_stages(proto)


def _extract_stages_from_source(source: str) -> list[dict]:
    """Extract stages by analyzing orchestrator source code patterns."""
    stages: list[dict] = []

    # Look for stage comments: "# Stage N: ..." or "# Step N: ..."
    stage_comments = re.findall(r'#\s*(?:Stage|Step|Phase)\s*\d*[:\s-]*(.+)', source)

    # Look for stage method definitions (match _keyword... or _run_keyword...)
    stage_methods = re.findall(
        r'async\s+def\s+(_?(?:(?:run_)?(?:stage|step|phase|round|gather|synthesize|analyze|evaluate|debate|vote|rank))\w*)',
        source,
    )

    if stage_comments:
        for comment in stage_comments:
            name = comment.strip()
            stage_type = _classify_stage(name)
            stages.append({
                "name": name,
                "stage_type": stage_type,
                "depends_on": [stages[-1]["name"]] if stages else [],
                "agents_filter": "all" if stage_type == "agent" else None,
            })
    elif stage_methods:
        for method in stage_methods:
            name = method.lstrip("_").replace("_", " ").strip().title()
            stage_type = _classify_stage(method)
            stages.append({
                "name": name,
                "stage_type": stage_type,
                "depends_on": [stages[-1]["name"]] if stages else [],
                "agents_filter": "all" if stage_type == "agent" else None,
            })

    return stages


def _classify_stage(text: str) -> str:
    """Classify a stage as agent, synthesis, or mechanical."""
    lower = text.lower()
    if any(kw in lower for kw in ("agent", "gather", "parallel", "query", "debate", "round", "vote")):
        return "agent"
    if any(kw in lower for kw in ("synth", "combine", "merge", "final", "summary")):
        return "synthesis"
    return "mechanical"


def _fallback_stages(proto: dict) -> dict:
    """Generate basic stage diagram from protocol metadata."""
    supports_rounds = proto.get("supports_rounds", False)

    stages = [
        {"name": "Input & Agent Assignment", "stage_type": "mechanical", "depends_on": [], "agents_filter": None},
        {"name": "Agent Analysis", "stage_type": "agent", "depends_on": ["Input & Agent Assignment"], "agents_filter": "all"},
    ]

    if supports_rounds:
        stages.append({"name": "Multi-Round Iteration", "stage_type": "agent", "depends_on": ["Agent Analysis"], "agents_filter": "all"})
        stages.append({"name": "Synthesis", "stage_type": "synthesis", "depends_on": ["Multi-Round Iteration"], "agents_filter": None})
    else:
        stages.append({"name": "Synthesis", "stage_type": "synthesis", "depends_on": ["Agent Analysis"], "agents_filter": None})

    stages.append({"name": "Output", "stage_type": "mechanical", "depends_on": ["Synthesis"], "agents_filter": None})

    return {"protocol_id": proto.get("protocol_id", ""), "protocol_name": proto.get("name", ""), "stages": stages}
