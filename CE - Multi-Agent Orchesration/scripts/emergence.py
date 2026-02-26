"""EmergenceDetector — scores protocol outputs on the 12-criterion emergence rubric.

Usage:
    from scripts.emergence import EmergenceDetector
    detector = EmergenceDetector()
    result = await detector.detect(complex_output, baseline_output, question)
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from scripts.emergence_prompts import EMERGENCE_JUDGE_SYSTEM, EMERGENCE_USER_TEMPLATE

ROOT = Path(__file__).resolve().parent.parent
EMERGENCE_DIR = ROOT / "evaluations" / "emergence"

# Weights per Section 5.3
CONCRETE_WEIGHTS = {"C1": 1.5, "C2": 1.0, "C3": 1.5, "C4": 1.0, "C5": 1.0, "C6": 1.0}
PERCEPTUAL_WEIGHTS = {"P1": 1.0, "P2": 1.0, "P3": 1.5, "P4": 1.0, "P5": 1.0, "P6": 1.0}
CONCRETE_DIVISOR = sum(CONCRETE_WEIGHTS.values())  # 7.0
PERCEPTUAL_DIVISOR = sum(PERCEPTUAL_WEIGHTS.values())  # 6.5


@dataclass
class OutputScores:
    scores: dict[str, dict] = field(default_factory=dict)
    concrete_composite: float = 0.0
    perceptual_composite: float = 0.0
    zone: str = ""


@dataclass
class EmergenceResult:
    question: str = ""
    complex_protocol: str = ""
    baseline_protocol: str = ""
    question_id: str = ""
    complex_scores: OutputScores = field(default_factory=OutputScores)
    baseline_scores: OutputScores = field(default_factory=OutputScores)
    zone_transition: str = ""
    coordination_indicators: dict[str, bool] = field(default_factory=dict)
    judge_reasoning: str = ""
    timestamp: str = ""


def compute_composite(scores: dict[str, dict], weights: dict[str, float], divisor: float) -> float:
    total = sum(scores[k]["score"] * weights[k] for k in weights if k in scores)
    return round(total / divisor, 3)


def classify_zone(concrete: float, perceptual: float) -> str:
    if concrete >= 2.0 and perceptual >= 2.0:
        return "D"
    if concrete >= 2.0:
        return "B"
    if perceptual >= 2.0:
        return "C"
    return "A"


class EmergenceDetector:
    """Scores two protocol outputs on the emergence rubric using Opus."""

    def __init__(self, model: str = "claude-opus-4-6") -> None:
        self.client = anthropic.AsyncAnthropic()
        self.model = model

    async def detect(
        self,
        complex_output: str,
        baseline_output: str,
        question: str,
        *,
        complex_protocol: str = "",
        baseline_protocol: str = "",
        question_id: str = "",
    ) -> EmergenceResult:
        user_prompt = EMERGENCE_USER_TEMPLATE.format(
            question=question,
            complex_output=complex_output,
            baseline_output=baseline_output,
        )

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=16384,
            temperature=0.0,
            system=EMERGENCE_JUDGE_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = "\n".join(b.text for b in response.content if hasattr(b, "text"))
        return self._parse(raw, question, complex_protocol, baseline_protocol, question_id)

    def _parse(
        self,
        raw: str,
        question: str,
        complex_protocol: str,
        baseline_protocol: str,
        question_id: str,
    ) -> EmergenceResult:
        json_match = re.search(r"\{[\s\S]*\}", raw)
        if not json_match:
            return EmergenceResult(
                question=question,
                judge_reasoning=f"Failed to parse: {raw[:300]}",
            )

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            return EmergenceResult(
                question=question,
                judge_reasoning=f"Invalid JSON: {raw[:300]}",
            )

        def parse_output(key: str) -> OutputScores:
            out = data.get(key, {})
            scores = out.get("scores", {})
            concrete = compute_composite(scores, CONCRETE_WEIGHTS, CONCRETE_DIVISOR)
            perceptual = compute_composite(scores, PERCEPTUAL_WEIGHTS, PERCEPTUAL_DIVISOR)
            zone = classify_zone(concrete, perceptual)
            return OutputScores(
                scores=scores,
                concrete_composite=concrete,
                perceptual_composite=perceptual,
                zone=zone,
            )

        complex_scores = parse_output("complex_output")
        baseline_scores = parse_output("baseline_output")

        return EmergenceResult(
            question=question,
            complex_protocol=complex_protocol,
            baseline_protocol=baseline_protocol,
            question_id=question_id,
            complex_scores=complex_scores,
            baseline_scores=baseline_scores,
            zone_transition=f"{baseline_scores.zone}->{complex_scores.zone}",
            coordination_indicators=data.get("coordination_indicators", {}),
            judge_reasoning=data.get("reasoning", ""),
            timestamp=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        )


def save_emergence_result(result: EmergenceResult, pair_id: int) -> Path:
    """Save emergence result to evaluations/emergence/."""
    EMERGENCE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"pair{pair_id}_{result.question_id}_{result.timestamp}.json"
    outpath = EMERGENCE_DIR / filename
    outpath.write_text(json.dumps(asdict(result), indent=2))
    return outpath
