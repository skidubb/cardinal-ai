"""
Three-Tier Agent QA Protocol for C-Suite.

Implements autonomous quality assurance that eliminates Scott as the QA bottleneck.
Outputs pass through 1-3 tiers of validation before reaching human review.

Tier 1 (Haiku): Format, completeness, data validation
Tier 2 (Sonnet): Accuracy, methodology, logical consistency
Tier 3 (Opus): Strategic alignment, client readiness, brand safety

Based on COO-Agent-Native-Ops.md Section 4.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import anthropic

from csuite.config import get_settings


class QATier(Enum):
    """QA tier levels."""

    TIER_1 = "tier_1"  # Haiku - structural validation
    TIER_2 = "tier_2"  # Sonnet - strategic review
    TIER_3 = "tier_3"  # Opus - executive review


class QAResult(Enum):
    """QA evaluation result."""

    APPROVED = "approved"
    REVISIONS_NEEDED = "revisions_needed"
    ESCALATED = "escalated"


@dataclass
class QAScore:
    """Tier 2 scoring dimensions."""

    strategic_alignment: int = 0  # 1-10
    analytical_rigor: int = 0  # 1-10
    actionability: int = 0  # 1-10
    client_fit: int = 0  # 1-10

    @property
    def total(self) -> int:
        return (
            self.strategic_alignment
            + self.analytical_rigor
            + self.actionability
            + self.client_fit
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "strategic_alignment": self.strategic_alignment,
            "analytical_rigor": self.analytical_rigor,
            "actionability": self.actionability,
            "client_fit": self.client_fit,
            "total": self.total,
        }


@dataclass
class QAEvaluation:
    """Result of a QA tier evaluation."""

    tier: QATier
    result: QAResult
    timestamp: datetime = field(default_factory=datetime.now)
    issues: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    feedback: str = ""
    score: QAScore | None = None  # Tier 2 only
    risks: list[str] = field(default_factory=list)  # Tier 3 only
    token_usage: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier.value,
            "result": self.result.value,
            "timestamp": self.timestamp.isoformat(),
            "issues": self.issues,
            "strengths": self.strengths,
            "feedback": self.feedback,
            "score": self.score.to_dict() if self.score else None,
            "risks": self.risks,
            "token_usage": self.token_usage,
        }


@dataclass
class AgentOutput:
    """An agent output to be evaluated."""

    content: str
    output_type: str  # e.g., "audit_report", "proposal", "analysis"
    agent_role: str  # e.g., "cfo", "cto", "cmo", "coo"
    engagement_context: str = ""  # Brief from engagement
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class QAPipelineResult:
    """Complete result from running the QA pipeline."""

    output: AgentOutput
    evaluations: list[QAEvaluation] = field(default_factory=list)
    final_result: QAResult = QAResult.REVISIONS_NEEDED
    escalation_reason: str = ""
    total_cost: float = 0.0

    @property
    def passed(self) -> bool:
        return self.final_result == QAResult.APPROVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_result": self.final_result.value,
            "escalation_reason": self.escalation_reason,
            "total_cost": self.total_cost,
            "evaluations": [e.to_dict() for e in self.evaluations],
        }


# =============================================================================
# QA Agent Prompts
# =============================================================================

TIER_1_PROMPT = """You are the Tier 1 QA Validator Agent. Your role is structural validation.

Evaluate the agent output for completeness and formatting issues. This is a fast, automated check.

## Evaluation Criteria

Check each item (pass/fail):
1. All expected sections are present for this output type
2. No placeholder text (e.g., "[INSERT X]", "TODO", "TBD", "[PLACEHOLDER]")
3. Content length is reasonable (not too short or excessively long)
4. Formatting is consistent (headings, lists, tables are well-formed)
5. No obvious grammatical errors or incomplete sentences
6. Data/numbers appear to be filled in (not blank or zeros where values expected)
7. Links/references are formatted properly (if applicable)

## Output Type Context

This is a "{output_type}" from the {agent_role} agent.

## Response Format

Return ONLY valid JSON (no markdown, no explanation):
{{
    "pass": true/false,
    "issues": ["list of specific issues found"],
    "recommendation": "Approved - Tier 1" or "Revisions Needed"
}}

If any criteria fail, set pass=false and list all issues clearly."""

TIER_2_PROMPT = """You are the Tier 2 QA Strategist Agent. Your role is strategic quality review.

Evaluate the agent output for strategic alignment and analytical rigor.
This is a substantive review.

## Engagement Context

{engagement_context}

## Scoring Rubric (1-10 for each dimension)

**Strategic Alignment**:
- 1-3: Off-scope, misses key questions from the brief
- 4-6: Partial coverage, weak connection to objectives
- 7-8: Answers brief questions, solid strategic alignment
- 9-10: Exceeds brief with proactive insights

**Analytical Rigor**:
- 1-3: Contains errors, claims without evidence
- 4-6: Basic analysis, needs more depth or support
- 7-8: Sound logic, claims backed by data
- 9-10: Sophisticated analysis, highly defensible

**Actionability**:
- 1-3: Vague, theoretical recommendations
- 4-6: Some actionable steps but unclear priorities
- 7-8: Clear next actions with owners/timelines
- 9-10: Prioritized roadmap with dependencies

**Client Fit**:
- 1-3: Generic content, wrong tone for audience
- 4-6: Somewhat tailored but misses nuances
- 7-8: Good fit for client context and sophistication
- 9-10: Highly personalized, demonstrates deep understanding

## Decision Thresholds

- Total 28+: Approved - Tier 2
- Total 20-27: Revisions Needed (provide detailed feedback)
- Total <20: Escalated to Scott (explain why)

## Response Format

Return ONLY valid JSON:
{{
    "scores": {{
        "strategic_alignment": X,
        "analytical_rigor": X,
        "actionability": X,
        "client_fit": X
    }},
    "total_score": XX,
    "strengths": ["list of strong points"],
    "weaknesses": ["list of areas needing improvement"],
    "feedback": "Detailed feedback for the original agent if revisions needed",
    "recommendation": "Approved - Tier 2" or "Revisions Needed" or "Escalated to Scott"
}}"""

TIER_3_PROMPT = """You are the Tier 3 Executive QA Agent.
Your role is final quality assurance before client delivery.

Review this output as if you were the CEO reviewing it before it goes to the client.
This is a client-facing deliverable.

## Engagement Context

{engagement_context}

## Evaluation Criteria

**Brand Alignment**: Does this reflect Cardinal Element's positioning
as a high-quality, strategic consultancy?

**Risk Assessment**: Identify any reputational risks:
- Overcommitting to outcomes we can't guarantee
- Incorrect industry facts or data
- Tone that doesn't match client expectations
- Scope creep beyond the engagement boundaries
- Promises that could create liability

**Polish**: Is the writing professional, clear, and error-free?

**Strategic Narrative**: Does it tell a coherent story from problem to solution?

**Defensibility**: Could we defend every recommendation in a client Q&A?

## Response Format

Return ONLY valid JSON:
{{
    "pass": true/false,
    "reputational_risks": ["list any risks identified"],
    "polish_issues": ["list any writing/formatting issues"],
    "strengths": ["what's working well"],
    "feedback": "Specific feedback if revisions needed",
    "recommendation": "Approved - Ready for Scott" or "Revisions Needed" or "Escalated to Scott"
}}

If risks are flagged, explain why this needs manual review."""


# =============================================================================
# QA Agent Classes
# =============================================================================


class BaseQAAgent:
    """Base class for QA agents."""

    TIER: QATier
    MODEL: str
    COST_PER_1M_INPUT: float
    COST_PER_1M_OUTPUT: float

    def __init__(self):
        self.settings = get_settings()
        self.client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for this evaluation."""
        input_cost = (input_tokens / 1_000_000) * self.COST_PER_1M_INPUT
        output_cost = (output_tokens / 1_000_000) * self.COST_PER_1M_OUTPUT
        return input_cost + output_cost

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """Parse JSON from response, handling potential formatting issues."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

    async def evaluate(self, output: AgentOutput) -> QAEvaluation:
        """Evaluate an agent output. Subclasses implement specific logic."""
        raise NotImplementedError


class Tier1QAAgent(BaseQAAgent):
    """Tier 1: Automated structural validation using Haiku."""

    TIER = QATier.TIER_1
    MODEL = "claude-haiku-4-5-20251001"
    COST_PER_1M_INPUT = 0.80
    COST_PER_1M_OUTPUT = 4.00

    async def evaluate(self, output: AgentOutput) -> QAEvaluation:
        """Run Tier 1 structural validation."""
        prompt = TIER_1_PROMPT.format(
            output_type=output.output_type,
            agent_role=output.agent_role.upper(),
        )

        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=1024,
            temperature=0.1,
            system=prompt,
            messages=[{"role": "user", "content": output.content}],
        )

        result_text = response.content[0].text
        token_usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        try:
            data = self._parse_json_response(result_text)
        except json.JSONDecodeError:
            return QAEvaluation(
                tier=self.TIER,
                result=QAResult.ESCALATED,
                issues=["Failed to parse Tier 1 response"],
                feedback=result_text,
                token_usage=token_usage,
            )

        passed = data.get("pass", False)
        issues = data.get("issues", [])

        if passed:
            result = QAResult.APPROVED
        else:
            result = QAResult.REVISIONS_NEEDED

        return QAEvaluation(
            tier=self.TIER,
            result=result,
            issues=issues,
            feedback=data.get("recommendation", ""),
            token_usage=token_usage,
        )


class Tier2QAAgent(BaseQAAgent):
    """Tier 2: Strategic review using Sonnet."""

    TIER = QATier.TIER_2
    MODEL = "claude-sonnet-4-5-20250929"
    COST_PER_1M_INPUT = 3.00
    COST_PER_1M_OUTPUT = 15.00

    async def evaluate(self, output: AgentOutput) -> QAEvaluation:
        """Run Tier 2 strategic review."""
        engagement_context = output.engagement_context or "No specific engagement context provided."

        prompt = TIER_2_PROMPT.format(engagement_context=engagement_context)

        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=2048,
            temperature=0.2,
            system=prompt,
            messages=[{"role": "user", "content": output.content}],
        )

        result_text = response.content[0].text
        token_usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        try:
            data = self._parse_json_response(result_text)
        except json.JSONDecodeError:
            return QAEvaluation(
                tier=self.TIER,
                result=QAResult.ESCALATED,
                issues=["Failed to parse Tier 2 response"],
                feedback=result_text,
                token_usage=token_usage,
            )

        scores_data = data.get("scores", {})
        score = QAScore(
            strategic_alignment=scores_data.get("strategic_alignment", 0),
            analytical_rigor=scores_data.get("analytical_rigor", 0),
            actionability=scores_data.get("actionability", 0),
            client_fit=scores_data.get("client_fit", 0),
        )

        total = score.total
        recommendation = data.get("recommendation", "")

        if total >= 28 or "Approved" in recommendation:
            result = QAResult.APPROVED
        elif total < 20 or "Escalated" in recommendation:
            result = QAResult.ESCALATED
        else:
            result = QAResult.REVISIONS_NEEDED

        return QAEvaluation(
            tier=self.TIER,
            result=result,
            score=score,
            strengths=data.get("strengths", []),
            issues=data.get("weaknesses", []),
            feedback=data.get("feedback", ""),
            token_usage=token_usage,
        )


class Tier3QAAgent(BaseQAAgent):
    """Tier 3: Executive review using Opus."""

    TIER = QATier.TIER_3
    MODEL = "claude-opus-4-6"
    COST_PER_1M_INPUT = 5.00
    COST_PER_1M_OUTPUT = 25.00

    async def evaluate(self, output: AgentOutput) -> QAEvaluation:
        """Run Tier 3 executive review."""
        engagement_context = output.engagement_context or "No specific engagement context provided."

        prompt = TIER_3_PROMPT.format(engagement_context=engagement_context)

        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=2048,
            temperature=0.3,
            system=prompt,
            messages=[{"role": "user", "content": output.content}],
        )

        result_text = response.content[0].text
        token_usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        try:
            data = self._parse_json_response(result_text)
        except json.JSONDecodeError:
            return QAEvaluation(
                tier=self.TIER,
                result=QAResult.ESCALATED,
                issues=["Failed to parse Tier 3 response"],
                feedback=result_text,
                token_usage=token_usage,
            )

        passed = data.get("pass", False)
        risks = data.get("reputational_risks", [])
        recommendation = data.get("recommendation", "")

        if passed and not risks:
            result = QAResult.APPROVED
        elif "Escalated" in recommendation or risks:
            result = QAResult.ESCALATED
        else:
            result = QAResult.REVISIONS_NEEDED

        return QAEvaluation(
            tier=self.TIER,
            result=result,
            risks=risks,
            strengths=data.get("strengths", []),
            issues=data.get("polish_issues", []),
            feedback=data.get("feedback", ""),
            token_usage=token_usage,
        )


# =============================================================================
# QA Pipeline
# =============================================================================


# Output types that require Tier 3 review (client-facing)
CLIENT_FACING_OUTPUT_TYPES = {
    "audit_report",
    "proposal",
    "playbook",
    "implementation_plan",
    "deliverable",
    "presentation",
    "executive_summary",
}


class QAPipeline:
    """Orchestrates the 3-tier QA process."""

    def __init__(self):
        self.tier1 = Tier1QAAgent()
        self.tier2 = Tier2QAAgent()
        self.tier3 = Tier3QAAgent()

    def _requires_tier3(self, output: AgentOutput) -> bool:
        """Determine if output requires Tier 3 review."""
        return output.output_type.lower() in CLIENT_FACING_OUTPUT_TYPES

    def _calculate_total_cost(self, evaluations: list[QAEvaluation]) -> float:
        """Calculate total cost across all evaluations."""
        total = 0.0
        for eval in evaluations:
            if eval.tier == QATier.TIER_1:
                agent = self.tier1
            elif eval.tier == QATier.TIER_2:
                agent = self.tier2
            else:
                agent = self.tier3

            total += agent._calculate_cost(
                eval.token_usage.get("input_tokens", 0),
                eval.token_usage.get("output_tokens", 0),
            )
        return round(total, 4)

    async def run(self, output: AgentOutput) -> QAPipelineResult:
        """Run the full QA pipeline on an agent output.

        Flow:
        1. Tier 1 (Haiku): Structural validation
           - Pass: Proceed to Tier 2
           - Fail: Return for revisions

        2. Tier 2 (Sonnet): Strategic review
           - Score 28+: Proceed to Tier 3 (if client-facing) or approve
           - Score 20-27: Return for revisions
           - Score <20: Escalate to Scott

        3. Tier 3 (Opus): Executive review (client-facing only)
           - Pass: Approved, ready for Scott's final review
           - Risks: Escalate to Scott
           - Issues: Return for revisions
        """
        result = QAPipelineResult(output=output)

        # Tier 1: Structural validation
        tier1_eval = await self.tier1.evaluate(output)
        result.evaluations.append(tier1_eval)

        if tier1_eval.result != QAResult.APPROVED:
            result.final_result = tier1_eval.result
            if tier1_eval.result == QAResult.ESCALATED:
                result.escalation_reason = "Tier 1 validation failed to parse or critical error"
            result.total_cost = self._calculate_total_cost(result.evaluations)
            return result

        # Tier 2: Strategic review
        tier2_eval = await self.tier2.evaluate(output)
        result.evaluations.append(tier2_eval)

        if tier2_eval.result == QAResult.ESCALATED:
            result.final_result = QAResult.ESCALATED
            result.escalation_reason = (
                "Tier 2 score below threshold"
                f" ({tier2_eval.score.total if tier2_eval.score else 'N/A'}/40)"
            )
            result.total_cost = self._calculate_total_cost(result.evaluations)
            return result

        if tier2_eval.result == QAResult.REVISIONS_NEEDED:
            result.final_result = QAResult.REVISIONS_NEEDED
            result.total_cost = self._calculate_total_cost(result.evaluations)
            return result

        # Check if Tier 3 is required
        if not self._requires_tier3(output):
            result.final_result = QAResult.APPROVED
            result.total_cost = self._calculate_total_cost(result.evaluations)
            return result

        # Tier 3: Executive review (client-facing only)
        tier3_eval = await self.tier3.evaluate(output)
        result.evaluations.append(tier3_eval)

        if tier3_eval.result == QAResult.ESCALATED:
            result.final_result = QAResult.ESCALATED
            risks = ', '.join(tier3_eval.risks)
            result.escalation_reason = f"Reputational risks identified: {risks}"
        elif tier3_eval.result == QAResult.REVISIONS_NEEDED:
            result.final_result = QAResult.REVISIONS_NEEDED
        else:
            result.final_result = QAResult.APPROVED

        result.total_cost = self._calculate_total_cost(result.evaluations)
        return result

    async def run_tier1_only(self, output: AgentOutput) -> QAEvaluation:
        """Run only Tier 1 validation (for quick checks)."""
        return await self.tier1.evaluate(output)

    async def run_through_tier2(self, output: AgentOutput) -> QAPipelineResult:
        """Run Tier 1 and Tier 2, skip Tier 3."""
        result = QAPipelineResult(output=output)

        tier1_eval = await self.tier1.evaluate(output)
        result.evaluations.append(tier1_eval)

        if tier1_eval.result != QAResult.APPROVED:
            result.final_result = tier1_eval.result
            result.total_cost = self._calculate_total_cost(result.evaluations)
            return result

        tier2_eval = await self.tier2.evaluate(output)
        result.evaluations.append(tier2_eval)
        result.final_result = tier2_eval.result

        if tier2_eval.result == QAResult.ESCALATED:
            result.escalation_reason = (
                f"Tier 2 score: {tier2_eval.score.total if tier2_eval.score else 'N/A'}/40"
            )

        result.total_cost = self._calculate_total_cost(result.evaluations)
        return result


# =============================================================================
# Convenience Functions
# =============================================================================


async def evaluate_output(
    content: str,
    output_type: str,
    agent_role: str,
    engagement_context: str = "",
) -> QAPipelineResult:
    """Convenience function to run QA pipeline on an output.

    Args:
        content: The agent output content to evaluate
        output_type: Type of output (e.g., "audit_report", "analysis")
        agent_role: Role of agent that produced this (e.g., "cfo", "cto")
        engagement_context: Optional context about the engagement

    Returns:
        QAPipelineResult with all evaluations and final result
    """
    output = AgentOutput(
        content=content,
        output_type=output_type,
        agent_role=agent_role,
        engagement_context=engagement_context,
    )
    pipeline = QAPipeline()
    return await pipeline.run(output)


def format_qa_report(result: QAPipelineResult) -> str:
    """Format QA pipeline result as a human-readable report."""
    lines = [
        "# QA Pipeline Report",
        "",
        f"**Final Result**: {result.final_result.value.upper()}",
        f"**Total Cost**: ${result.total_cost:.4f}",
    ]

    if result.escalation_reason:
        lines.extend(["", f"**Escalation Reason**: {result.escalation_reason}"])

    lines.extend(["", "## Tier Evaluations", ""])

    for eval in result.evaluations:
        tier_name = eval.tier.value.replace("_", " ").title()
        lines.append(f"### {tier_name}")
        lines.append(f"- **Result**: {eval.result.value}")

        if eval.score:
            lines.append(f"- **Score**: {eval.score.total}/40")
            lines.append(f"  - Strategic Alignment: {eval.score.strategic_alignment}/10")
            lines.append(f"  - Analytical Rigor: {eval.score.analytical_rigor}/10")
            lines.append(f"  - Actionability: {eval.score.actionability}/10")
            lines.append(f"  - Client Fit: {eval.score.client_fit}/10")

        if eval.strengths:
            lines.append("- **Strengths**:")
            for s in eval.strengths:
                lines.append(f"  - {s}")

        if eval.issues:
            lines.append("- **Issues**:")
            for i in eval.issues:
                lines.append(f"  - {i}")

        if eval.risks:
            lines.append("- **Risks**:")
            for r in eval.risks:
                lines.append(f"  - {r}")

        if eval.feedback:
            lines.append(f"- **Feedback**: {eval.feedback}")

        tokens = eval.token_usage
        if tokens:
            lines.append(
                f"- **Tokens**: {tokens.get('input_tokens', 0)} in"
                f" / {tokens.get('output_tokens', 0)} out"
            )

        lines.append("")

    return "\n".join(lines)
