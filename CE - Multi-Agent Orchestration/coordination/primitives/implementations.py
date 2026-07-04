"""Concrete implementations of the 9 coordination primitives.

Each primitive wraps an LLM call with typed I/O and tracing.
These are used by agents during open conversation and by the
ConversationRuntime for structured coordination.
"""

from __future__ import annotations

import time
from typing import Any

from coordination.primitives.base import (
    Primitive,
    PrimitiveInput,
    PrimitiveOutput,
    PrimitiveTrace,
    PrimitiveType,
)


class _BaseLLMPrimitive(Primitive):
    """Shared logic for primitives backed by LLM calls."""

    primitive_type: PrimitiveType
    _system_prompt: str = ""

    async def execute(
        self,
        input: PrimitiveInput,
        agent_id: str | None = None,
    ) -> tuple[PrimitiveOutput, PrimitiveTrace]:
        trace = PrimitiveTrace(
            primitive_type=self.primitive_type,
            agent_id=agent_id,
            input_summary=input.content[:200],
            started_at=time.time(),
        )

        try:
            from protocols.llm import llm_complete
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic()
            prompt = self._build_prompt(input)
            response = await llm_complete(
                client,
                agent_name=f"primitive_{self.primitive_type.value}",
                model=input.constraints.get("model", "claude-haiku-4-5-20251001"),
                messages=[{"role": "user", "content": prompt}],
                system=self._system_prompt,
                max_tokens=input.constraints.get("max_tokens", 2000),
            )
            output = PrimitiveOutput(
                content=response,
                confidence=0.7,  # Default; specialized primitives override
                metadata={"primitive_type": self.primitive_type.value},
            )
        except Exception as e:
            output = PrimitiveOutput(
                content=f"Primitive {self.primitive_type.value} failed: {e}",
                confidence=0.0,
                metadata={"error": str(e)},
            )

        trace.output_summary = output.content[:200]
        trace.completed_at = time.time()
        trace.latency_ms = (trace.completed_at - trace.started_at) * 1000
        return output, trace

    def _build_prompt(self, input: PrimitiveInput) -> str:
        """Build the LLM prompt. Override for specialized behavior."""
        parts = [input.content]
        if input.context:
            parts.append(f"\n\nContext: {input.context}")
        return "\n".join(parts)


class Decompose(_BaseLLMPrimitive):
    """Break a problem into subproblems."""
    primitive_type = PrimitiveType.DECOMPOSE
    _system_prompt = (
        "You are a problem decomposition specialist. Break the given problem "
        "into 2-5 clear, non-overlapping subproblems. For each subproblem, "
        "state what needs to be resolved and what expertise it requires."
    )


class Propose(_BaseLLMPrimitive):
    """Generate candidate solutions or framings."""
    primitive_type = PrimitiveType.PROPOSE
    _system_prompt = (
        "You are a solution generator. Propose 2-4 distinct candidate "
        "solutions or framings for the given problem. Each candidate should "
        "be substantively different, not just variations of the same approach."
    )


class Challenge(_BaseLLMPrimitive):
    """Adversarial evaluation of proposals."""
    primitive_type = PrimitiveType.CHALLENGE
    _system_prompt = (
        "You are an adversarial evaluator. Identify weaknesses, blind spots, "
        "and failure modes in the given proposal. Be specific about what could "
        "go wrong and under what conditions. Do not soften your critique."
    )


class Retrieve(_BaseLLMPrimitive):
    """Pull relevant context, precedent, and evidence."""
    primitive_type = PrimitiveType.RETRIEVE
    _system_prompt = (
        "You are an evidence retrieval specialist. Identify and surface the "
        "most relevant context, precedents, data points, and evidence for "
        "the given question. Cite specific examples where possible."
    )


class Simulate(_BaseLLMPrimitive):
    """Model outcomes under assumptions."""
    primitive_type = PrimitiveType.SIMULATE
    _system_prompt = (
        "You are a scenario modeler. Given the problem and assumptions, "
        "model 2-3 plausible outcome scenarios. For each, state the key "
        "assumptions, expected outcomes, and probability assessment."
    )


class Score(_BaseLLMPrimitive):
    """Evaluate against explicit criteria."""
    primitive_type = PrimitiveType.SCORE
    _system_prompt = (
        "You are an evaluation specialist. Score the given output against "
        "the stated criteria. Provide a numerical score (0-1) for each "
        "criterion and a brief justification. Be calibrated and consistent."
    )


class Reconcile(_BaseLLMPrimitive):
    """Resolve conflicts between competing outputs."""
    primitive_type = PrimitiveType.RECONCILE
    _system_prompt = (
        "You are a conflict resolution specialist. Given competing outputs "
        "or perspectives, identify the core disagreements, evaluate the "
        "strength of each position, and produce a reconciled view that "
        "preserves the strongest elements of each."
    )


class Escalate(_BaseLLMPrimitive):
    """Flag uncertainty or constraint violations for human review."""
    primitive_type = PrimitiveType.ESCALATE
    _system_prompt = (
        "You are a risk detection specialist. Evaluate the current state "
        "and identify any issues that require human review: low confidence, "
        "constraint violations, ethical concerns, or decisions that exceed "
        "the scope of automated analysis. Be specific about what needs "
        "human judgment and why."
    )


class Compress(_BaseLLMPrimitive):
    """Synthesize outputs into minimal coherent form."""
    primitive_type = PrimitiveType.COMPRESS
    _system_prompt = (
        "You are a synthesis specialist. Compress the given outputs into "
        "the most concise, coherent form possible. Preserve all essential "
        "insights and decisions while eliminating redundancy. The output "
        "should be executive-readable."
    )


# Registry mapping primitive types to their implementations
PRIMITIVE_REGISTRY: dict[PrimitiveType, type[Primitive]] = {
    PrimitiveType.DECOMPOSE: Decompose,
    PrimitiveType.PROPOSE: Propose,
    PrimitiveType.CHALLENGE: Challenge,
    PrimitiveType.RETRIEVE: Retrieve,
    PrimitiveType.SIMULATE: Simulate,
    PrimitiveType.SCORE: Score,
    PrimitiveType.RECONCILE: Reconcile,
    PrimitiveType.ESCALATE: Escalate,
    PrimitiveType.COMPRESS: Compress,
}


def get_primitive(primitive_type: PrimitiveType) -> Primitive:
    """Get a primitive instance by type."""
    cls = PRIMITIVE_REGISTRY[primitive_type]
    return cls()
