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

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session

from api.database import engine
from api.models import Run
from api.runner import run_protocol_stream
from protocols.adaptive_router import (
    AdaptiveRouterOrchestrator,
    Resolver,
)
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/router", tags=["router"])


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
async def router_run(payload: RouterRunRequest, request: Request) -> StreamingResponse:
    """Classify, resolve, then stream the chosen protocol's SSE events.

    Event order:
      1. `router_decision` — the classification + execution plan
      2. Normal protocol SSE stream (run_start, agent_roster, stage events, …)

    If the decision has no plan or tier=='low', yields `router_error` and stops.
    """
    orchestrator = AdaptiveRouterOrchestrator(
        resolver=Resolver(max_cost_tier=payload.max_cost_tier),
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
    with Session(engine) as session:
        run = Run(
            type="protocol",
            protocol_key=plan.protocol_key,
            question=payload.question,
            status="pending",
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
