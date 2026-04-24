"""Protocol endpoints."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import re

import json as _json
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from api.context_pipeline import (
    MAX_FILE_SIZE,
    MAX_TOTAL_SIZE,
    RunContext,
    process_uploaded_files,
)
from api.database import engine
from api.manifest import get_protocol_manifest
from api.middleware.clerk_auth import resolve_tenant
from api.models import Run
from api.routers.runs import ProtocolRunRequest
from api.runner import run_protocol_stream

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/protocols", tags=["protocols"])


@router.get("")
def list_protocols() -> list[dict]:
    return get_protocol_manifest()


# ── POST /run — declared BEFORE GET /{key}/stages to avoid route conflict ─────

@router.post("/run")
async def start_protocol_run(
    payload: ProtocolRunRequest,
    request: Request,
    tenant_slug: str = Depends(resolve_tenant),
) -> StreamingResponse:
    """Start a protocol run and stream SSE events.

    Runs complete server-side regardless of client disconnect. Close the
    browser tab and the run keeps going -- check Run History for results.

    The run row is stamped with ``tenant_slug`` derived from the caller's
    Clerk JWT (or the configured fallback for unauthenticated local calls).
    """
    with Session(engine) as session:
        run = Run(
            type="protocol",
            protocol_key=payload.protocol_key,
            question=payload.question,
            status="pending",
            tenant_slug=tenant_slug,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    event_queue: asyncio.Queue = asyncio.Queue(maxsize=5000)

    async def _run_protocol():
        try:
            async for chunk in run_protocol_stream(
                run_id=run_id,
                protocol_key=payload.protocol_key,
                question=payload.question,
                agent_keys=payload.agent_keys,
                thinking_model=payload.thinking_model,
                orchestration_model=payload.orchestration_model,
                rounds=payload.rounds,
                no_tools=payload.no_tools,
                tenant_slug=tenant_slug,
            ):
                await event_queue.put(chunk)
        finally:
            await event_queue.put(None)

    asyncio.create_task(_run_protocol())

    async def _stream():
        while True:
            chunk = await event_queue.get()
            if chunk is None:
                break
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── POST /run/with-context — multipart file upload + run config ────────────

@router.post("/run/with-context")
async def start_protocol_run_with_context(
    request: Request,
    protocol_key: str = Form(...),
    question: str = Form(...),
    agent_keys: str = Form(...),  # JSON-encoded list
    thinking_model: str = Form("claude-opus-4-7"),
    orchestration_model: str = Form("claude-haiku-4-5-20251001"),
    rounds: int | None = Form(None),
    no_tools: bool = Form(False),
    files: list[UploadFile] = File(default=[]),
    tenant_slug: str = Depends(resolve_tenant),
) -> StreamingResponse:
    """Start a protocol run with uploaded context files and stream SSE events.

    The run row is stamped with ``tenant_slug`` derived from the caller's Clerk
    JWT so the resulting run is visible to the caller's list-by-tenant query.
    """
    # Parse agent_keys from JSON string
    try:
        parsed_agent_keys: list[str] = _json.loads(agent_keys)
    except _json.JSONDecodeError:
        raise HTTPException(400, "agent_keys must be a JSON-encoded list of strings")

    # Validate file sizes
    total_size = 0
    for f in files:
        content = await f.read()
        size = len(content)
        if size > MAX_FILE_SIZE:
            raise HTTPException(
                413,
                f"File '{f.filename}' ({size // (1024 * 1024)}MB) exceeds 50MB limit",
            )
        total_size += size
        await f.seek(0)  # reset for downstream read
    if total_size > MAX_TOTAL_SIZE:
        raise HTTPException(
            413,
            f"Total upload size ({total_size // (1024 * 1024)}MB) exceeds 200MB limit",
        )

    # Create Run record
    with Session(engine) as session:
        run = Run(
            type="protocol",
            protocol_key=protocol_key,
            question=question,
            status="pending",
            tenant_slug=tenant_slug,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    # Process uploaded files into RunContext
    run_context: RunContext | None = None
    if files:
        run_context = await process_uploaded_files(run_id, files)
        # Persist context metadata to the Run record
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.context_mode = run_context.mode
                run.context_files_json = run_context.files_metadata_json()
                session.add(run)
                session.commit()

    event_queue_ctx: asyncio.Queue = asyncio.Queue(maxsize=5000)

    async def _run_with_context():
        try:
            async for chunk in run_protocol_stream(
                run_id=run_id,
                protocol_key=protocol_key,
                question=question,
                agent_keys=parsed_agent_keys,
                thinking_model=thinking_model,
                orchestration_model=orchestration_model,
                rounds=rounds,
                no_tools=no_tools,
                context=run_context,
                tenant_slug=tenant_slug,
            ):
                await event_queue_ctx.put(chunk)
        finally:
            await event_queue_ctx.put(None)

    asyncio.create_task(_run_with_context())

    async def _stream():
        while True:
            chunk = await event_queue_ctx.get()
            if chunk is None:
                break
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _stages_from_yaml(key: str) -> list[dict] | None:
    """Load an explicit stage manifest from a protocol's capability.yaml.

    Returns None if no `stages:` array is defined; otherwise returns the stages
    normalized to the shape the frontend expects.
    """
    import yaml
    from pathlib import Path

    cap_file = (
        Path(__file__).resolve().parent.parent.parent
        / "protocols" / key / "capability.yaml"
    )
    if not cap_file.exists():
        return None
    with open(cap_file) as f:
        cap = yaml.safe_load(f) or {}
    raw_stages = cap.get("stages")
    if not isinstance(raw_stages, list) or not raw_stages:
        return None

    stages: list[dict] = []
    for s in raw_stages:
        if not isinstance(s, dict):
            continue
        name = s.get("name") or s.get("key") or ""
        if not name:
            continue
        stages.append({
            "key": s.get("key") or _slugify(name),
            "name": name,
            # `kind` is the canonical YAML field (used by P53-P57 Decentralized
            # Coordination protocols); `stage_type` kept as an alias for older
            # manifests; _classify_stage is a last-resort name heuristic.
            "stage_type": s.get("stage_type") or s.get("kind") or _classify_stage(name),
            "depends_on": s.get("depends_on") or [],
            "agents_filter": s.get("agents_filter"),
            "description": s.get("description") or "",
        })
    return stages or None


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


@router.get("/{key}/stages")
def get_protocol_stages(key: str):
    """Return stage metadata for a protocol.

    Prefers an explicit `stages:` array in the protocol's capability.yaml.
    Falls back to source-code extraction for un-annotated protocols.
    """
    manifest = get_protocol_manifest()
    proto = next((p for p in manifest if p["key"] == key), None)
    if not proto:
        raise HTTPException(status_code=404, detail=f"Protocol '{key}' not found")

    protocol_id = proto["protocol_id"]

    yaml_stages = _stages_from_yaml(key)
    if yaml_stages:
        return {
            "protocol_id": protocol_id,
            "protocol_name": proto["name"],
            "stages": yaml_stages,
            "source": "yaml",
            "orchestration_pattern": proto.get("orchestration_pattern"),
        }

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
            return {
                "protocol_id": protocol_id,
                "protocol_name": proto["name"],
                "stages": stages,
                "orchestration_pattern": proto.get("orchestration_pattern"),
            }
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

    return {
        "protocol_id": proto.get("protocol_id", ""),
        "protocol_name": proto.get("name", ""),
        "stages": stages,
        "orchestration_pattern": proto.get("orchestration_pattern"),
    }
