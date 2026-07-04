"""Protocol execution runner with SSE event emission.

Dynamically imports protocol orchestrators, builds agent dicts from the registry,
runs the protocol, and yields SSE events for each stage of execution.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import logging
import os
import re
import time
import traceback

_log = logging.getLogger(__name__)
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from api.context_pipeline import RunContext


# ── Active task registry ──────────────────────────────────────────────────────
# Maps run_id -> asyncio.Task for the orchestrator coroutine.
# Used by disconnect watchers to cancel in-flight runs when the client disconnects.

_active_run_tasks: dict[int, asyncio.Task] = {}

from sqlmodel import Session

from api.database import engine
from api.models import AgentOutput, Run, RunStep
from protocols.agent_provider import build_production_agents
from protocols.config import ORCHESTRATION_MODEL, THINKING_MODEL
from protocols.cost_tracker import CostCeilingExceeded, ProtocolCostTracker
from protocols.judge import QualityJudge
from protocols.langfuse_tracing import (
    get_trace_id,
    is_enabled as langfuse_is_enabled,
    score_trace,
    set_session_id,
)
from protocols.llm import set_cost_tracker, set_event_queue, set_no_tools
from protocols.persistence import PersistOutcome, persist_run
from protocols.run_envelope import StepEnvelope, TelemetryWarning, build_run_envelope
from protocols.learning.hooks import pre_run_hook, post_run_hook


# ── Protocol → orchestrator class mapping ────────────────────────────────────


def _discover_orchestrators() -> dict[str, tuple[str, str]]:
    """Map protocol keys to (module_path, class_name) tuples.

    Scans protocols/p*/orchestrator.py for class definitions. Prefers classes
    named ``*Orchestrator``; falls back to the class containing an
    ``async def run`` method (the canonical entrypoint signature).
    """
    from pathlib import Path

    mapping: dict[str, tuple[str, str]] = {}
    protocols_dir = Path(__file__).resolve().parent.parent / "protocols"
    for orch_file in protocols_dir.glob("p*/orchestrator.py"):
        protocol_key = orch_file.parent.name
        class_name = _find_entrypoint_class(orch_file.read_text())
        if class_name:
            module = f"protocols.{protocol_key}.orchestrator"
            mapping[protocol_key] = (module, class_name)
    return mapping


def _find_entrypoint_class(text: str) -> str | None:
    match = re.search(r"^class (\w+Orchestrator)\b", text, re.MULTILINE)
    if match:
        return match.group(1)
    classes = [
        (m.start(), m.group(1))
        for m in re.finditer(r"^class (\w+)\b", text, re.MULTILINE)
    ]
    for run in re.finditer(r"^    async def run\s*\(", text, re.MULTILINE):
        preceding = [name for pos, name in classes if pos < run.start()]
        if preceding:
            return preceding[-1]
    return None


_ORCHESTRATOR_MAP: dict[str, tuple[str, str]] | None = None


def get_orchestrator_map() -> dict[str, tuple[str, str]]:
    global _ORCHESTRATOR_MAP
    if _ORCHESTRATOR_MAP is None:
        _ORCHESTRATOR_MAP = _discover_orchestrators()
    return _ORCHESTRATOR_MAP


def _load_orchestrator_class(protocol_key: str):
    """Dynamically import and return the orchestrator class for a protocol."""
    omap = get_orchestrator_map()
    if protocol_key not in omap:
        raise ValueError(f"Unknown protocol: {protocol_key}")
    module_path, class_name = omap[protocol_key]
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


# ── SSE event helpers ────────────────────────────────────────────────────────


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _merge_cost_summaries(cost_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "total_usd": 0.0,
        "calls": 0,
        "by_model": {},
        "by_agent": {},
    }

    for summary in cost_summaries:
        merged["total_usd"] += float(summary.get("total_usd", 0.0) or 0.0)
        merged["calls"] += int(summary.get("calls", 0) or 0)

        for model, model_stats in summary.get("by_model", {}).items():
            cur = merged["by_model"].setdefault(
                model,
                {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cached_tokens": 0,
                    "cost_usd": 0.0,
                },
            )
            cur["calls"] += int(model_stats.get("calls", 0) or 0)
            cur["input_tokens"] += int(model_stats.get("input_tokens", 0) or 0)
            cur["output_tokens"] += int(model_stats.get("output_tokens", 0) or 0)
            cur["cached_tokens"] += int(model_stats.get("cached_tokens", 0) or 0)
            cur["cost_usd"] += float(model_stats.get("cost_usd", 0.0) or 0.0)

        for agent, agent_stats in summary.get("by_agent", {}).items():
            cur = merged["by_agent"].setdefault(
                agent,
                {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cached_tokens": 0,
                    "cost_usd": 0.0,
                    "primary_model": agent_stats.get("primary_model", ""),
                    "by_model": {},
                },
            )
            cur["calls"] += int(agent_stats.get("calls", 0) or 0)
            cur["input_tokens"] += int(agent_stats.get("input_tokens", 0) or 0)
            cur["output_tokens"] += int(agent_stats.get("output_tokens", 0) or 0)
            cur["cached_tokens"] += int(agent_stats.get("cached_tokens", 0) or 0)
            cur["cost_usd"] += float(agent_stats.get("cost_usd", 0.0) or 0.0)
            if not cur.get("primary_model"):
                cur["primary_model"] = agent_stats.get("primary_model", "")

    merged["total_usd"] = round(merged["total_usd"], 6)
    for stats in merged["by_model"].values():
        stats["cost_usd"] = round(stats["cost_usd"], 6)
    for stats in merged["by_agent"].values():
        stats["cost_usd"] = round(stats["cost_usd"], 6)
    return merged


# ── Single protocol run ─────────────────────────────────────────────────────


async def run_protocol_stream(
    run_id: int,
    protocol_key: str,
    question: str,
    agent_keys: list[str],
    thinking_model: str = THINKING_MODEL,
    orchestration_model: str = ORCHESTRATION_MODEL,
    rounds: int | None = None,
    no_tools: bool = False,
    context: "RunContext | None" = None,
    tenant_slug: str = "cardinal-element",
    cost_ceiling_usd: float | None = None,
) -> AsyncGenerator[str, None]:
    """Execute a protocol and yield SSE events.

    ``tenant_slug`` is propagated to ``persist_run`` so the Postgres run row
    is correctly tenant-scoped. Defaults to ``cardinal-element`` for CLI/local
    callers that don't have an auth context.

    ``cost_ceiling_usd`` is the per-run entitlement cost cap. When set (and
    entitlement enforcement is on), the run hard-stops with a
    ``cost_cap_exceeded`` error once accumulated LLM spend crosses it. When
    None, the tracker falls back to the warn-only ``PROTOCOL_COST_CEILING``.
    """
    from api.context_pipeline import build_effective_question, cleanup_run_context

    yield _sse_event("run_start", {"run_id": run_id, "protocol_key": protocol_key})

    # Update run status
    with Session(engine) as session:
        run = session.get(Run, run_id)
        if run:
            run.status = "running"
            session.add(run)
            session.commit()

    started_at = datetime.now(timezone.utc)
    cost_tracker: ProtocolCostTracker | None = None

    try:
        OrchestratorClass = _load_orchestrator_class(protocol_key)
        agents = build_production_agents(agent_keys, model=thinking_model)

        # M5: Assemble context from the tenant's knowledge graph + inject as
        # institutional_memory. Best-effort -- failures don't block the run.
        try:
            from protocols.context_assembler import assemble_context

            _ce_brief = await assemble_context(tenant_slug, question, agent_keys)
            if _ce_brief:
                for agent in agents:
                    if hasattr(agent, "institutional_memory"):
                        existing = getattr(agent, "institutional_memory", None) or ""
                        agent.institutional_memory = (
                            existing + "\n\n" if existing else ""
                        ) + _ce_brief
        except Exception:
            pass

        # Protocol learning: classify question + retrieve insights + inject memory
        _learning_categories = ["unclassified"]
        try:
            import anthropic as _anth

            _learning_client = _anth.AsyncAnthropic()
            _user_config = {"rounds": rounds}
            _user_config, _learning_categories = await pre_run_hook(
                client=_learning_client,
                protocol_key=protocol_key,
                question=question,
                agents=agents,
                user_config=_user_config,
            )
            if _user_config.get("rounds") and rounds is None:
                rounds = _user_config["rounds"]
        except Exception:
            pass  # Learning hooks are non-blocking

        yield _sse_event(
            "agent_roster",
            {
                "agents": [
                    {"key": k, "name": a["name"]} for k, a in zip(agent_keys, agents)
                ]
            },
        )

        # Build orchestrator kwargs, then filter to what the orchestrator's
        # __init__ actually accepts. Older orchestrators (e.g. P04 Debate) don't
        # take `orchestration_model`; this avoids a TypeError that otherwise
        # crashes the run at construction time with a misleading traceback.
        candidate_kwargs: dict[str, Any] = {
            "agents": agents,
            "thinking_model": thinking_model,
            "orchestration_model": orchestration_model,
        }
        if rounds is not None:
            candidate_kwargs["rounds"] = rounds

        _accepted = inspect.signature(OrchestratorClass.__init__).parameters
        # If __init__ uses **kwargs, pass everything; otherwise drop keys it doesn't name.
        accepts_var_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in _accepted.values()
        )
        kwargs = (
            candidate_kwargs
            if accepts_var_kwargs
            else {k: v for k, v in candidate_kwargs.items() if k in _accepted}
        )
        dropped = set(candidate_kwargs) - set(kwargs)
        if dropped:
            print(
                f"[runner] {protocol_key}: {OrchestratorClass.__name__} does not "
                f"accept {sorted(dropped)}; passing "
                f"{sorted(kwargs)} instead.",
                flush=True,
            )

        orchestrator = OrchestratorClass(**kwargs)

        yield _sse_event("stage", {"message": "Running protocol..."})

        # Inject uploaded context into the question
        effective_question = question
        if context is not None:
            yield _sse_event(
                "context_processing",
                {
                    "message": f"Processing {len(context.files)} context file(s)...",
                    "mode": context.mode,
                    "files": [f.metadata_dict() for f in context.files],
                },
            )
            effective_question = await build_effective_question(question, context)

        # Set up cost tracker for this run. A per-tier entitlement ceiling
        # hard-stops the run; without one, warn-only env ceiling applies.
        from api.entitlements import _enforce as _entitlements_enforce

        cost_tracker = ProtocolCostTracker(
            cost_ceiling_usd=cost_ceiling_usd,
            hard_stop=cost_ceiling_usd is not None and _entitlements_enforce(),
        )
        set_cost_tracker(cost_tracker)

        # Set up event queue for live tool visibility
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        set_event_queue(queue)
        set_no_tools(no_tools)
        tool_events: list[dict] = []

        t0 = time.time()
        orch_task = asyncio.create_task(orchestrator.run(effective_question))
        _active_run_tasks[run_id] = orch_task

        def _cleanup_task(t: asyncio.Task) -> None:
            _active_run_tasks.pop(run_id, None)
            if not t.cancelled() and t.exception():
                pass  # exceptions surfaced via await orch_task below

        orch_task.add_done_callback(_cleanup_task)

        # Drain queue live, yielding SSE events as they fire
        last_heartbeat = time.time()
        while not orch_task.done():
            try:
                evt = await asyncio.wait_for(queue.get(), timeout=0.1)
                if evt is None:
                    break
                tool_events.append(evt)
                yield _sse_event(evt["event"], evt)
                last_heartbeat = time.time()
            except asyncio.TimeoutError:
                # SSE heartbeat every 5s to keep connection alive
                now = time.time()
                if now - last_heartbeat >= 5.0:
                    yield f": heartbeat {int(now - t0)}s\n\n"
                    last_heartbeat = now
                continue

        result = await orch_task
        elapsed = time.time() - t0

        # Drain any remaining queued events
        while not queue.empty():
            evt = queue.get_nowait()
            if evt is None:
                break
            tool_events.append(evt)
            yield _sse_event(evt["event"], evt)

        cost_summary = cost_tracker.summary()
        # Record cost as a Langfuse score for unified cost+quality dashboards
        if cost_tracker.total_cost > 0:
            score_trace("cost_usd", cost_tracker.total_cost, trace_id=get_trace_id())
        run_warnings: list[TelemetryWarning | dict[str, Any]] = []
        if not langfuse_is_enabled():
            run_warnings.append(
                TelemetryWarning(
                    code="langfuse_disabled",
                    message="Langfuse tracing is disabled for this run.",
                    component="langfuse",
                    recoverable=True,
                )
            )

        envelope = build_run_envelope(
            protocol_key=protocol_key,
            question=question,
            agent_keys=agent_keys,
            result=result,
            source="api",
            status="completed",
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            trace_id=get_trace_id(),
            run_id=run_id,
            cost_summary=cost_summary,
            tool_events=tool_events,
            warnings=run_warnings,
        )

        for output in envelope.agent_outputs:
            yield _sse_event("agent_output", output.as_sse_payload())

        if envelope.result_summary:
            yield _sse_event("synthesis", {"text": envelope.result_summary})

        # Quality Judge — score synthesis against agent outputs
        _judge_overall: float | None = None
        judge_verdict_dict: dict[str, Any] | None = None
        if envelope.result_summary and envelope.agent_outputs:
            try:
                from protocols.tracing import make_client as _make_judge_client

                judge_client = _make_judge_client(protocol_id="judge")
                judge = QualityJudge(judge_client)
                agent_outputs_text = "\n\n".join(
                    f"=== {o.agent_key} ===\n{o.text}" for o in envelope.agent_outputs
                )
                verdict = await judge.evaluate(
                    question=question,
                    agent_outputs=agent_outputs_text,
                    synthesis=envelope.result_summary,
                )
                judge_verdict_dict = verdict.as_dict()
                _judge_overall = float(verdict.overall)
                yield _sse_event("judge_verdict", judge_verdict_dict)
                # Attach scores to Langfuse trace for dashboard filtering/trends
                trace_id = envelope.trace_id
                for dim in ("completeness", "consistency", "actionability", "overall"):
                    score_trace(
                        f"judge_{dim}", float(getattr(verdict, dim)), trace_id=trace_id
                    )
                score_trace(
                    "judge_recommendation",
                    1.0 if verdict.recommendation == "accept" else 0.0,
                    comment="; ".join(verdict.flags) if verdict.flags else None,
                    trace_id=trace_id,
                )
            except Exception as judge_err:
                _judge_warning = {
                    "code": "judge_failed",
                    "message": f"Quality judge failed: {judge_err}",
                    "component": "judge",
                    "recoverable": True,
                }
                run_warnings.append(TelemetryWarning(**_judge_warning))

        # Article — narrative readout of the completed run. Best-effort: a
        # failure here logs a warning and never fails the run.
        article_dict: dict[str, Any] | None = None
        if envelope.result_summary and os.getenv("ARTICLE_ENABLED", "true").lower() in (
            "1",
            "true",
            "yes",
        ):
            try:
                from protocols.article import ArticleWriter
                from protocols.tracing import make_client as _make_article_client

                writer = ArticleWriter(
                    _make_article_client(protocol_id="article_writer")
                )
                article = await writer.write(
                    question=question,
                    synthesis=envelope.result_summary,
                    protocol_key=protocol_key,
                    agent_outputs=[
                        {"name": o.agent_key, "text": o.text}
                        for o in envelope.agent_outputs
                    ],
                    judge_verdict=judge_verdict_dict,
                )
                if not article.is_empty:
                    article_dict = article.as_dict()
                    yield _sse_event("article", article_dict)
            except Exception as article_err:
                run_warnings.append(
                    TelemetryWarning(
                        code="article_failed",
                        message=f"Article writer failed: {article_err}",
                        component="article_writer",
                        recoverable=True,
                    )
                )

        # Persist outputs
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)
                run.cost_usd = cost_tracker.total_cost
                run.trace_id = envelope.trace_id
                if judge_verdict_dict:
                    run.judge_verdict_json = json.dumps(judge_verdict_dict)
                if envelope.telemetry_degraded:
                    warning_json = json.dumps([w.as_dict() for w in envelope.warnings])[
                        :4000
                    ]
                    run.error_message = warning_json
                session.add(run)

                for out in envelope.agent_outputs:
                    session.add(
                        AgentOutput(
                            run_id=run_id,
                            agent_key=out.agent_key,
                            model=out.model or thinking_model,
                            output_text=out.text,
                            tool_calls_json=json.dumps(out.tool_calls)
                            if out.tool_calls
                            else "[]",
                            input_tokens=out.input_tokens,
                            output_tokens=out.output_tokens,
                            cost_usd=out.cost_usd,
                            started_at=out.started_at,
                            completed_at=out.completed_at,
                        )
                    )

                if envelope.result_summary:
                    session.add(
                        AgentOutput(
                            run_id=run_id,
                            agent_key="_synthesis",
                            model=thinking_model,
                            output_text=envelope.result_summary,
                        )
                    )
                if article_dict:
                    session.add(
                        AgentOutput(
                            run_id=run_id,
                            agent_key="_article",
                            model=thinking_model,
                            output_text=json.dumps(article_dict),
                        )
                    )
                session.commit()

        # Persist to Postgres (alongside SQLite) with explicit outcome reporting.
        persist_outcome = PersistOutcome()
        try:
            persist_outcome = await persist_run(
                protocol_key=protocol_key,
                question=question,
                agent_keys=agent_keys,
                result=result,
                source="api",
                started_at=started_at,
                envelope=envelope,
                tenant_slug=tenant_slug,
                also_write_legacy=False,  # API already wrote the legacy Run row upfront (status=pending) and updated it post-run.
            )
        except Exception as pg_err:
            persist_outcome.warnings.append(
                {
                    "code": "postgres_persist_exception",
                    "message": f"Postgres persist raised exception: {pg_err}",
                    "component": "postgres_persistence",
                    "recoverable": True,
                }
            )

        # M5: Write a Decision node to the tenant's knowledge graph. This is
        # what closes the compounding loop -- future runs query these decisions
        # via context_assembler. Best-effort; never blocks the run.
        try:
            from protocols.graph_writer import write_decision

            try:
                envelope.run_id = run_id  # type: ignore[attr-defined]
            except Exception:
                pass
            await write_decision(
                tenant_slug=tenant_slug, envelope=envelope, run_id_source=str(run_id)
            )
        except Exception as graph_err:
            _log.warning(
                "graph_writer.invoke_failed run_id=%s tenant=%s err=%s",
                run_id,
                tenant_slug,
                graph_err,
            )

        if persist_outcome.telemetry_degraded:
            for warning in persist_outcome.warnings:
                envelope.add_warning(warning)
            fatal_warnings = [w for w in envelope.warnings if not w.recoverable]
            if fatal_warnings:
                with Session(engine) as session:
                    run = session.get(Run, run_id)
                    if run and run.status == "completed":
                        run.error_message = json.dumps(
                            [w.as_dict() for w in fatal_warnings]
                        )[:4000]
                        session.add(run)
                        session.commit()

        # Protocol learning: record run outcome
        try:
            await post_run_hook(
                run_id=persist_outcome.run_id
                if persist_outcome and persist_outcome.run_id
                else str(run_id),
                protocol_key=protocol_key,
                question=question,
                question_categories=_learning_categories,
                eval_score=_judge_overall,
                config={
                    "rounds": rounds,
                    "agents": agent_keys,
                    "thinking_model": thinking_model,
                },
                synthesis_text=envelope.result_summary or "",
                cost_summary=cost_summary,
            )
        except Exception:
            pass  # Learning hooks are non-blocking

        run_complete_payload: dict[str, Any] = {
            "run_id": run_id,
            "elapsed_seconds": round(elapsed, 1),
            "status": "completed",
            "cost": cost_summary,
            "trace_id": envelope.trace_id,
            "telemetry_degraded": envelope.telemetry_degraded,
            "warnings": [w.as_dict() for w in envelope.warnings],
        }
        if judge_verdict_dict:
            run_complete_payload["judge_verdict"] = judge_verdict_dict
        yield _sse_event("run_complete", run_complete_payload)

    except asyncio.CancelledError:
        _active_run_tasks.pop(run_id, None)
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "cancelled"
                run.completed_at = datetime.now(timezone.utc)
                session.add(run)
                session.commit()
        yield _sse_event("run_complete", {"run_id": run_id, "status": "cancelled"})
        raise  # Re-raise CancelledError so asyncio task machinery handles it properly

    except Exception as e:
        tb_str = traceback.format_exc()
        run_warnings: list[dict[str, Any]] = []
        _active_run_tasks.pop(run_id, None)
        cost_capped = isinstance(e, CostCeilingExceeded)
        if cost_capped:
            error_message = json.dumps(
                {
                    "code": "cost_cap_exceeded",
                    "message": str(e),
                    "total_cost_usd": round(e.total_cost, 6),
                    "ceiling_usd": e.ceiling,
                }
            )
        else:
            error_message = tb_str[:4000]  # truncate to avoid oversized rows
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "failed"
                run.completed_at = datetime.now(timezone.utc)
                run.error_message = error_message
                if cost_tracker is not None:
                    run.cost_usd = cost_tracker.total_cost
                session.add(run)
                session.commit()

        try:
            outcome = await persist_run(
                protocol_key=protocol_key,
                question=question,
                agent_keys=agent_keys,
                result={"error": str(e)},
                source="api",
                started_at=started_at,
                error=tb_str,
                tenant_slug=tenant_slug,
                also_write_legacy=False,  # API already updated the legacy Run row to status=failed above.
            )
            run_warnings.extend(outcome.warnings)
        except Exception as pg_err:
            run_warnings.append(
                {
                    "code": "postgres_persist_exception",
                    "message": f"Postgres failure persist raised exception: {pg_err}",
                    "component": "postgres_persistence",
                    "recoverable": True,
                }
            )

        _log.error("Run failed:\n%s", tb_str)
        error_event: dict[str, Any] = {"message": str(e)}
        if cost_capped:
            error_event = {
                "code": "cost_cap_exceeded",
                "message": (
                    "Run stopped: it reached your plan's per-run cost cap. "
                    "Upgrade for a higher cap."
                ),
                "total_cost_usd": round(e.total_cost, 6),
                "ceiling_usd": e.ceiling,
                "upgrade_url": "/billing",
            }
        yield _sse_event("error", error_event)
        yield _sse_event(
            "run_complete",
            {
                "run_id": run_id,
                "status": "failed",
                "telemetry_degraded": len(run_warnings) > 0,
                "warnings": run_warnings,
            },
        )

    finally:
        # Always clean up context vars, regardless of how the generator exits
        set_cost_tracker(None)
        set_event_queue(None)
        # Clean up ephemeral Pinecone namespace for run context
        if context is not None and context.pinecone_namespace:
            await cleanup_run_context(context.pinecone_namespace)


# ── Pipeline run ─────────────────────────────────────────────────────────────


async def run_pipeline_stream(
    run_id: int,
    steps: list[dict],
    question: str,
    agent_keys: list[str],
    start_from_step: int = 0,
    initial_prev_output: str = "",
) -> AsyncGenerator[str, None]:
    """Execute a pipeline (sequence of protocols) and yield SSE events.

    Supports resume: pass start_from_step and initial_prev_output to skip
    already-completed steps and continue from the last checkpoint.
    """

    yield _sse_event(
        "run_start",
        {
            "run_id": run_id,
            "type": "pipeline",
            "step_count": len(steps),
            "resuming_from": start_from_step,
        },
    )

    # Set session_id so all protocol traces in this pipeline are grouped
    pipeline_session_id = f"pipeline-{run_id}"
    set_session_id(pipeline_session_id)

    with Session(engine) as session:
        run = session.get(Run, run_id)
        if run:
            run.status = "running"
            session.add(run)
            session.commit()

    prev_output = initial_prev_output
    pipeline_total_cost = 0.0
    pipeline_started_at = datetime.now(timezone.utc)
    step_envelopes: list[StepEnvelope] = []
    step_cost_summaries: list[dict[str, Any]] = []
    run_warnings: list[TelemetryWarning | dict[str, Any]] = []
    if not langfuse_is_enabled():
        run_warnings.append(
            TelemetryWarning(
                code="langfuse_disabled",
                message="Langfuse tracing is disabled for this pipeline run.",
                component="langfuse",
                recoverable=True,
            )
        )

    try:
        for i, step in enumerate(steps):
            if i < start_from_step:
                continue  # Skip already-completed steps (resume)
            step_question = step["question_template"]
            step_question = step_question.replace("{question}", question)
            if "{prev_output}" in step_question and prev_output:
                step_question = step_question.replace("{prev_output}", prev_output)

            protocol_key = step["protocol_key"]
            yield _sse_event("step_start", {"step": i, "protocol_key": protocol_key})

            # Create run step record
            with Session(engine) as session:
                run_step = RunStep(
                    run_id=run_id,
                    step_order=i,
                    protocol_key=protocol_key,
                    status="running",
                    started_at=datetime.now(timezone.utc),
                )
                session.add(run_step)
                session.commit()
                step_id = run_step.id

            OrchestratorClass = _load_orchestrator_class(protocol_key)
            step_thinking_model = step.get("thinking_model", THINKING_MODEL)
            agents = build_production_agents(agent_keys, model=step_thinking_model)

            kwargs: dict[str, Any] = {
                "agents": agents,
                "thinking_model": step_thinking_model,
                "orchestration_model": step.get(
                    "orchestration_model", ORCHESTRATION_MODEL
                ),
            }
            if step.get("rounds"):
                kwargs["rounds"] = step["rounds"]

            orchestrator = OrchestratorClass(**kwargs)

            # Set up cost tracker, event queue and tool controls for this step
            step_tracker = ProtocolCostTracker()
            set_cost_tracker(step_tracker)
            pip_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
            set_event_queue(pip_queue)
            set_no_tools(step.get("no_tools", False))

            step_started_at = datetime.now(timezone.utc)
            step_tool_events: list[dict[str, Any]] = []
            pip_task = asyncio.create_task(orchestrator.run(step_question))
            _active_run_tasks[run_id] = pip_task
            pip_task.add_done_callback(
                lambda t: t.exception() if not t.cancelled() and t.exception() else None
            )

            pip_t0 = time.time()
            pip_last_heartbeat = time.time()
            while not pip_task.done():
                try:
                    evt = await asyncio.wait_for(pip_queue.get(), timeout=0.1)
                    if evt is None:
                        break
                    step_tool_events.append(evt)
                    yield _sse_event(evt["event"], {**evt, "step": i})
                    pip_last_heartbeat = time.time()
                except asyncio.TimeoutError:
                    now = time.time()
                    if now - pip_last_heartbeat >= 5.0:
                        yield f": heartbeat {int(now - pip_t0)}s\n\n"
                        pip_last_heartbeat = now
                    continue

            result = await pip_task

            # Drain remaining
            while not pip_queue.empty():
                evt = pip_queue.get_nowait()
                if evt is None:
                    break
                step_tool_events.append(evt)
                yield _sse_event(evt["event"], {**evt, "step": i})

            step_cost_summary = step_tracker.summary()
            step_cost_summaries.append(step_cost_summary)
            step_env = build_run_envelope(
                protocol_key=protocol_key,
                question=step_question,
                agent_keys=agent_keys,
                result=result,
                source="api",
                status="completed",
                started_at=step_started_at,
                completed_at=datetime.now(timezone.utc),
                cost_summary=step_cost_summary,
                tool_events=step_tool_events,
            )

            for output in step_env.agent_outputs:
                yield _sse_event("agent_output", {**output.as_sse_payload(), "step": i})

            if step_env.result_summary:
                yield _sse_event(
                    "synthesis", {"text": step_env.result_summary, "step": i}
                )

            # Pass output forward
            if step.get("output_passthrough", True):
                prev_output = step_env.result_summary or (
                    step_env.agent_outputs[-1].text if step_env.agent_outputs else ""
                )

            # Update step record with checkpoint for resume
            with Session(engine) as session:
                rs = session.get(RunStep, step_id)
                if rs:
                    rs.status = "completed"
                    rs.completed_at = datetime.now(timezone.utc)
                    rs.cost_usd = step_tracker.total_cost
                    rs.output_text = prev_output[:50_000] if prev_output else ""
                    session.add(rs)
                    session.commit()

            pipeline_total_cost += step_tracker.total_cost
            step_envelopes.append(
                StepEnvelope(
                    step_order=i,
                    protocol_key=protocol_key,
                    status="completed",
                    question=step_question,
                    synthesis=step_env.result_summary,
                    cost=step_cost_summary,
                    agent_outputs=step_env.agent_outputs,
                    started_at=step_started_at,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            set_cost_tracker(None)
            yield _sse_event(
                "step_complete",
                {
                    "step": i,
                    "protocol_key": protocol_key,
                    "cost": step_cost_summary,
                },
            )

        # Mark run complete and persist agent outputs for report generation
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)
                run.cost_usd = pipeline_total_cost
                if run_warnings:
                    warning_payload = [
                        w.as_dict() if hasattr(w, "as_dict") else w
                        for w in run_warnings
                    ]
                    run.error_message = json.dumps(warning_payload)[:4000]
                session.add(run)

                # Save agent outputs from each step so reports can reconstruct them
                for step_env in step_envelopes:
                    for out in step_env.agent_outputs:
                        session.add(
                            AgentOutput(
                                run_id=run_id,
                                run_step_id=None,
                                agent_key=out.agent_key,
                                model=out.model or "",
                                output_text=out.text,
                                tool_calls_json=json.dumps(out.tool_calls)
                                if out.tool_calls
                                else "[]",
                                input_tokens=out.input_tokens,
                                output_tokens=out.output_tokens,
                                cost_usd=out.cost_usd,
                                started_at=out.started_at,
                                completed_at=out.completed_at,
                            )
                        )

                # Save final synthesis (last step's synthesis or accumulated prev_output)
                if prev_output:
                    session.add(
                        AgentOutput(
                            run_id=run_id,
                            agent_key="_synthesis",
                            model="",
                            output_text=prev_output,
                        )
                    )
                session.commit()

        pipeline_cost_summary = _merge_cost_summaries(step_cost_summaries)
        pipeline_result = {
            "steps": [s.as_dict() for s in step_envelopes],
            "final_output": prev_output,
        }
        pipeline_envelope = build_run_envelope(
            protocol_key="pipeline",
            question=question,
            agent_keys=agent_keys,
            result=pipeline_result,
            source="api",
            status="completed",
            started_at=pipeline_started_at,
            completed_at=datetime.now(timezone.utc),
            run_id=run_id,
            cost_summary=pipeline_cost_summary,
            steps=step_envelopes,
            warnings=run_warnings,
        )
        if not pipeline_envelope.result_summary and prev_output:
            pipeline_envelope.result_summary = prev_output[:2000]

        try:
            persist_outcome = await persist_run(
                protocol_key="pipeline",
                question=question,
                agent_keys=agent_keys,
                result=pipeline_result,
                source="api",
                started_at=pipeline_started_at,
                envelope=pipeline_envelope,
                also_write_legacy=False,  # Pipeline runner already wrote its legacy Run row.
            )
            if persist_outcome.telemetry_degraded:
                for warning in persist_outcome.warnings:
                    pipeline_envelope.add_warning(warning)
                with Session(engine) as session:
                    run = session.get(Run, run_id)
                    if run:
                        run.error_message = json.dumps(
                            [w.as_dict() for w in pipeline_envelope.warnings]
                        )[:4000]
                        session.add(run)
                        session.commit()
        except Exception as pg_err:
            pipeline_envelope.add_warning(
                {
                    "code": "postgres_persist_exception",
                    "message": f"Postgres persist raised exception: {pg_err}",
                    "component": "postgres_persistence",
                    "recoverable": True,
                }
            )

        yield _sse_event(
            "run_complete",
            {
                "run_id": run_id,
                "status": "completed",
                "cost": pipeline_cost_summary,
                "telemetry_degraded": pipeline_envelope.telemetry_degraded,
                "warnings": [w.as_dict() for w in pipeline_envelope.warnings],
            },
        )

    except asyncio.CancelledError:
        _active_run_tasks.pop(run_id, None)
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "cancelled"
                run.completed_at = datetime.now(timezone.utc)
                session.add(run)
                session.commit()
        yield _sse_event("run_complete", {"run_id": run_id, "status": "cancelled"})
        raise  # Re-raise CancelledError so asyncio task machinery handles it properly

    except Exception as e:
        tb_str = traceback.format_exc()
        _active_run_tasks.pop(run_id, None)
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "failed"
                run.completed_at = datetime.now(timezone.utc)
                run.error_message = tb_str[:4000]
                session.add(run)
                session.commit()

        run_error_warnings: list[dict[str, Any]] = []
        try:
            outcome = await persist_run(
                protocol_key="pipeline",
                question=question,
                agent_keys=agent_keys,
                result={"error": str(e)},
                source="api",
                started_at=pipeline_started_at,
                error=tb_str,
                also_write_legacy=False,  # Pipeline runner already updated the legacy Run row to status=failed above.
            )
            run_error_warnings.extend(outcome.warnings)
        except Exception as pg_err:
            run_error_warnings.append(
                {
                    "code": "postgres_persist_exception",
                    "message": f"Postgres failure persist raised exception: {pg_err}",
                    "component": "postgres_persistence",
                    "recoverable": True,
                }
            )

        _log.error("Run failed:\n%s", tb_str)
        yield _sse_event("error", {"message": str(e)})
        yield _sse_event(
            "run_complete",
            {
                "run_id": run_id,
                "status": "failed",
                "telemetry_degraded": len(run_error_warnings) > 0,
                "warnings": run_error_warnings,
            },
        )

    finally:
        # Always clean up context vars and active task tracking
        _active_run_tasks.pop(run_id, None)
        set_cost_tracker(None)
        set_event_queue(None)
        set_session_id(None)
