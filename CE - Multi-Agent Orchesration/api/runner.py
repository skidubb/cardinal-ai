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
    thinking_model: str = "claude-opus-4-6",
    orchestration_model: str = "claude-haiku-4-5-20251001",
    rounds: int | None = None,
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

        t0 = time.time()
        result = await orchestrator.run(question)
        elapsed = time.time() - t0

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

                for out in outputs:
                    agent_out = AgentOutput(
                        run_id=run_id,
                        agent_key=out.get("agent_key", ""),
                        model=thinking_model,
                        output_text=out.get("text", ""),
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

        yield _sse_event("run_complete", {
            "run_id": run_id,
            "elapsed_seconds": round(elapsed, 1),
            "status": "completed",
        })

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
                "thinking_model": step.get("thinking_model", "claude-opus-4-6"),
                "orchestration_model": step.get("orchestration_model", "claude-haiku-4-5-20251001"),
            }
            if step.get("rounds"):
                kwargs["rounds"] = step["rounds"]

            orchestrator = OrchestratorClass(**kwargs)
            result = await orchestrator.run(step_question)

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

            yield _sse_event("step_complete", {"step": i, "protocol_key": protocol_key})

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
