"""ProblemProfile — continuous-dimension problem typing.

Classifies problems by 9 structural dimensions (not surface domains)
to enable learned routing and cross-domain transfer.
"""

from __future__ import annotations

import json
import logging
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GoalClarity(str, Enum):
    CLEAR = "clear"
    AMBIGUOUS = "ambiguous"
    CONTRADICTORY = "contradictory"


class EvidenceQuality(str, Enum):
    RICH = "rich"
    SPARSE = "sparse"
    NOISY = "noisy"
    ADVERSARIAL = "adversarial"


class DownsideSymmetry(str, Enum):
    SYMMETRIC = "symmetric"
    ASYMMETRIC_NEGATIVE = "asymmetric_negative"
    ASYMMETRIC_POSITIVE = "asymmetric_positive"


class TimePressure(str, Enum):
    UNBOUNDED = "unbounded"
    CONSTRAINED = "constrained"
    URGENT = "urgent"


class StakeholderCount(str, Enum):
    SINGLE = "single"
    FEW = "few"
    MANY = "many"
    ADVERSARIAL = "adversarial"


class DomainFamiliarity(str, Enum):
    WELL_KNOWN = "well_known"
    PARTIALLY_KNOWN = "partially_known"
    NOVEL = "novel"


class OutputType(str, Enum):
    DECISION = "decision"
    ANALYSIS = "analysis"
    ARTIFACT = "artifact"
    RECOMMENDATION = "recommendation"
    PLAN = "plan"


class EvaluationClarity(str, Enum):
    OBJECTIVE_METRIC = "objective_metric"
    SUBJECTIVE_JUDGMENT = "subjective_judgment"
    NO_CLEAR_EVAL = "no_clear_eval"


class Decomposability(str, Enum):
    NATURALLY_MODULAR = "naturally_modular"
    ENTANGLED = "entangled"
    SEQUENTIAL = "sequential"


class ProblemProfile(BaseModel):
    """Structural profile of a problem across 9 continuous dimensions.

    Used for routing: similar profiles should use similar coordination strategies.
    """
    goal_clarity: GoalClarity = GoalClarity.AMBIGUOUS
    evidence_quality: EvidenceQuality = EvidenceQuality.SPARSE
    downside_symmetry: DownsideSymmetry = DownsideSymmetry.SYMMETRIC
    time_pressure: TimePressure = TimePressure.UNBOUNDED
    stakeholder_count: StakeholderCount = StakeholderCount.FEW
    domain_familiarity: DomainFamiliarity = DomainFamiliarity.PARTIALLY_KNOWN
    output_type: OutputType = OutputType.RECOMMENDATION
    evaluation_clarity: EvaluationClarity = EvaluationClarity.SUBJECTIVE_JUDGMENT
    decomposability: Decomposability = Decomposability.ENTANGLED

    # Numeric scores (0-1) for continuous similarity matching
    goal_clarity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_quality_score: float = Field(default=0.5, ge=0.0, le=1.0)
    downside_asymmetry_score: float = Field(default=0.5, ge=0.0, le=1.0)
    time_pressure_score: float = Field(default=0.5, ge=0.0, le=1.0)
    stakeholder_complexity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    domain_novelty_score: float = Field(default=0.5, ge=0.0, le=1.0)
    evaluation_clarity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    decomposability_score: float = Field(default=0.5, ge=0.0, le=1.0)

    def to_vector(self) -> list[float]:
        """Convert to a numeric vector for similarity computation."""
        return [
            self.goal_clarity_score,
            self.evidence_quality_score,
            self.downside_asymmetry_score,
            self.time_pressure_score,
            self.stakeholder_complexity_score,
            self.domain_novelty_score,
            self.evaluation_clarity_score,
            self.decomposability_score,
        ]

    def similarity(self, other: ProblemProfile) -> float:
        """Cosine similarity between two problem profiles."""
        v1 = self.to_vector()
        v2 = other.to_vector()
        dot = sum(a * b for a, b in zip(v1, v2))
        mag1 = sum(a * a for a in v1) ** 0.5
        mag2 = sum(b * b for b in v2) ** 0.5
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)


_CLASSIFY_PROMPT = """Analyze this problem and classify it along 9 structural dimensions.

Problem: {question}

For each dimension, provide:
1. The categorical label
2. A numeric score from 0.0 to 1.0

Return ONLY a JSON object with this exact structure:
{{
  "goal_clarity": {{"label": "clear|ambiguous|contradictory", "score": 0.0-1.0}},
  "evidence_quality": {{"label": "rich|sparse|noisy|adversarial", "score": 0.0-1.0}},
  "downside_symmetry": {{"label": "symmetric|asymmetric_negative|asymmetric_positive", "score": 0.0-1.0}},
  "time_pressure": {{"label": "unbounded|constrained|urgent", "score": 0.0-1.0}},
  "stakeholder_count": {{"label": "single|few|many|adversarial", "score": 0.0-1.0}},
  "domain_familiarity": {{"label": "well_known|partially_known|novel", "score": 0.0-1.0}},
  "output_type": {{"label": "decision|analysis|artifact|recommendation|plan", "score": 0.0-1.0}},
  "evaluation_clarity": {{"label": "objective_metric|subjective_judgment|no_clear_eval", "score": 0.0-1.0}},
  "decomposability": {{"label": "naturally_modular|entangled|sequential", "score": 0.0-1.0}}
}}"""


async def classify_problem(
    question: str,
    model: str = "claude-haiku-4-5-20251001",
) -> ProblemProfile:
    """Classify a problem into a ProblemProfile using LLM. ~$0.002/call."""
    try:
        from protocols.llm import llm_complete
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic()
        response = await llm_complete(
            client,
            agent_name="problem_classifier",
            model=model,
            messages=[{"role": "user", "content": _CLASSIFY_PROMPT.format(question=question)}],
            max_tokens=500,
        )
        return _parse_profile(response)
    except Exception as e:
        logger.warning(f"classify_problem failed: {e}")
        return ProblemProfile()  # Safe defaults


def _parse_profile(raw: str) -> ProblemProfile:
    """Parse LLM response into a ProblemProfile."""
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
    try:
        data = json.loads(raw)
        return ProblemProfile(
            goal_clarity=_safe_enum(GoalClarity, data.get("goal_clarity", {}).get("label")),
            evidence_quality=_safe_enum(EvidenceQuality, data.get("evidence_quality", {}).get("label")),
            downside_symmetry=_safe_enum(DownsideSymmetry, data.get("downside_symmetry", {}).get("label")),
            time_pressure=_safe_enum(TimePressure, data.get("time_pressure", {}).get("label")),
            stakeholder_count=_safe_enum(StakeholderCount, data.get("stakeholder_count", {}).get("label")),
            domain_familiarity=_safe_enum(DomainFamiliarity, data.get("domain_familiarity", {}).get("label")),
            output_type=_safe_enum(OutputType, data.get("output_type", {}).get("label")),
            evaluation_clarity=_safe_enum(EvaluationClarity, data.get("evaluation_clarity", {}).get("label")),
            decomposability=_safe_enum(Decomposability, data.get("decomposability", {}).get("label")),
            goal_clarity_score=_safe_score(data.get("goal_clarity", {}).get("score")),
            evidence_quality_score=_safe_score(data.get("evidence_quality", {}).get("score")),
            downside_asymmetry_score=_safe_score(data.get("downside_symmetry", {}).get("score")),
            time_pressure_score=_safe_score(data.get("time_pressure", {}).get("score")),
            stakeholder_complexity_score=_safe_score(data.get("stakeholder_count", {}).get("score")),
            domain_novelty_score=_safe_score(data.get("domain_familiarity", {}).get("score")),
            evaluation_clarity_score=_safe_score(data.get("evaluation_clarity", {}).get("score")),
            decomposability_score=_safe_score(data.get("decomposability", {}).get("score")),
        )
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        logger.warning(f"_parse_profile failed: {e}")
        return ProblemProfile()


def _safe_enum(enum_cls: type, value: Any) -> Any:
    """Safely convert a string to an enum value, with fallback to first member."""
    if value is None:
        return list(enum_cls)[0]
    try:
        return enum_cls(value)
    except ValueError:
        return list(enum_cls)[0]


def _safe_score(value: Any) -> float:
    """Safely convert to a float in [0, 1]."""
    if value is None:
        return 0.5
    try:
        return max(0.0, min(1.0, float(value)))
    except (ValueError, TypeError):
        return 0.5
