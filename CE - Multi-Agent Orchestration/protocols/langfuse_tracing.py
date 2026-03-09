"""Langfuse observability integration for protocol runs.

Provides decorators and context management for instrumenting protocol
orchestrators and agent calls with Langfuse spans. Gracefully degrades
to no-ops when Langfuse is not configured (LANGFUSE_SECRET_KEY not set).

Compatible with Langfuse SDK v3 (start_span / start_observation API).

Usage:
    from protocols.langfuse_tracing import trace_protocol, get_trace_id

    class MyOrchestrator:
        @trace_protocol("p06_triz")
        async def run(self, question: str) -> Result:
            ...  # agent_complete() calls auto-traced via llm.py hook
"""

from __future__ import annotations

import functools
import logging
import os
import re
import time
from contextvars import ContextVar
from typing import Any

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy Langfuse initialization
# ---------------------------------------------------------------------------

_langfuse_available = False
_langfuse_client = None

# Load .env so CLI runs pick up LANGFUSE_* keys automatically
try:
    from ce_shared.env import find_and_load_dotenv
    find_and_load_dotenv()
except ImportError:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

try:
    from langfuse import Langfuse

    if os.environ.get("LANGFUSE_SECRET_KEY"):
        host = os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL")
        _langfuse_client = Langfuse(host=host) if host else Langfuse()
        _langfuse_available = True
        _log.info("Langfuse tracing enabled")
    else:
        _log.debug("LANGFUSE_SECRET_KEY not set — Langfuse tracing disabled")
except ImportError:
    _log.debug("langfuse not installed — tracing disabled")

# ---------------------------------------------------------------------------
# Context variables
# ---------------------------------------------------------------------------

_current_trace_id: ContextVar[str | None] = ContextVar("_lf_trace_id", default=None)
_current_root_span: ContextVar[Any] = ContextVar("_lf_root_span", default=None)
_current_protocol: ContextVar[str | None] = ContextVar("_lf_protocol", default=None)
_current_session_id: ContextVar[str | None] = ContextVar("_lf_session_id", default=None)

# Auto-detect user from env or system for CLI runs
_default_user: str | None = (
    os.environ.get("LANGFUSE_USER_ID")
    or os.environ.get("USER")
    or os.environ.get("USERNAME")
)
_current_user_id: ContextVar[str | None] = ContextVar("_lf_user_id", default=_default_user)


# ---------------------------------------------------------------------------
# Protocol category taxonomy
# ---------------------------------------------------------------------------

_CATEGORY_RANGES: list[tuple[range, str]] = [
    (range(0, 3), "meta"),              # P0a-P0c
    (range(3, 6), "baselines"),         # P3-P5
    (range(6, 16), "liberating_structures"),  # P6-P15
    (range(16, 19), "intelligence_analysis"),  # P16-P18
    (range(19, 22), "game_theory"),     # P19-P21
    (range(22, 24), "org_theory"),      # P22-P23
    (range(24, 26), "systems_thinking"),  # P24-P25
    (range(26, 28), "design_thinking"),  # P26-P27
    (range(28, 48), "wave2_research"),  # P28-P47
]


def _category(protocol_key: str) -> str:
    """Derive category tag from protocol key using the taxonomy."""
    m = re.search(r"p(\d+)", protocol_key)
    if not m:
        return "unknown"
    num = int(m.group(1))
    for rng, cat in _CATEGORY_RANGES:
        if num in rng:
            return cat
    return "unknown"


def is_enabled() -> bool:
    return _langfuse_available


def get_trace_id() -> str | None:
    """Get the current Langfuse trace ID (for linking to Postgres runs)."""
    return _current_trace_id.get()


# ---------------------------------------------------------------------------
# Protocol-level decorator
# ---------------------------------------------------------------------------

def set_session_id(session_id: str | None) -> None:
    """Set a session ID for grouping related traces (e.g. pipeline runs)."""
    _current_session_id.set(session_id)


def set_user_id(user_id: str | None) -> None:
    """Set a user ID for attributing traces (e.g. CLI user, API caller)."""
    _current_user_id.set(user_id)


def _create_trace_via_ingestion(
    trace_id: str,
    name: str,
    tags: list[str] | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    input: Any = None,
    metadata: dict | None = None,
) -> None:
    """Create a trace via the ingestion API with all attributes baked in.

    This is the only reliable way to set tags, session_id, and user_id
    on traces in Langfuse SDK v3. OTel-created traces (via start_span)
    cannot be patched with these attributes after the fact.
    """
    try:
        from langfuse.api import TraceBody
        body_kwargs: dict[str, Any] = {"id": trace_id, "name": name}
        if tags:
            body_kwargs["tags"] = tags
        if session_id:
            body_kwargs["session_id"] = session_id
        if user_id:
            body_kwargs["user_id"] = user_id
        if input is not None:
            body_kwargs["input"] = input
        if metadata:
            body_kwargs["metadata"] = metadata
        event = {
            "id": _langfuse_client.create_trace_id(),
            "type": "trace-create",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "body": TraceBody(**body_kwargs),
        }
        if _langfuse_client._resources is not None:
            _langfuse_client._resources.add_trace_task(event)
    except Exception as e:
        _log.debug("Failed to create trace via ingestion: %s", e)


def trace_protocol(protocol_key: str):
    """Decorator for orchestrator ``run()`` methods.

    Creates a Langfuse trace via ingestion API (with tags, session, user),
    then attaches a root span for timing. Sets context vars so that
    ``record_generation()`` calls from ``llm.py`` attach as child spans.
    """
    def decorator(fn):
        if not _langfuse_available:
            return fn

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            tags = [
                f"category:{_category(protocol_key)}",
                f"env:{os.getenv('ENV', 'dev')}",
                f"mode:{os.getenv('AGENT_MODE', 'production')}",
            ]
            trace_id = _langfuse_client.create_trace_id()
            session_id = _current_session_id.get()
            user_id = _current_user_id.get()

            # Create trace via ingestion FIRST — this is the only way
            # to reliably set tags, session_id, and user_id in SDK v3.
            _create_trace_via_ingestion(
                trace_id=trace_id,
                name=protocol_key,
                tags=tags,
                session_id=session_id,
                user_id=user_id,
                metadata={"protocol_key": protocol_key},
            )

            # Attach root span for timing and output capture
            root = _langfuse_client.start_span(
                trace_context={"trace_id": trace_id},
                name=protocol_key,
                metadata={"protocol_key": protocol_key},
            )

            tok_id = _current_trace_id.set(trace_id)
            tok_root = _current_root_span.set(root)
            tok_proto = _current_protocol.set(protocol_key)
            try:
                result = await fn(*args, **kwargs)
                try:
                    result._langfuse_trace_id = trace_id
                except (AttributeError, TypeError):
                    pass
                root.update(
                    output=str(result)[:2000],
                    metadata={"protocol_key": protocol_key, "status": "completed"},
                )

                # Run multi-agent evals (non-blocking, best-effort)
                if not os.getenv("SKIP_MULTIAGENT_EVALS"):
                    try:
                        orchestrator = args[0] if args else None
                        agent_keys = []
                        if orchestrator and hasattr(orchestrator, "agents"):
                            agents = orchestrator.agents
                            if isinstance(agents, list):
                                agent_keys = [
                                    a.get("name", "") if isinstance(a, dict)
                                    else getattr(a, "name", "")
                                    for a in agents
                                ]
                        from protocols.multiagent_evals import evaluate_multiagent
                        await evaluate_multiagent(result, agent_keys, trace_id)
                    except Exception as eval_err:
                        _log.debug("Multi-agent eval skipped: %s", eval_err)

                return result
            except Exception as e:
                root.update(
                    level="ERROR",
                    status_message=str(e)[:500],
                    metadata={"protocol_key": protocol_key, "status": "failed"},
                )
                raise
            finally:
                root.end()
                _current_trace_id.reset(tok_id)
                _current_root_span.reset(tok_root)
                _current_protocol.reset(tok_proto)
                _langfuse_client.flush()

        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Generation recording (called from llm.py after each LLM call)
# ---------------------------------------------------------------------------

_MECHANICAL_AGENT_NAMES = frozenset({
    "dedup", "ranking", "synthesis", "verdict", "loop_decision",
    "final_synthesis", "classification", "extraction", "scoring",
    "consensus", "merge", "judge",
})


def _is_mechanical(agent_name: str | None) -> bool:
    """Return True if this is a mechanical/orchestration step, not an agent call."""
    if not agent_name:
        return True  # unnamed calls are mechanical
    return agent_name.lower() in _MECHANICAL_AGENT_NAMES


def _extract_user_question(messages: list[dict] | str | None) -> str | None:
    """Extract the user's actual question from a messages array.

    For agent calls, Langfuse evals work best with a clean question string
    rather than the full messages array with system prompts and JSON instructions.
    """
    if isinstance(messages, str):
        return messages[:5_000] if len(messages) > 5_000 else messages
    if not isinstance(messages, list):
        return None
    # Find the last user message
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content[:5_000] if len(content) > 5_000 else content
    return None


def record_generation(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    agent_name: str | None = None,
    latency_ms: float | None = None,
    cost_usd: float | None = None,
    input_content: list[dict] | str | None = None,
    output_content: str | None = None,
    token_source: str | None = None,
) -> None:
    """Record an LLM call as a Langfuse generation under the current trace.

    Includes actual input/output content so Langfuse's built-in LLM-as-Judge
    evaluators can score the generation. Content is truncated to avoid
    excessive data volume.

    Tags each generation with ``generation_type: agent`` or
    ``generation_type: mechanical`` in metadata so Langfuse evaluators
    can target only agent responses (where scoring is meaningful).

    When ``token_source`` is provided (e.g., ``"estimated_from_cost"`` or
    ``"sdk_response"``), it is included in the span metadata for provenance.
    """
    if not _langfuse_available:
        return
    trace_id = _current_trace_id.get()
    if not trace_id:
        return

    mechanical = _is_mechanical(agent_name)
    name = f"llm:{agent_name}" if agent_name else f"llm:{model}"
    metadata: dict[str, Any] = {
        "cached_tokens": cached_tokens,
        "generation_type": "mechanical" if mechanical else "agent",
    }
    if token_source:
        metadata["token_source"] = token_source
    if latency_ms:
        metadata["latency_ms"] = latency_ms

    usage_details: dict[str, Any] = {
        "input": input_tokens,
        "output": output_tokens,
    }
    if cached_tokens:
        usage_details["input_cached"] = cached_tokens

    cost_details: dict[str, float] | None = None
    if cost_usd is not None:
        cost_details = {"total": cost_usd}

    # For agent calls: extract clean user question for Langfuse evals.
    # For mechanical calls: send full messages so debugging is possible.
    if not mechanical:
        gen_input = _extract_user_question(input_content)
    else:
        gen_input = input_content
        if isinstance(gen_input, str) and len(gen_input) > 10_000:
            gen_input = gen_input[:10_000] + "...[truncated]"
        elif isinstance(gen_input, list):
            truncated = []
            for msg in gen_input:
                if isinstance(msg, dict) and isinstance(msg.get("content"), str) and len(msg["content"]) > 5_000:
                    truncated.append({**msg, "content": msg["content"][:5_000] + "...[truncated]"})
                else:
                    truncated.append(msg)
            gen_input = truncated

    gen_output = output_content
    if gen_output and len(gen_output) > 10_000:
        gen_output = gen_output[:10_000] + "...[truncated]"

    try:
        gen = _langfuse_client.start_observation(
            as_type="generation",
            name=name,
            trace_context={"trace_id": trace_id},
            input=gen_input,
            model=model,
            usage_details=usage_details,
            cost_details=cost_details,
            metadata=metadata,
        )
        gen.update(output=gen_output or f"model={model} in={input_tokens} out={output_tokens}")
        gen.end()
    except Exception as e:
        _log.debug("start_observation(generation) failed, falling back to span: %s", e)
        gen = _langfuse_client.start_span(
            name=name,
            trace_context={"trace_id": trace_id},
            metadata={**metadata, "model": model, "input_tokens": input_tokens, "output_tokens": output_tokens},
        )
        gen.update(output=gen_output or f"model={model} in={input_tokens} out={output_tokens}")
        gen.end()


# ---------------------------------------------------------------------------
# Manual span helpers (for stages, not individual LLM calls)
# ---------------------------------------------------------------------------

def create_span(name: str, metadata: dict | None = None) -> Any:
    """Create a child span under the current trace. Returns span or None."""
    if not _langfuse_available:
        return None
    trace_id = _current_trace_id.get()
    if not trace_id:
        return None
    return _langfuse_client.start_span(
        name=name,
        trace_context={"trace_id": trace_id},
        metadata=metadata or {},
    )


def end_span(span: Any, output: str | None = None, error: str | None = None) -> None:
    """End a span with optional output or error."""
    if span is None:
        return
    kwargs: dict = {}
    if output:
        kwargs["output"] = output[:2000]
    if error:
        kwargs["level"] = "ERROR"
        kwargs["status_message"] = error[:500]
    if kwargs:
        span.update(**kwargs)
    span.end()


def score_trace(
    name: str,
    value: float,
    comment: str | None = None,
    trace_id: str | None = None,
) -> None:
    """Attach a numeric score to the current (or specified) trace.

    Use for judge verdicts, eval scores, or any quality metric.
    Scores appear in the Langfuse dashboard for filtering and trends.
    """
    if not _langfuse_available or not _langfuse_client:
        return
    tid = trace_id or _current_trace_id.get()
    if not tid:
        return
    try:
        _langfuse_client.create_score(
            trace_id=tid,
            name=name,
            value=value,
            comment=comment,
        )
    except Exception as e:
        _log.warning("Failed to record Langfuse score %s: %s", name, e)


def flush() -> None:
    """Flush pending Langfuse events."""
    if _langfuse_available and _langfuse_client:
        _langfuse_client.flush()


# ---------------------------------------------------------------------------
# Dataset helpers (for benchmark evaluation experiments)
# ---------------------------------------------------------------------------

def create_dataset(name: str, description: str | None = None, metadata: dict | None = None) -> Any:
    """Create a Langfuse dataset (idempotent — safe to call repeatedly)."""
    if not _langfuse_available or not _langfuse_client:
        return None
    try:
        kwargs: dict[str, Any] = {"name": name}
        if description:
            kwargs["description"] = description
        if metadata:
            kwargs["metadata"] = metadata
        return _langfuse_client.create_dataset(**kwargs)
    except Exception as e:
        _log.warning("Failed to create Langfuse dataset %s: %s", name, e)
        return None


def create_dataset_item(
    dataset_name: str,
    input: dict,
    metadata: dict | None = None,
    item_id: str | None = None,
) -> Any:
    """Add an item to a Langfuse dataset."""
    if not _langfuse_available or not _langfuse_client:
        return None
    try:
        kwargs: dict[str, Any] = {
            "dataset_name": dataset_name,
            "input": input,
        }
        if metadata:
            kwargs["metadata"] = metadata
        if item_id:
            kwargs["id"] = item_id
        return _langfuse_client.create_dataset_item(**kwargs)
    except Exception as e:
        _log.warning("Failed to create Langfuse dataset item %s: %s", item_id, e)
        return None


def link_trace_to_dataset_item(
    dataset_name: str,
    item_id: str,
    trace_id: str,
    run_name: str,
    run_metadata: dict | None = None,
) -> None:
    """Link a trace to a dataset item for experiment comparison.

    Uses the low-level API (CreateDatasetRunItemRequest) so we can link
    by trace_id without needing the observation object in scope.
    """
    if not _langfuse_available or not _langfuse_client:
        return
    try:
        from langfuse.api import CreateDatasetRunItemRequest

        _langfuse_client.api.dataset_run_items.create(
            request=CreateDatasetRunItemRequest(
                run_name=run_name,
                dataset_item_id=item_id,
                trace_id=trace_id,
                metadata=run_metadata,
            )
        )
        _langfuse_client.flush()
    except Exception as e:
        _log.warning("Failed to link trace %s to dataset item %s: %s", trace_id, item_id, e)
