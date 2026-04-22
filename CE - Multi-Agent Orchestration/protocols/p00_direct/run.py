"""CLI entry point for P00: Direct LLM Response.

Usage:
    python -m protocols.p00_direct.run -q "What year did WWII end?"
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from protocols.langfuse_tracing import get_trace_id

from .orchestrator import DirectOrchestrator
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL


def print_result(result):
    print("\n" + "=" * 70)
    print("DIRECT LLM RESPONSE")
    print("=" * 70)
    print(f"\nQuestion: {result.question}\n")
    print("-" * 40)
    print("RESPONSE")
    print("-" * 40)
    print(result.response)


def main():
    parser = argparse.ArgumentParser(description="P00: Direct LLM Response")
    parser.add_argument("--question", "-q", required=True, help="The question to answer")
    parser.add_argument("--thinking-model", default=THINKING_MODEL, help="Unused; accepted for signature consistency")
    parser.add_argument("--orchestration-model", default=ORCHESTRATION_MODEL, help="Model for the direct completion (default: Haiku)")
    parser.add_argument("--thinking-budget", type=int, default=10000, help="Unused; accepted for signature consistency")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output result as JSON")
    parser.add_argument("--mode", choices=["research", "production"], default="production", help="Unused; accepted for interface consistency")
    args = parser.parse_args()

    orchestrator = DirectOrchestrator(
        thinking_model=args.thinking_model,
        orchestration_model=args.orchestration_model,
        thinking_budget=args.thinking_budget,
    )

    started_at = datetime.now(timezone.utc)
    result = asyncio.run(orchestrator.run(args.question))

    if args.json_output:
        print(json.dumps({"question": result.question, "response": result.response}, indent=2))
    else:
        print_result(result)

    # Persist to Postgres (no-op if unavailable)
    try:
        from protocols.persistence import persist_run
        asyncio.run(persist_run(
            protocol_key="p00_direct",
            question=args.question,
            agent_keys=[],
            result=result,
            trace_id=getattr(result, '_langfuse_trace_id', None) or get_trace_id(),
            source="cli",
            started_at=started_at,
        ))
    except Exception:
        pass  # persistence is best-effort for CLI


if __name__ == "__main__":
    main()
