"""Adaptive Router API — POST /api/router/run.

Classify the question via P0a, resolve to a protocol + agent set, then stream
the chosen protocol's SSE events. The router's decision is emitted as the
first SSE event so clients can render a "why this protocol" card before any
stage events arrive.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session

from api.context_pipeline import (
    MAX_FILE_SIZE,
    MAX_TOTAL_SIZE,
    RunContext,
    process_uploaded_files,
)
from api.database import engine
from api.entitlements import (
    FEATURE_PREMIUM_PROTOCOLS,
    FREE_PROTOCOL_KEYS,
    TenantEntitlements,
    check_protocol_allowed,
    require_run_admission,
)
from api.models import Run
from api.runner import run_protocol_stream
from protocols.adaptive_router import (
    AdaptiveRouterOrchestrator,
    Resolver,
)
from protocols.adaptive_router.resolver import DEFAULT_ALLOWLIST
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/router", tags=["router"])


def _resolver_allowlist(te: TenantEntitlements) -> frozenset[str] | None:
    """Free tenants route only within the free protocol set (degrade, not 403)."""
    if FEATURE_PREMIUM_PROTOCOLS in te.entitlements.features:
        return None  # Resolver default allowlist
    return FREE_PROTOCOL_KEYS & DEFAULT_ALLOWLIST


class RouterRunRequest(BaseModel):
    question: str
    agents: list[str] | None = None
    max_cost_tier: str = "medium"
    high_threshold: int = 80
    mid_threshold: int = 50
    rounds: int | None = None
    thinking_model: str = THINKING_MODEL
    orchestration_model: str = ORCHESTRATION_MODEL
    no_tools: bool = False
    # If true, return 409 when confidence is below high_threshold.
    require_high_confidence: bool = False
    # If true, decide only — do not execute. Returns JSON (not SSE).
    dry_run: bool = False


@router.post("/decide")
async def decide_only(payload: RouterRunRequest) -> dict:
    """Classify + resolve without executing. Fast synchronous response."""
    orchestrator = AdaptiveRouterOrchestrator(
        resolver=Resolver(max_cost_tier=payload.max_cost_tier),
        high_threshold=payload.high_threshold,
        mid_threshold=payload.mid_threshold,
    )
    decision = await orchestrator.decide(
        payload.question,
        requested_agents=payload.agents,
    )
    return decision.to_dict()


@router.post("/run")
async def router_run(
    payload: RouterRunRequest,
    request: Request,
    te: TenantEntitlements = Depends(require_run_admission),
) -> StreamingResponse:
    """Classify, resolve, then stream the chosen protocol's SSE events.

    Event order:
      1. `router_decision` — the classification + execution plan
      2. Normal protocol SSE stream (run_start, agent_roster, stage events, …)

    If the decision has no plan or tier=='low', yields `router_error` and stops.
    """
    tenant_slug = te.tenant_slug
    allowlist = _resolver_allowlist(te)
    orchestrator = AdaptiveRouterOrchestrator(
        resolver=Resolver(allowlist=allowlist, max_cost_tier=payload.max_cost_tier)
        if allowlist is not None
        else Resolver(max_cost_tier=payload.max_cost_tier),
        high_threshold=payload.high_threshold,
        mid_threshold=payload.mid_threshold,
    )

    decision = await orchestrator.decide(
        payload.question,
        requested_agents=payload.agents,
    )

    if payload.dry_run:
        # Non-SSE JSON response — lets the UI preview before committing.
        raise HTTPException(status_code=200, detail=decision.to_dict())

    if decision.plan is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_routable_protocol",
                "decision": decision.to_dict(),
            },
        )

    if payload.require_high_confidence and decision.tier != "high":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "low_confidence",
                "tier": decision.tier,
                "decision": decision.to_dict(),
            },
        )

    # Create the Run record so the executed protocol's events persist properly.
    plan = decision.plan
    check_protocol_allowed(plan.protocol_key, te)
    with Session(engine) as session:
        run = Run(
            type="protocol",
            protocol_key=plan.protocol_key,
            question=payload.question,
            status="pending",
            tenant_slug=tenant_slug,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    event_queue: asyncio.Queue = asyncio.Queue(maxsize=5000)

    # Emit the router decision as the first event so the UI can render a card.
    await event_queue.put(
        _sse_event("router_decision", {"run_id": run_id, **decision.to_dict()})
    )

    async def _run():
        try:
            async for chunk in run_protocol_stream(
                run_id=run_id,
                protocol_key=plan.protocol_key,
                question=payload.question,
                agent_keys=plan.agent_keys,
                thinking_model=payload.thinking_model,
                orchestration_model=payload.orchestration_model,
                rounds=payload.rounds,
                no_tools=payload.no_tools,
                tenant_slug=tenant_slug,
                cost_ceiling_usd=te.entitlements.run_cost_ceiling_usd,
            ):
                await event_queue.put(chunk)
        finally:
            await event_queue.put(None)

    asyncio.create_task(_run())

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


@router.post("/run/with-context")
async def router_run_with_context(
    request: Request,
    question: str = Form(...),
    agents: str | None = Form(None),  # JSON-encoded list of agent keys, optional
    max_cost_tier: str = Form("medium"),
    high_threshold: int = Form(80),
    mid_threshold: int = Form(50),
    rounds: int | None = Form(None),
    thinking_model: str = Form(THINKING_MODEL),
    orchestration_model: str = Form(ORCHESTRATION_MODEL),
    no_tools: bool = Form(False),
    files: list[UploadFile] = File(default=[]),
    te: TenantEntitlements = Depends(require_run_admission),
) -> StreamingResponse:
    """Smart-route + uploaded context. Classifies the question via P0a, then
    runs the chosen protocol with the uploaded files as grounding context.

    Same SSE event order as /run: router_decision first, then the protocol
    stream. Classification happens against the question only — files are not
    fed into the router to keep decisions deterministic.
    """
    parsed_agents: list[str] | None = None
    if agents:
        try:
            parsed_agents = json.loads(agents)
        except json.JSONDecodeError:
            raise HTTPException(400, "agents must be a JSON-encoded list of strings")

    # Validate file sizes up front — same contract as protocols /run/with-context.
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
        await f.seek(0)
    if total_size > MAX_TOTAL_SIZE:
        raise HTTPException(
            413,
            f"Total upload size ({total_size // (1024 * 1024)}MB) exceeds 200MB limit",
        )

    tenant_slug = te.tenant_slug
    allowlist = _resolver_allowlist(te)
    orchestrator = AdaptiveRouterOrchestrator(
        resolver=Resolver(allowlist=allowlist, max_cost_tier=max_cost_tier)
        if allowlist is not None
        else Resolver(max_cost_tier=max_cost_tier),
        high_threshold=high_threshold,
        mid_threshold=mid_threshold,
    )

    decision = await orchestrator.decide(
        question,
        requested_agents=parsed_agents,
    )

    if decision.plan is None:
        raise HTTPException(
            status_code=422,
            detail={"error": "no_routable_protocol", "decision": decision.to_dict()},
        )

    plan = decision.plan
    check_protocol_allowed(plan.protocol_key, te)

    # Persist Run row (tenant-scoped).
    with Session(engine) as session:
        run = Run(
            type="protocol",
            protocol_key=plan.protocol_key,
            question=question,
            status="pending",
            tenant_slug=tenant_slug,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    # Ingest uploaded files now that we have a run_id.
    run_context: RunContext | None = None
    if files:
        run_context = await process_uploaded_files(run_id, files)
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.context_mode = run_context.mode
                run.context_files_json = run_context.files_metadata_json()
                session.add(run)
                session.commit()

    event_queue: asyncio.Queue = asyncio.Queue(maxsize=5000)

    # Emit the router decision first so the UI can render a "why this protocol" card.
    await event_queue.put(
        _sse_event("router_decision", {"run_id": run_id, **decision.to_dict()})
    )

    async def _run():
        try:
            async for chunk in run_protocol_stream(
                run_id=run_id,
                protocol_key=plan.protocol_key,
                question=question,
                agent_keys=plan.agent_keys,
                thinking_model=thinking_model,
                orchestration_model=orchestration_model,
                rounds=rounds,
                no_tools=no_tools,
                context=run_context,
                tenant_slug=tenant_slug,
                cost_ceiling_usd=te.entitlements.run_cost_ceiling_usd,
            ):
                await event_queue.put(chunk)
        finally:
            await event_queue.put(None)

    asyncio.create_task(_run())

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


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
