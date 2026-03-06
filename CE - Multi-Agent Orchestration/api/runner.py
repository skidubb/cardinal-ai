"""Protocol execution runner with SSE event emission.

Dynamically imports protocol orchestrators, builds agent dicts from the registry,
runs the protocol, and yields SSE events for each stage of execution.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import re
import time
import traceback
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session

from api.database import engine
from api.models import AgentOutput, Run, RunStep
from protocols.config import ORCHESTRATION_MODEL, THINKING_MODEL
from protocols.cost_tracker import ProtocolCostTracker
from protocols.langfuse_tracing import get_trace_id, is_enabled as langfuse_is_enabled
from protocols.llm import set_cost_tracker, set_event_queue, set_no_tools
from protocols.persistence import PersistOutcome, persist_run
from protocols.run_envelope import StepEnvelope, TelemetryWarning, build_run_envelope


# ── Protocol → orchestrator class mapping ────────────────────────────────────

def _discover_orchestrators() -> dict[str, tuple[str, str]]:
    """Map protocol keys to (module_path, class_name) tuples.

    Scans protocols/p*/orchestrator.py for class definitions.
    Returns e.g. {"p03_parallel_synthesis": ("protocols.p03_parallel_synthesis.orchestrator", "SynthesisOrchestrator")}
    """
    from pathlib import Path
    mapping: dict[str, tuple[str, str]] = {}
    protocols_dir = Path(__file__).resolve().parent.parent / "protocols"
    for orch_file in protocols_dir.glob("p*/orchestrator.py"):
        protocol_key = orch_file.parent.name
        text = orch_file.read_text()
        match = re.search(r"class (\w+Orchestrator)", text)
        if match:
            module = f"protocols.{protocol_key}.orchestrator"
            mapping[protocol_key] = (module, match.group(1))
    return mapping


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


# ── Agent resolution ─────────────────────────────────────────────────────────

def _resolve_agents(agent_keys: list[str]) -> list[dict]:
    """Build full agent dicts from DB (rich) or registry (thin)."""
    from sqlmodel import select as sql_select

    from api.models import Agent as AgentModel
    from protocols.agents import BUILTIN_AGENTS

    agents = []

    with Session(engine) as sess:
        for key in agent_keys:
            db_agent = sess.exec(  # noqa: S102
                sql_select(AgentModel).where(AgentModel.key == key)
            ).first()

            if db_agent and db_agent.system_prompt:
                tools = json.loads(db_agent.tools_json) if db_agent.tools_json != "[]" else []

                assembled_prompt = db_agent.system_prompt

                frameworks = json.loads(db_agent.frameworks_json) if db_agent.frameworks_json != "[]" else []
                if frameworks:
                    assembled_prompt += "\n\n## Analytical Frameworks\n"
                    for fw in frameworks:
                        assembled_prompt += f"\n### {fw['name']}\n{fw['description']}\n**When to use:** {fw['when_to_use']}\n"

                if db_agent.deliverable_template:
                    assembled_prompt += f"\n\n## Deliverable Template\n{db_agent.deliverable_template}"

                if db_agent.communication_style:
                    assembled_prompt += f"\n\n## Communication Style\n{db_agent.communication_style}"

                agent_dict = {
                    "name": db_agent.name,
                    "system_prompt": assembled_prompt,
                    "tools": tools,
                    "max_tokens": db_agent.max_tokens,
                    "temperature": db_agent.temperature,
                }
                if db_agent.model:
                    agent_dict["model"] = db_agent.model

                agents.append(agent_dict)
            elif key in BUILTIN_AGENTS:
                a = BUILTIN_AGENTS[key]
                agents.append({
                    "name": a["name"],
                    "system_prompt": a["system_prompt"],
                })
            else:
                agents.append({"name": key, "system_prompt": f"You are {key}."})

    return agents


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
) -> AsyncGenerator[str, None]:
    """Execute a protocol and yield SSE events."""

    yield _sse_event("run_start", {"run_id": run_id, "protocol_key": protocol_key})

    # Update run status
    with Session(engine) as session:
        run = session.get(Run, run_id)
        if run:
            run.status = "running"
            session.add(run)
            session.commit()

    started_at = datetime.now(timezone.utc)

    try:
        OrchestratorClass = _load_orchestrator_class(protocol_key)
        agents = _resolve_agents(agent_keys)

        yield _sse_event("agent_roster", {
            "agents": [{"key": k, "name": a["name"]} for k, a in zip(agent_keys, agents)]
        })

        # Build orchestrator kwargs
        kwargs: dict[str, Any] = {
            "agents": agents,
            "thinking_model": thinking_model,
            "orchestration_model": orchestration_model,
        }
        if rounds is not None:
            kwargs["rounds"] = rounds

        orchestrator = OrchestratorClass(**kwargs)

        yield _sse_event("stage", {"message": "Running protocol..."})

        # Set up cost tracker for this run
        cost_tracker = ProtocolCostTracker()
        set_cost_tracker(cost_tracker)

        # Set up event queue for live tool visibility
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        set_event_queue(queue)
        set_no_tools(no_tools)
        tool_events: list[dict] = []

        t0 = time.time()
        orch_task = asyncio.create_task(orchestrator.run(question))
        orch_task.add_done_callback(lambda t: t.exception() if not t.cancelled() and t.exception() else None)

        # Drain queue live, yielding SSE events as tools fire
        while not orch_task.done():
            try:
                evt = await asyncio.wait_for(queue.get(), timeout=0.1)
                if evt is None:
                    break
                tool_events.append(evt)
                yield _sse_event(evt["event"], evt)
            except asyncio.TimeoutError:
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

        # Persist outputs
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)
                run.cost_usd = cost_tracker.total_cost
                if envelope.telemetry_degraded:
                    warning_json = json.dumps([w.as_dict() for w in envelope.warnings])[:4000]
                    run.error_message = warning_json
                session.add(run)

                for out in envelope.agent_outputs:
                    session.add(
                        AgentOutput(
                            run_id=run_id,
                            agent_key=out.agent_key,
                            model=out.model or thinking_model,
                            output_text=out.text,
                            tool_calls_json=json.dumps(out.tool_calls) if out.tool_calls else "[]",
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

        if persist_outcome.telemetry_degraded:
            for warning in persist_outcome.warnings:
                envelope.add_warning(warning)
            with Session(engine) as session:
                run = session.get(Run, run_id)
                if run and run.status == "completed":
                    run.error_message = json.dumps([w.as_dict() for w in envelope.warnings])[:4000]
                    session.add(run)
                    session.commit()

        yield _sse_event("run_complete", {
            "run_id": run_id,
            "elapsed_seconds": round(elapsed, 1),
            "status": "completed",
            "cost": cost_summary,
            "telemetry_degraded": envelope.telemetry_degraded,
            "warnings": [w.as_dict() for w in envelope.warnings],
        })

        # Clear tracker from context
        set_cost_tracker(None)

    except Exception as e:
        tb_str = traceback.format_exc()
        run_warnings: list[dict[str, Any]] = []
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "failed"
                run.completed_at = datetime.now(timezone.utc)
                run.error_message = tb_str[:4000]  # truncate to avoid oversized rows
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

        set_cost_tracker(None)
        yield _sse_event("error", {"message": str(e), "traceback": tb_str})
        yield _sse_event(
            "run_complete",
            {
                "run_id": run_id,
                "status": "failed",
                "telemetry_degraded": len(run_warnings) > 0,
                "warnings": run_warnings,
            },
        )


# ── Pipeline run ─────────────────────────────────────────────────────────────

async def run_pipeline_stream(
    run_id: int,
    steps: list[dict],
    question: str,
    agent_keys: list[str],
) -> AsyncGenerator[str, None]:
    """Execute a pipeline (sequence of protocols) and yield SSE events."""

    yield _sse_event("run_start", {"run_id": run_id, "type": "pipeline", "step_count": len(steps)})

    with Session(engine) as session:
        run = session.get(Run, run_id)
        if run:
            run.status = "running"
            session.add(run)
            session.commit()

    prev_output = ""
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
            step_question = step["question_template"]
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
            agents = _resolve_agents(agent_keys)

            kwargs: dict[str, Any] = {
                "agents": agents,
                "thinking_model": step.get("thinking_model", THINKING_MODEL),
                "orchestration_model": step.get("orchestration_model", ORCHESTRATION_MODEL),
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
            pip_task.add_done_callback(lambda t: t.exception() if not t.cancelled() and t.exception() else None)

            while not pip_task.done():
                try:
                    evt = await asyncio.wait_for(pip_queue.get(), timeout=0.1)
                    if evt is None:
                        break
                    step_tool_events.append(evt)
                    yield _sse_event(evt["event"], {**evt, "step": i})
                except asyncio.TimeoutError:
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
                yield _sse_event("synthesis", {"text": step_env.result_summary, "step": i})

            # Pass output forward
            if step.get("output_passthrough", True):
                prev_output = step_env.result_summary or (step_env.agent_outputs[-1].text if step_env.agent_outputs else "")

            # Update step record
            with Session(engine) as session:
                rs = session.get(RunStep, step_id)
                if rs:
                    rs.status = "completed"
                    rs.completed_at = datetime.now(timezone.utc)
                    rs.cost_usd = step_tracker.total_cost
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
            yield _sse_event("step_complete", {
                "step": i,
                "protocol_key": protocol_key,
                "cost": step_cost_summary,
            })

        # Mark run complete
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
            )
            if persist_outcome.telemetry_degraded:
                for warning in persist_outcome.warnings:
                    pipeline_envelope.add_warning(warning)
                with Session(engine) as session:
                    run = session.get(Run, run_id)
                    if run:
                        run.error_message = json.dumps([w.as_dict() for w in pipeline_envelope.warnings])[:4000]
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

    except Exception as e:
        tb_str = traceback.format_exc()
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "failed"
                run.completed_at = datetime.now(timezone.utc)
                run.error_message = tb_str[:4000]
                session.add(run)
                session.commit()

        set_cost_tracker(None)
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

        yield _sse_event("error", {"message": str(e), "traceback": tb_str})
        yield _sse_event(
            "run_complete",
            {
                "run_id": run_id,
                "status": "failed",
                "telemetry_degraded": len(run_error_warnings) > 0,
                "warnings": run_error_warnings,
            },
        )
