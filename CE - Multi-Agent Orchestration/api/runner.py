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
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from protocols.cost_tracker import ProtocolCostTracker
from protocols.llm import set_cost_tracker, set_event_queue, set_no_tools


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
        queue: asyncio.Queue = asyncio.Queue()
        set_event_queue(queue)
        set_no_tools(no_tools)
        tool_events: list[dict] = []

        t0 = time.time()
        orch_task = asyncio.create_task(orchestrator.run(question))

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

        # Extract outputs from result dataclass
        outputs = _extract_outputs(result, agent_keys)

        for output in outputs:
            yield _sse_event("agent_output", output)

        # Extract synthesis
        synthesis = _extract_synthesis(result)
        if synthesis:
            yield _sse_event("synthesis", {"text": synthesis})

        # Persist outputs
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)
                session.add(run)

                # Group tool events by agent key
                tool_events_by_agent: dict[str, list] = {}
                for te in tool_events:
                    aname = te.get("agent_name", "")
                    tool_events_by_agent.setdefault(aname, []).append({
                        "name": te.get("tool_name", ""),
                        "input_summary": te.get("tool_input", "")[:200] if te.get("event") == "tool_call" else None,
                        "result_preview": te.get("result_preview", "")[:200] if te.get("event") == "tool_result" else None,
                        "elapsed_ms": te.get("elapsed_ms"),
                        "event": te.get("event"),
                    })

                for out in outputs:
                    agent_key = out.get("agent_key", "")
                    agent_name = out.get("agent_name", "")
                    # Match tool events to agent by name
                    matched_tools = tool_events_by_agent.get(agent_name, [])
                    agent_out = AgentOutput(
                        run_id=run_id,
                        agent_key=agent_key,
                        model=thinking_model,
                        output_text=out.get("text", ""),
                        tool_calls_json=json.dumps(matched_tools) if matched_tools else "[]",
                    )
                    session.add(agent_out)

                if synthesis:
                    session.add(AgentOutput(
                        run_id=run_id,
                        agent_key="_synthesis",
                        model=thinking_model,
                        output_text=synthesis,
                    ))
                session.commit()

        cost_summary = cost_tracker.summary()
        yield _sse_event("run_complete", {
            "run_id": run_id,
            "elapsed_seconds": round(elapsed, 1),
            "status": "completed",
            "cost": cost_summary,
        })

        # Clear tracker from context
        set_cost_tracker(None)

    except Exception as e:
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "failed"
                run.completed_at = datetime.now(timezone.utc)
                session.add(run)
                session.commit()

        set_cost_tracker(None)
        yield _sse_event("error", {"message": str(e), "traceback": traceback.format_exc()})
        yield _sse_event("run_complete", {"run_id": run_id, "status": "failed"})


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
            pip_queue: asyncio.Queue = asyncio.Queue()
            set_event_queue(pip_queue)
            set_no_tools(step.get("no_tools", False))

            pip_task = asyncio.create_task(orchestrator.run(step_question))

            while not pip_task.done():
                try:
                    evt = await asyncio.wait_for(pip_queue.get(), timeout=0.1)
                    if evt is None:
                        break
                    yield _sse_event(evt["event"], {**evt, "step": i})
                except asyncio.TimeoutError:
                    continue

            result = await pip_task

            # Drain remaining
            while not pip_queue.empty():
                evt = pip_queue.get_nowait()
                if evt is None:
                    break
                yield _sse_event(evt["event"], {**evt, "step": i})

            outputs = _extract_outputs(result, agent_keys)
            synthesis = _extract_synthesis(result)

            for output in outputs:
                yield _sse_event("agent_output", {**output, "step": i})

            if synthesis:
                yield _sse_event("synthesis", {"text": synthesis, "step": i})

            # Pass output forward
            if step.get("output_passthrough", True):
                prev_output = synthesis or (outputs[-1]["text"] if outputs else "")

            # Update step record
            with Session(engine) as session:
                rs = session.get(RunStep, step_id)
                if rs:
                    rs.status = "completed"
                    rs.completed_at = datetime.now(timezone.utc)
                    session.add(rs)
                    session.commit()

            set_cost_tracker(None)
            yield _sse_event("step_complete", {
                "step": i,
                "protocol_key": protocol_key,
                "cost": step_tracker.summary(),
            })

        # Mark run complete
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)
                session.add(run)
                session.commit()

        yield _sse_event("run_complete", {"run_id": run_id, "status": "completed"})

    except Exception as e:
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "failed"
                run.completed_at = datetime.now(timezone.utc)
                session.add(run)
                session.commit()

        yield _sse_event("error", {"message": str(e), "traceback": traceback.format_exc()})
        yield _sse_event("run_complete", {"run_id": run_id, "status": "failed"})


# ── Result extraction helpers ────────────────────────────────────────────────

def _extract_outputs(result: Any, agent_keys: list[str]) -> list[dict]:
    """Extract per-agent outputs from a protocol result dataclass."""
    outputs = []

    # Common patterns across protocol results:
    # .perspectives (P3 SynthesisResult)
    if hasattr(result, "perspectives"):
        for p in result.perspectives:
            outputs.append({
                "agent_key": _name_to_key(p.name, agent_keys),
                "agent_name": p.name,
                "text": p.response if hasattr(p, "response") else str(p),
            })
        return outputs

    # .rounds (P4 DebateResult — list of Round objects with .responses)
    if hasattr(result, "rounds") and isinstance(result.rounds, list):
        for ri, rnd in enumerate(result.rounds):
            if hasattr(rnd, "responses"):
                for resp in rnd.responses:
                    outputs.append({
                        "agent_key": _name_to_key(resp.name if hasattr(resp, "name") else "", agent_keys),
                        "agent_name": resp.name if hasattr(resp, "name") else f"Agent (round {ri+1})",
                        "text": resp.response if hasattr(resp, "response") else str(resp),
                        "round": ri + 1,
                    })
        return outputs

    # .stages (P6 TRIZ-style — list of stage objects)
    if hasattr(result, "stages"):
        for stage in result.stages:
            stage_name = stage.name if hasattr(stage, "name") else "stage"
            text = stage.output if hasattr(stage, "output") else str(stage)
            outputs.append({
                "agent_key": "_stage",
                "agent_name": stage_name,
                "text": text,
            })
        return outputs

    # .agent_outputs / .responses — generic list of agent responses
    for attr in ("agent_outputs", "responses", "agent_responses"):
        val = getattr(result, attr, None)
        if val and isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    outputs.append({
                        "agent_key": item.get("agent_key", ""),
                        "agent_name": item.get("name", item.get("agent_name", "")),
                        "text": item.get("text", item.get("response", str(item))),
                    })
                elif hasattr(item, "name"):
                    outputs.append({
                        "agent_key": _name_to_key(item.name, agent_keys),
                        "agent_name": item.name,
                        "text": item.response if hasattr(item, "response") else str(item),
                    })
            return outputs

    # Fallback: just serialize the whole result
    outputs.append({
        "agent_key": "_result",
        "agent_name": "Result",
        "text": str(result),
    })
    return outputs


def _extract_synthesis(result: Any) -> str:
    """Extract the synthesis/final output from a protocol result."""
    for attr in ("synthesis", "final_synthesis", "final_output", "recommendation", "summary", "conclusion"):
        val = getattr(result, attr, None)
        if val and isinstance(val, str):
            return val
    return ""


def _name_to_key(name: str, agent_keys: list[str]) -> str:
    """Best-effort match an agent name back to its key."""
    name_lower = name.lower().replace(" ", "-")
    for key in agent_keys:
        if key in name_lower or name_lower in key:
            return key
    return name_lower
