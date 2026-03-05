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
from contextvars import ContextVar
from typing import Any

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy Langfuse initialization
# ---------------------------------------------------------------------------

_langfuse_available = False
_langfuse_client = None

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


def is_enabled() -> bool:
    return _langfuse_available


def get_trace_id() -> str | None:
    """Get the current Langfuse trace ID (for linking to Postgres runs)."""
    return _current_trace_id.get()


# ---------------------------------------------------------------------------
# Protocol-level decorator
# ---------------------------------------------------------------------------

def trace_protocol(protocol_key: str):
    """Decorator for orchestrator ``run()`` methods.

    Creates a top-level Langfuse span (v3 API), sets context vars so that
    ``record_generation()`` calls from ``llm.py`` attach as child spans.
    """
    def decorator(fn):
        if not _langfuse_available:
            return fn

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            root = _langfuse_client.start_span(
                name=protocol_key,
                metadata={"protocol_key": protocol_key},
            )
            trace_id = root.trace_id
            tok_id = _current_trace_id.set(trace_id)
            tok_root = _current_root_span.set(root)
            tok_proto = _current_protocol.set(protocol_key)
            try:
                result = await fn(*args, **kwargs)
                # Stash trace_id on result so callers can retrieve it
                # after the context var is reset
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

def record_generation(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    agent_name: str | None = None,
    latency_ms: float | None = None,
) -> None:
    """Record an LLM call as a Langfuse generation span under the current trace."""
    if not _langfuse_available:
        return
    trace_id = _current_trace_id.get()
    if not trace_id:
        return
    name = f"llm:{agent_name}" if agent_name else f"llm:{model}"
    metadata = {"cached_tokens": cached_tokens}
    if latency_ms:
        metadata["latency_ms"] = latency_ms
    gen = _langfuse_client.start_span(
        name=name,
        trace_context={"trace_id": trace_id},
        metadata=metadata,
    )
    gen.update(
        output=f"model={model} in={input_tokens} out={output_tokens}",
        metadata={**metadata, "model": model, "input_tokens": input_tokens, "output_tokens": output_tokens},
    )
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


def flush() -> None:
    """Flush pending Langfuse events."""
    if _langfuse_available and _langfuse_client:
        _langfuse_client.flush()
