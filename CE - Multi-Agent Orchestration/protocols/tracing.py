"""JSONL execution trace for coordination protocols.

Wraps AsyncAnthropic to log every messages.create() call as a JSONL line.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

import anthropic

TRACES_DIR = Path(__file__).resolve().parent.parent / "traces"


class TracingMessages:
    """Proxy for client.messages that logs each create() call to JSONL."""

    def __init__(
        self,
        real_messages: anthropic.resources.AsyncMessages,
        protocol_id: str,
        trace_path: Path,
    ) -> None:
        self._real = real_messages
        self._protocol_id = protocol_id
        self._trace_path = trace_path

    async def create(self, **kwargs):
        """Proxy messages.create(), log timing and token usage."""
        t0 = time.time()
        response = await self._real.create(**kwargs)
        latency = time.time() - t0

        # Extract agent name from system prompt if available
        agent_name = ""
        system = kwargs.get("system", "")
        if isinstance(system, str) and system:
            # Take first ~60 chars as identifier
            agent_name = system[:60].replace("\n", " ")
        elif isinstance(system, list):
            for block in system:
                if isinstance(block, dict) and block.get("text"):
                    agent_name = block["text"][:60].replace("\n", " ")
                    break

        # Extract response text (truncated)
        response_text = ""
        if hasattr(response, "content"):
            for block in response.content:
                if hasattr(block, "text"):
                    response_text = block.text[:500]
                    break

        entry = {
            "timestamp": time.time(),
            "protocol_id": self._protocol_id,
            "model": kwargs.get("model", ""),
            "agent_name": agent_name,
            "stage_name": "",  # caller can set via kwarg convention
            "input_tokens": getattr(response.usage, "input_tokens", 0),
            "output_tokens": getattr(response.usage, "output_tokens", 0),
            "latency_seconds": round(latency, 3),
            "response_text": response_text,
        }

        self._trace_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._trace_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return response


class TracingAsyncAnthropic:
    """Drop-in wrapper for AsyncAnthropic that traces messages.create() calls."""

    def __init__(self, protocol_id: str, trace_path: Path | None = None) -> None:
        self._real_client = anthropic.AsyncAnthropic()
        self._protocol_id = protocol_id
        run_id = uuid.uuid4().hex[:8]
        ts = time.strftime("%Y%m%d_%H%M%S")
        self._trace_path = trace_path or (
            TRACES_DIR / f"{protocol_id}_{run_id}_{ts}.jsonl"
        )
        self.messages = TracingMessages(
            self._real_client.messages,
            protocol_id,
            self._trace_path,
        )

    @property
    def trace_path(self) -> Path:
        return self._trace_path


class BlackboardTracer:
    """Watcher that logs blackboard writes to the same JSONL trace file."""

    def __init__(self, trace_path: Path) -> None:
        self._trace_path = trace_path

    def on_entry(self, entry) -> None:
        """Registered via bb.on_write(tracer.on_entry)."""
        record = {
            "type": "blackboard_write",
            "timestamp": entry.timestamp,
            "entry_id": entry.entry_id,
            "topic": entry.topic,
            "author": entry.author,
            "stage": entry.stage,
            "version": entry.version,
            "content_preview": str(entry.content)[:500],
            "metadata": entry.metadata,
        }
        self._trace_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._trace_path, "a") as f:
            f.write(json.dumps(record) + "\n")


def make_client(
    protocol_id: str = "",
    trace: bool = False,
    trace_path: Path | None = None,
) -> anthropic.AsyncAnthropic | TracingAsyncAnthropic:
    """Factory: returns tracing wrapper if trace=True or COORD_TRACE=1."""
    if trace or os.environ.get("COORD_TRACE") == "1":
        return TracingAsyncAnthropic(protocol_id=protocol_id, trace_path=trace_path)
    return anthropic.AsyncAnthropic()
