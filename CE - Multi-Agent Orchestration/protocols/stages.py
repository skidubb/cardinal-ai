"""Reusable stage executors for blackboard-driven orchestration.

Factory functions producing async callables: (Blackboard, agents, **config) -> None.
Agent stages use agent_complete() from llm.py. Mechanical stages use Anthropic directly.
"""

from __future__ import annotations

import asyncio
import logging
import string
from typing import Any, Callable

logger = logging.getLogger(__name__)


from protocols.blackboard import Blackboard, BlackboardEntry
from protocols.config import THINKING_MODEL, ORCHESTRATION_MODEL
from protocols.llm import agent_complete, extract_text


def parallel_agent_stage(
    topic_in: str,
    topic_out: str,
    prompt_template: str,
    use_thinking: bool = True,
) -> Callable:
    """All agents answer independently, each writes to blackboard."""

    async def execute(bb: Blackboard, agents: list[dict], **config) -> None:
        client = config.get("client")
        thinking_model = config.get("thinking_model", THINKING_MODEL)
        thinking_budget = config.get("thinking_budget", 10_000)

        # Build prompt from blackboard input
        input_entry = bb.read_latest(topic_in)
        input_content = input_entry.content if input_entry else ""
        prompt = prompt_template.format(question=input_content, input=input_content)

        async def query_agent(agent: dict) -> None:
            response = await agent_complete(
                agent=agent,
                fallback_model=thinking_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=thinking_budget if use_thinking else 1000,
                anthropic_client=client,
                no_tools=config.get("no_tools", False),
            )
            bb.write(topic_out, response, author=agent["name"], stage=topic_out)

        results = await asyncio.gather(*(query_agent(a) for a in agents), return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.warning("Agent failed in %s: %s", topic_out, r)

    return execute


def sequential_agent_stage(
    topic_in: str,
    topic_out: str,
    prompt_template: str,
) -> Callable:
    """Agents run in order, each reads prior outputs from blackboard."""

    async def execute(bb: Blackboard, agents: list[dict], **config) -> None:
        client = config.get("client")
        thinking_model = config.get("thinking_model", THINKING_MODEL)
        thinking_budget = config.get("thinking_budget", 10_000)

        input_entry = bb.read_latest(topic_in)
        input_content = input_entry.content if input_entry else ""

        for agent in agents:
            prior = bb.read(topic_out, reader=agent)
            prior_text = "\n\n".join(
                f"[{e.author}]: {e.content}" for e in prior
            )
            prompt = prompt_template.format(
                question=input_content,
                input=input_content,
                prior_responses=prior_text,
            )
            response = await agent_complete(
                agent=agent,
                fallback_model=thinking_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=thinking_budget,
                anthropic_client=client,
                no_tools=config.get("no_tools", False),
            )
            bb.write(topic_out, response, author=agent["name"], stage=topic_out)

    return execute


def mechanical_stage(
    topic_in: str,
    topic_out: str,
    prompt_template: str,
    parse_fn: Callable[[str], Any] | None = None,
) -> Callable:
    """Single orchestration_model call, no agent identity."""

    async def execute(bb: Blackboard, agents: list[dict], **config) -> None:
        client = config.get("client")
        orchestration_model = config.get("orchestration_model", ORCHESTRATION_MODEL)

        # Gather all entries for topic_in
        entries = bb.read(topic_in)
        if not entries:
            return

        # Format input: combine all entries
        combined = "\n\n".join(
            f"=== {e.author} ===\n{e.content}" for e in entries
        )
        keys_needed = {
            fname for _, fname, _, _ in string.Formatter().parse(prompt_template)
            if fname is not None
        }
        fmt = {key: combined for key in keys_needed}
        fmt["input"] = combined
        prompt = prompt_template.format(**fmt)

        response = await client.messages.create(
            model=orchestration_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        text = extract_text(response)
        content = parse_fn(text) if parse_fn else text

        bb.write(
            topic_out,
            content,
            author="system",
            stage=topic_out,
            metadata={
                "token_usage": {
                    "input_tokens": getattr(response.usage, "input_tokens", 0),
                    "output_tokens": getattr(response.usage, "output_tokens", 0),
                }
            },
        )

    return execute


def synthesis_stage(
    topics_in: list[str],
    topic_out: str,
    prompt_template: str,
) -> Callable:
    """Reads multiple topics, produces final output."""

    async def execute(bb: Blackboard, agents: list[dict], **config) -> None:
        client = config.get("client")
        thinking_model = config.get("thinking_model", THINKING_MODEL)
        thinking_budget = config.get("thinking_budget", 10_000)

        # Gather content from all input topics
        sections = {}
        for topic in topics_in:
            entries = bb.read(topic)
            sections[topic] = "\n\n".join(
                f"[{e.author}]: {e.content}" if e.author != "system" else str(e.content)
                for e in entries
            )

        # Build prompt — pass question and all gathered sections
        question_entry = bb.read_latest("question")
        question = question_entry.content if question_entry else ""

        # Discover which format keys the template expects
        keys_needed = {
            fname for _, fname, _, _ in string.Formatter().parse(prompt_template)
            if fname is not None
        }

        # Build format kwargs: topic sections + standard keys
        fmt = {t: sections.get(t, "") for t in topics_in}
        fmt["question"] = question
        fmt["input"] = question
        # Map any remaining unresolved keys to the best available section
        all_content = "\n\n".join(sections.values())
        for key in keys_needed:
            if key not in fmt:
                fmt[key] = sections.get(key, all_content)
        prompt = prompt_template.format(**fmt)

        response = await client.messages.create(
            model=thinking_model,
            max_tokens=thinking_budget + 4096,
            thinking={"type": "adaptive", "budget_tokens": thinking_budget},
            messages=[{"role": "user", "content": prompt}],
        )
        text = extract_text(response)

        bb.write(
            topic_out,
            text,
            author="system",
            stage=topic_out,
            metadata={
                "token_usage": {
                    "input_tokens": getattr(response.usage, "input_tokens", 0),
                    "output_tokens": getattr(response.usage, "output_tokens", 0),
                }
            },
        )

    return execute


def multi_round_stage(
    topic_base: str,
    prompt_template: str,
    max_rounds: int = 3,
    convergence_fn: Callable[[Blackboard, int], bool] | None = None,
) -> Callable:
    """N rounds of parallel agent queries; each round reads prior round context."""

    async def execute(bb: Blackboard, agents: list[dict], **config) -> None:
        client = config.get("client")
        thinking_model = config.get("thinking_model", THINKING_MODEL)
        thinking_budget = config.get("thinking_budget", 10_000)

        question_entry = bb.read_latest("question")
        question = question_entry.content if question_entry else ""

        for round_num in range(1, max_rounds + 1):
            # Check convergence before starting new round (skip round 1)
            if round_num > 1 and convergence_fn and convergence_fn(bb, round_num):
                break

            # Gather prior round context
            prior_entries = bb.read(f"{topic_base}_round_{round_num - 1}") if round_num > 1 else []
            prior_text = "\n\n".join(
                f"[{e.author}]: {e.content}" for e in prior_entries
            )
            topic_out = f"{topic_base}_round_{round_num}"

            async def query_agent(agent: dict, prior: str = prior_text) -> None:
                import string
                keys_needed = {
                    fname for _, fname, _, _ in string.Formatter().parse(prompt_template)
                    if fname is not None
                }
                fmt: dict[str, Any] = {
                    "question": question, "input": question,
                    "prior_arguments": prior, "prior_responses": prior,
                    "round_number": round_num,
                }
                for key in keys_needed:
                    if key not in fmt:
                        fmt[key] = prior or question
                prompt = prompt_template.format(**fmt)

                response = await agent_complete(
                    agent=agent,
                    fallback_model=thinking_model,
                    messages=[{"role": "user", "content": prompt}],
                    thinking_budget=thinking_budget,
                    anthropic_client=client,
                    no_tools=config.get("no_tools", False),
                )
                bb.write(topic_out, response, author=agent["name"], stage=topic_out)

            results = await asyncio.gather(*(query_agent(a) for a in agents), return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    logger.warning("Agent failed in %s round %d: %s", topic_base, round_num, r)

        # Write sentinel so downstream triggers don't depend on max_rounds
        bb.write(f"{topic_base}_complete", "done", author="system", stage=f"{topic_base}_complete")

    return execute


def scoped_parallel_stage(
    topic_in: str,
    topic_out: str,
    prompt_template: str,
    scope_fn: Callable[[dict, list[BlackboardEntry]], list[BlackboardEntry]] | None = None,
) -> Callable:
    """Parallel stage where each agent gets filtered input via scope_fn(agent, entries)."""

    async def execute(bb: Blackboard, agents: list[dict], **config) -> None:
        client = config.get("client")
        thinking_model = config.get("thinking_model", THINKING_MODEL)
        thinking_budget = config.get("thinking_budget", 10_000)

        entries = bb.read(topic_in)
        question_entry = bb.read_latest("question")
        question = question_entry.content if question_entry else ""

        async def query_agent(agent: dict) -> None:
            scoped_entries = scope_fn(agent, entries) if scope_fn else entries
            scoped_text = "\n\n".join(
                f"[{e.author}]: {e.content}" for e in scoped_entries
            )
            import string
            keys_needed = {
                fname for _, fname, _, _ in string.Formatter().parse(prompt_template)
                if fname is not None
            }
            fmt: dict[str, Any] = {
                "question": question, "input": scoped_text,
                "scoped_input": scoped_text,
            }
            for key in keys_needed:
                if key not in fmt:
                    fmt[key] = scoped_text or question
            prompt = prompt_template.format(**fmt)

            response = await agent_complete(
                agent=agent,
                fallback_model=thinking_model,
                messages=[{"role": "user", "content": prompt}],
                thinking_budget=thinking_budget,
                anthropic_client=client,
                no_tools=config.get("no_tools", False),
            )
            bb.write(topic_out, response, author=agent["name"], stage=topic_out)

        results = await asyncio.gather(*(query_agent(a) for a in agents), return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.warning("Agent failed in %s: %s", topic_out, r)

    return execute


def compute_stage(
    topic_in: str,
    topic_out: str,
    compute_fn: Callable[[list[BlackboardEntry]], Any],
) -> Callable:
    """Pure Python computation stage — no LLM call. compute_fn receives entries, returns content."""

    async def execute(bb: Blackboard, agents: list[dict], **config) -> None:
        entries = bb.read(topic_in)
        if not entries:
            return
        result = compute_fn(entries)
        bb.write(topic_out, result, author="system", stage=topic_out)

    return execute
