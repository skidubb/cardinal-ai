"""P22: Sequential Pipeline Orchestrator.

Agent A -> Agent B -> Agent C — each builds on prior output.
"""

import asyncio
import json
from dataclasses import dataclass, field

import anthropic

from .prompts import FINAL_SYNTHESIS_PROMPT, QUALITY_GATE_PROMPT, STAGE_PROMPT


@dataclass
class StageOutput:
    """Output from a single pipeline stage."""

    agent_name: str
    content: str
    stage_number: int


@dataclass
class SequentialPipelineResult:
    """Full result from the sequential pipeline."""

    question: str
    stages: list[StageOutput] = field(default_factory=list)
    quality_passed: bool = False
    final_output: str = ""


def _extract_text(response) -> str:
    """Extract text content from an Anthropic API response."""
    for block in response.content:
        if block.type == "text":
            return block.text.strip()
    return ""


def _format_prior_outputs(stages: list[StageOutput]) -> str:
    """Format prior stage outputs for inclusion in prompts."""
    if not stages:
        return "(No prior outputs — you are the first stage.)"
    parts = []
    for s in stages:
        parts.append(f"### Stage {s.stage_number}: {s.agent_name}\n{s.content}")
    return "\n\n".join(parts)


def _format_all_outputs(stages: list[StageOutput]) -> str:
    """Format all stage outputs for quality gate and synthesis."""
    parts = []
    for s in stages:
        parts.append(f"### Stage {s.stage_number}: {s.agent_name}\n{s.content}")
    return "\n\n".join(parts)


class SequentialPipelineOrchestrator:
    """Orchestrates a sequential pipeline of agents."""

    def __init__(
        self,
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        max_thinking_tokens: int = 10000,
    ):
        self.client = anthropic.AsyncAnthropic()
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.max_thinking_tokens = max_thinking_tokens

    async def _run_stage(
        self,
        agent: dict,
        question: str,
        stage_number: int,
        total_stages: int,
        prior_stages: list[StageOutput],
    ) -> StageOutput:
        """Run a single pipeline stage with extended thinking."""
        prompt = STAGE_PROMPT.format(
            stage_number=stage_number,
            total_stages=total_stages,
            agent_name=agent["name"],
            system_prompt=agent["system_prompt"],
            question=question,
            prior_outputs=_format_prior_outputs(prior_stages),
        )

        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=16000,
            temperature=1,  # required for extended thinking
            thinking={
                "type": "enabled",
                "budget_tokens": self.max_thinking_tokens,
            },
            messages=[{"role": "user", "content": prompt}],
        )

        return StageOutput(
            agent_name=agent["name"],
            content=_extract_text(response),
            stage_number=stage_number,
        )

    async def _quality_gate(
        self, question: str, stages: list[StageOutput]
    ) -> dict:
        """Run quality gate check using orchestration model."""
        prompt = QUALITY_GATE_PROMPT.format(
            question=question,
            total_stages=len(stages),
            all_outputs=_format_all_outputs(stages),
        )

        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        text = _extract_text(response)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            return {"passes": True, "reason": "Quality gate parse error — defaulting to pass", "failing_stage": None}

    async def _synthesize(
        self, question: str, stages: list[StageOutput]
    ) -> str:
        """Produce final synthesis from all stage outputs."""
        prompt = FINAL_SYNTHESIS_PROMPT.format(
            question=question,
            all_outputs=_format_all_outputs(stages),
        )

        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=16000,
            temperature=1,
            thinking={
                "type": "enabled",
                "budget_tokens": self.max_thinking_tokens,
            },
            messages=[{"role": "user", "content": prompt}],
        )

        return _extract_text(response)

    async def run(
        self, question: str, agents: list[dict]
    ) -> SequentialPipelineResult:
        """Run the full sequential pipeline.

        Args:
            question: The strategic question to analyze.
            agents: Ordered list of agent dicts with 'name' and 'system_prompt'.

        Returns:
            SequentialPipelineResult with all stage outputs and final synthesis.
        """
        result = SequentialPipelineResult(question=question)
        total_stages = len(agents)

        # --- Sequential execution ---
        for i, agent in enumerate(agents, 1):
            print(f"  Stage {i}/{total_stages}: {agent['name']}...")
            stage_output = await self._run_stage(
                agent=agent,
                question=question,
                stage_number=i,
                total_stages=total_stages,
                prior_stages=result.stages,
            )
            result.stages.append(stage_output)

        # --- Quality gate ---
        print("  Running quality gate...")
        gate = await self._quality_gate(question, result.stages)
        result.quality_passed = gate.get("passes", True)

        # --- Retry one stage if quality gate fails ---
        if not result.quality_passed:
            failing_stage = gate.get("failing_stage")
            if failing_stage and 1 <= failing_stage <= total_stages:
                print(f"  Quality gate failed — re-running stage {failing_stage} ({agents[failing_stage - 1]['name']})...")
                prior = [s for s in result.stages if s.stage_number < failing_stage]
                new_output = await self._run_stage(
                    agent=agents[failing_stage - 1],
                    question=question,
                    stage_number=failing_stage,
                    total_stages=total_stages,
                    prior_stages=prior,
                )
                result.stages[failing_stage - 1] = new_output

                # Re-run quality gate
                gate = await self._quality_gate(question, result.stages)
                result.quality_passed = gate.get("passes", True)
            else:
                print(f"  Quality gate failed: {gate.get('reason', 'unknown')}")

        # --- Final synthesis ---
        print("  Synthesizing final output...")
        result.final_output = await self._synthesize(question, result.stages)

        return result
