"""Reusable stage executors for blackboard-driven orchestration.

Factory functions producing async callables: (Blackboard, agents, **config) -> None.
Agent stages use agent_complete() from llm.py. Mechanical stages use Anthropic directly.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

import anthropic

from protocols.blackboard import Blackboard
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
        thinking_model = config.get("thinking_model", "claude-opus-4-6")
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
            )
            bb.write(topic_out, response, author=agent["name"], stage=topic_out)

        await asyncio.gather(*(query_agent(a) for a in agents))

    return execute


def sequential_agent_stage(
    topic_in: str,
    topic_out: str,
    prompt_template: str,
) -> Callable:
    """Agents run in order, each reads prior outputs from blackboard."""

    async def execute(bb: Blackboard, agents: list[dict], **config) -> None:
        client = config.get("client")
        thinking_model = config.get("thinking_model", "claude-opus-4-6")
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
        orchestration_model = config.get("orchestration_model", "claude-haiku-4-5-20251001")

        # Gather all entries for topic_in
        entries = bb.read(topic_in)
        if not entries:
            return

        # Format input: combine all entries
        combined = "\n\n".join(
            f"=== {e.author} ===\n{e.content}" for e in entries
        )
        import string
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
        text = response.content[0].text
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
        thinking_model = config.get("thinking_model", "claude-opus-4-6")
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
        import string
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
            thinking={"type": "enabled", "budget_tokens": thinking_budget},
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
