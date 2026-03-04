"""Emergence detection pair definitions + question mappings.

Each pair compares a complex multi-agent protocol against a simpler baseline
on the same set of benchmark questions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_FILE = ROOT / "benchmark-questions.json"


@dataclass
class Pair:
    id: int
    complex_protocol: str
    baseline_protocol: str
    question_ids: list[str]
    rationale: str


PAIRS: list[Pair] = [
    Pair(
        id=1,
        complex_protocol="p16_ach",
        baseline_protocol="p03_parallel_synthesis",
        question_ids=["Q4.1", "Q4.2", "Q4.3", "Q4.4"],
        rationale="ACH structured hypothesis testing vs simple synthesis on diagnostic questions",
    ),
    Pair(
        id=2,
        complex_protocol="p05_constraint_negotiation",
        baseline_protocol="p04_multi_round_debate",
        question_ids=["Q3.1", "Q3.2", "Q3.3", "Q3.4"],
        rationale="Constraint negotiation vs debate on stakeholder tension questions",
    ),
    Pair(
        id=3,
        complex_protocol="p14_one_two_four_all",
        baseline_protocol="p03_parallel_synthesis",
        question_ids=["Q5.1", "Q5.2", "Q5.3", "Q5.4"],
        rationale="Progressive merging vs flat synthesis on exploration questions",
    ),
    Pair(
        id=4,
        complex_protocol="p06_triz",
        baseline_protocol="p17_red_blue_white",
        question_ids=["Q8.1", "Q8.2", "Q8.3", "Q8.4"],
        rationale="TRIZ inversion vs Red/Blue/White adversarial on risk/premortem questions",
    ),
    Pair(
        id=5,
        complex_protocol="p24_causal_loop_mapping",
        baseline_protocol="p03_parallel_synthesis",
        question_ids=["Q7.1", "Q7.2", "Q7.3", "Q7.4"],
        rationale="Causal loop systems thinking vs synthesis on paradox/wicked questions",
    ),
    Pair(
        id=6,
        complex_protocol="p18_delphi_method",
        baseline_protocol="p04_multi_round_debate",
        question_ids=["Q6.1", "Q6.2", "Q6.3", "Q6.4"],
        rationale="Delphi consensus vs debate on prioritization questions",
    ),
    Pair(
        id=7,
        complex_protocol="p37_hegel_sublation",
        baseline_protocol="p04_multi_round_debate",
        question_ids=["Q2.1", "Q2.2", "Q2.3", "Q2.4"],
        rationale="Hegelian dialectic vs debate on adversarial questions",
    ),
    Pair(
        id=8,
        complex_protocol="p23_cynefin_probe",
        baseline_protocol="p03_parallel_synthesis",
        question_ids=["Q1.1", "Q1.2", "Q1.3", "Q1.4"],
        rationale="Cynefin sense-making vs synthesis on integration questions",
    ),
    Pair(
        id=9,
        complex_protocol="p28_six_hats",
        baseline_protocol="p03_parallel_synthesis",
        question_ids=["Q3.1", "Q3.2", "Q3.5", "Q3.4"],
        rationale="Six Hats structured perspectives vs synthesis on stakeholder tension",
    ),
    Pair(
        id=10,
        complex_protocol="p38_klein_premortem",
        baseline_protocol="p04_multi_round_debate",
        question_ids=["Q8.1", "Q8.2", "Q8.3", "Q8.4"],
        rationale="Klein premortem vs debate on risk/premortem questions",
    ),
]

PAIRS_BY_ID: dict[int, Pair] = {p.id: p for p in PAIRS}


def load_questions() -> dict[str, dict]:
    """Load benchmark questions keyed by id."""
    with open(BENCHMARK_FILE) as f:
        questions = json.load(f)
    return {q["id"]: q for q in questions}


def get_pair_questions(pair: Pair) -> list[dict]:
    """Load the benchmark questions for a given pair."""
    all_qs = load_questions()
    result = []
    for qid in pair.question_ids:
        if qid not in all_qs:
            raise ValueError(f"Unknown question ID: {qid}")
        result.append(all_qs[qid])
    return result
