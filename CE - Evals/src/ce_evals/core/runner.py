"""Eval runner — orchestrates candidates x questions -> judge -> report."""

from __future__ import annotations

import logging
import time
from typing import Callable

from ce_evals.core.judge import BlindJudge
from ce_evals.core.models import CandidateResult, EvalSuite
from ce_evals.core.rubric import Rubric

logger = logging.getLogger(__name__)


class EvalRunner:
    """Runs a batch of candidates on a question, judges, returns EvalSuite."""

    def __init__(
        self,
        rubric: Rubric,
        judge_model: str | None = None,
        judge_models: list[str] | None = None,
    ) -> None:
        self.rubric = rubric
        if judge_models:
            self.judge = BlindJudge(rubric, judge_models=judge_models)
        elif judge_model:
            self.judge = BlindJudge(rubric, model=judge_model)
        else:
            self.judge = BlindJudge(rubric)

    def run(
        self,
        question_id: str,
        question_text: str,
        candidates: dict[str, Callable[[str], str]],
    ) -> EvalSuite:
        results: dict[str, CandidateResult] = {}

        for name, run_fn in candidates.items():
            logger.info(f"  Running {name}...")
            start = time.time()
            output = run_fn(question_text)
            duration = time.time() - start
            results[name] = CandidateResult(
                name=name,
                output_text=output,
                duration_seconds=duration,
            )

        logger.info("  Judging...")
        responses = {name: cr.output_text for name, cr in results.items()}
        judgment, per_judge = self.judge.evaluate(responses, question=question_text)

        return EvalSuite(
            question_id=question_id,
            question_text=question_text,
            candidates=results,
            judgment=judgment,
            per_judge_results=per_judge,
        )

    def run_batch(
        self,
        questions: list[tuple[str, str]],
        candidates: dict[str, Callable[[str], str]],
        replications: int = 1,
    ) -> list[EvalSuite]:
        suites = []
        total = len(questions) * replications
        completed = 0
        batch_start = time.time()
        for rep in range(replications):
            for qid, qtxt in questions:
                completed += 1
                run_id = f"{qid}" if replications == 1 else f"{qid}_r{rep + 1}"
                logger.info(f"[{completed}/{total}] Running {run_id}...")
                suite_start = time.time()
                suite = self.run(run_id, qtxt, candidates)
                suite_time = time.time() - suite_start
                suites.append(suite)
                elapsed = time.time() - batch_start
                avg = elapsed / completed
                remaining = avg * (total - completed)
                logger.info(
                    f"  Done in {suite_time:.1f}s — est. {remaining / 60:.1f}m remaining"
                )
        return suites
