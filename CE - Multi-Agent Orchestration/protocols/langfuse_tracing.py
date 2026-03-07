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


def trace_protocol(protocol_key: str):
    """Decorator for orchestrator ``run()`` methods.

    Creates a top-level Langfuse span (v3 API), sets context vars so that
    ``record_generation()`` calls from ``llm.py`` attach as child spans.
    Adds tags for category, environment, and agent mode for dashboard filtering.
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
            # start_as_current_span is a sync context manager that sets up
            # Langfuse's internal context. Tags/session are trace-level
            # attributes applied via update_current_trace.
            with _langfuse_client.start_as_current_span(
                name=protocol_key,
                metadata={"protocol_key": protocol_key},
            ) as root:
                trace_id = root.trace_id
                # Apply trace-level attributes (tags, session_id)
                trace_update: dict[str, Any] = {"name": protocol_key, "tags": tags}
                session_id = _current_session_id.get()
                if session_id:
                    trace_update["session_id"] = session_id
                _langfuse_client.update_current_trace(**trace_update)

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
                    return result
                except Exception as e:
                    root.update(
                        level="ERROR",
                        status_message=str(e)[:500],
                        metadata={"protocol_key": protocol_key, "status": "failed"},
                    )
                    raise
                finally:
                    _current_trace_id.reset(tok_id)
                    _current_root_span.reset(tok_root)
                    _current_protocol.reset(tok_proto)
                    _langfuse_client.flush()

        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Generation recording (called from llm.py after each LLM call)
# ---------------------------------------------------------------------------

def record_generation(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    agent_name: str | None = None,
    latency_ms: float | None = None,
    cost_usd: float | None = None,
) -> None:
    """Record an LLM call as a Langfuse generation under the current trace.

    Uses start_generation() instead of start_span() so Langfuse natively
    understands model, tokens, and cost — unlocking token histograms,
    model comparison views, and cache rate dashboards.
    """
    if not _langfuse_available:
        return
    trace_id = _current_trace_id.get()
    if not trace_id:
        return
    name = f"llm:{agent_name}" if agent_name else f"llm:{model}"
    metadata: dict[str, Any] = {"cached_tokens": cached_tokens}
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

    try:
        gen = _langfuse_client.start_observation(
            as_type="generation",
            name=name,
            trace_context={"trace_id": trace_id},
            model=model,
            usage_details=usage_details,
            cost_details=cost_details,
            metadata=metadata,
        )
        gen.update(output=f"model={model} in={input_tokens} out={output_tokens}")
        gen.end()
    except Exception as e:
        _log.debug("start_observation(generation) failed, falling back to span: %s", e)
        gen = _langfuse_client.start_span(
            name=name,
            trace_context={"trace_id": trace_id},
            metadata={**metadata, "model": model, "input_tokens": input_tokens, "output_tokens": output_tokens},
        )
        gen.update(output=f"model={model} in={input_tokens} out={output_tokens}")
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
