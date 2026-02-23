#!/usr/bin/env python3
"""Blind Opus judge for Coordination Lab evaluations.

Scores anonymized protocol outputs on 7 dimensions without knowing which protocol
produced them. Adapted from C-Suite's evaluation/judge.py for standalone use.

Usage:
    # Judge a single eval file
    python scripts/judge.py evaluations/p16_ach_Q4.1_20260222.json

    # Compare multiple protocols on same question
    python scripts/judge.py evaluations/p16_ach_Q4.1_*.json evaluations/p06_triz_Q4.1_*.json

    # Judge all evals for a question
    python scripts/judge.py --question Q4.1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent.parent
EVALUATIONS_DIR = ROOT / "evaluations"
JUDGED_DIR = EVALUATIONS_DIR / "judged"

DIMENSIONS = [
    "specificity",
    "internal_consistency",
    "tension_surfacing",
    "constraint_awareness",
    "actionability",
    "reasoning_depth",
    "completeness",
]

JUDGE_SYSTEM_PROMPT = """You are a senior strategy consultant evaluating \
strategic recommendations for a $5-40M professional services firm.

You will receive multiple responses to the same strategic question. Each is \
labeled only as "Response A", "Response B", etc. You do NOT know how they \
were generated.

Score each response on these 7 dimensions (1-5 scale):

1. **Specificity** (1-5): Are recommendations concrete enough to act on tomorrow?
2. **Internal Consistency** (1-5): Do financial, operational, and strategic recommendations align?
3. **Tension Surfacing** (1-5): Does the output identify genuine trade-offs, \
not just list perspectives?
4. **Constraint Awareness** (1-5): Does it acknowledge real-world limits \
(budget, timeline, headcount)?
5. **Actionability** (1-5): Is there a clear first step, owner, and timeline?
6. **Reasoning Depth** (1-5): Are claims supported by evidence or reasoning chains?
7. **Completeness** (1-5): Are all relevant functional perspectives addressed?

After scoring, provide a forced ranking: if you had to present ONE of \
these responses to a $15M company's CEO, which would you pick? Rank all \
responses from best to worst.

Respond ONLY with valid JSON in this exact format:
{
  "scores": {
    "Response A": {"specificity": N, "internal_consistency": N, \
"tension_surfacing": N, "constraint_awareness": N, "actionability": N, \
"reasoning_depth": N, "completeness": N},
    "Response B": {...}
  },
  "ranking": ["Response X", "Response Y", ...],
  "reasoning": "Brief explanation of key differences between top and bottom responses."
}"""

# Tokens to strip for blind evaluation — covers all 48 protocols
_STRIP_PATTERNS = [
    r"(?i)\b(TRIZ|ACH|Delphi|Cynefin|OODA|Troika|Ecocycle|Borda|Vickrey)\b",
    r"(?i)\b(Six Hats|PMI|Crazy Eights|Affinity|Causal Loop|System Archetype)\b",
    r"(?i)\b(Red Team|Blue Team|White Team|Red/Blue/White)\b",
    r"(?i)\b(Wicked Questions?|Min Specs?|HSR|DAD|25/10|1-2-4-All)\b",
    r"(?i)\b(Evaporation Cloud|Current Reality Tree|Satisficing)\b",
    r"(?i)\b(Peirce|Hegel|Klein|Popper|Boyd|Duke|Aristotle|Leibniz|Kant|Whitehead|Polya)\b",
    r"(?i)\b(Llull|Wittgenstein|Tetlock|Incubation)\b",
    r"(?i)(debate|negotiation|synthesis|parallel synthesis|constraint negotiation)\s*(mode|approach|protocol)?",
    r"(?i)Protocol\s*P\d+[a-c]?",
    r"Debate ID:\s*\S+",
    r"Constraint[s]?:\s*\d+",
]


@dataclass
class JudgeResult:
    """Result from blind evaluation."""
    scores: dict[str, dict[str, float]] = field(default_factory=dict)
    ranking: list[str] = field(default_factory=list)
    judge_reasoning: str = ""
    label_to_mode: dict[str, str] = field(default_factory=dict)
    question_id: str = ""


class BlindJudge:
    """Scores anonymized outputs on 7 dimensions using Opus."""

    def __init__(self, model: str = "claude-opus-4-6") -> None:
        self.client = anthropic.AsyncAnthropic()
        self.model = model

    async def evaluate(self, responses: dict[str, str], question_id: str = "") -> JudgeResult:
        """Evaluate {protocol_name: output_text} with blind scoring."""
        modes = list(responses.keys())
        random.shuffle(modes)
        labels = [f"Response {chr(65 + i)}" for i in range(len(modes))]
        label_to_mode = dict(zip(labels, modes))

        parts = []
        for label, mode in zip(labels, modes):
            text = _strip_metadata(responses[mode])
            parts.append(f"## {label}\n\n{text}")

        user_prompt = (
            "Please evaluate the following strategic recommendations.\n\n"
            + "\n\n---\n\n".join(parts)
        )

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.0,
            system=JUDGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text
        result = _parse_judge_response(raw, label_to_mode)
        result.question_id = question_id
        return result


def _strip_metadata(text: str) -> str:
    """Remove protocol-identifying tokens for blind evaluation."""
    for pattern in _STRIP_PATTERNS:
        text = re.sub(pattern, "", text)
    return text.strip()


def _parse_judge_response(raw: str, label_to_mode: dict[str, str]) -> JudgeResult:
    """Parse judge JSON and map labels back to protocol names."""
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if not json_match:
        return JudgeResult(judge_reasoning=f"Failed to parse judge response: {raw[:200]}")

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        return JudgeResult(judge_reasoning=f"Invalid JSON from judge: {raw[:200]}")

    scores: dict[str, dict[str, float]] = {}
    for label, mode in label_to_mode.items():
        if label in data.get("scores", {}):
            scores[mode] = data["scores"][label]

    ranking: list[str] = []
    for label in data.get("ranking", []):
        if label in label_to_mode:
            ranking.append(label_to_mode[label])

    return JudgeResult(
        scores=scores,
        ranking=ranking,
        judge_reasoning=data.get("reasoning", ""),
        label_to_mode=label_to_mode,
    )


def _extract_response_text(eval_data: dict) -> str:
    """Extract the primary response text from an evaluation JSON envelope."""
    result = eval_data.get("result", {})
    # Try common output keys from different protocols
    for key in ("synthesis", "final_synthesis", "output", "response", "result", "final_answer"):
        if key in result and isinstance(result[key], str):
            return result[key]
    # Fallback: serialize entire result
    return json.dumps(result, indent=2)


def collect_eval_files(paths: list[str], question_id: str | None) -> list[Path]:
    """Collect evaluation JSON files from CLI args or --question filter."""
    if paths:
        files = []
        for p in paths:
            fp = Path(p)
            if fp.is_file():
                files.append(fp)
            else:
                files.extend(Path(".").glob(p))
        return files

    if question_id:
        return sorted(EVALUATIONS_DIR.glob(f"*_{question_id}_*.json"))

    return []


async def judge_files(files: list[Path], model: str) -> JudgeResult:
    """Load eval files and run blind judge."""
    responses: dict[str, str] = {}
    question_id = ""

    for f in files:
        data = json.loads(f.read_text())
        protocol = data.get("protocol", f.stem)
        question_id = question_id or data.get("question_id", "")
        responses[protocol] = _extract_response_text(data)

    if not responses:
        print("No responses to judge.")
        sys.exit(1)

    if len(responses) == 1:
        print(f"Only 1 protocol found — judging single response for {list(responses)[0]}")

    judge = BlindJudge(model=model)
    print(f"Judging {len(responses)} response(s) with {model}...")
    result = await judge.evaluate(responses, question_id=question_id)
    return result


def save_result(result: JudgeResult) -> Path:
    """Save judged result to evaluations/judged/."""
    JUDGED_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    qid = result.question_id or "unknown"
    outpath = JUDGED_DIR / f"{qid}_{timestamp}.json"
    outpath.write_text(json.dumps(asdict(result), indent=2))
    return outpath


def print_result(result: JudgeResult) -> None:
    """Print a human-readable summary."""
    print("\n=== Judge Results ===\n")
    for protocol, dim_scores in result.scores.items():
        mean = sum(dim_scores.values()) / len(dim_scores) if dim_scores else 0
        print(f"  {protocol}: {mean:.2f}/5.0")
        for dim, score in dim_scores.items():
            print(f"    {dim}: {score}")
    if result.ranking:
        print(f"\n  Ranking: {' > '.join(result.ranking)}")
    if result.judge_reasoning:
        print(f"\n  Reasoning: {result.judge_reasoning}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Blind evaluation judge")
    parser.add_argument("files", nargs="*", help="Evaluation JSON files to judge")
    parser.add_argument("--question", "-q", help="Judge all evals for this question ID")
    parser.add_argument("--model", default="claude-opus-4-6", help="Judge model")
    args = parser.parse_args()

    files = collect_eval_files(args.files, args.question)
    if not files:
        print("No evaluation files found. Provide file paths or --question ID.")
        sys.exit(1)

    print(f"Found {len(files)} eval file(s): {', '.join(f.name for f in files)}")
    result = asyncio.run(judge_files(files, args.model))
    outpath = save_result(result)
    print_result(result)
    print(f"\nSaved to {outpath}")


if __name__ == "__main__":
    main()
