"""Eval runner — orchestrates candidates x questions -> judge -> report."""

from __future__ import annotations

import logging
import statistics
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

        suite = EvalSuite(
            question_id=question_id,
            question_text=question_text,
            candidates=results,
            judgment=judgment,
            per_judge_results=per_judge,
        )

        # Persist to Postgres (no-op if ce-db unavailable)
        self._persist_eval(suite, run_id=question_id)

        return suite

    def _persist_eval(self, suite: EvalSuite, run_id: str | None = None) -> None:
        """Persist evaluation results to Postgres via ce-db. Best-effort.

        Writes both legacy ``eval_runs`` and granular economics rows:
        ``eval_samples`` + ``eval_regressions``.
        """
        try:
            import asyncio
            from ce_db import EvalRegression as DbEvalRegression
            from ce_db import EvalRun as DbEvalRun
            from ce_db import EvalSample as DbEvalSample
            from ce_db import get_session

            judgment = suite.judgment
            if not judgment:
                return

            scale_midpoint = (
                sum((d.scale_min + d.scale_max) / 2 for d in self.rubric.dimensions)
                / max(len(self.rubric.dimensions), 1)
            )

            def _avg_score(dims: dict[str, float]) -> float:
                if not dims:
                    return 0.0
                return float(sum(dims.values()) / max(len(dims), 1))

            def _replication_index(question_id: str) -> int:
                if "_r" not in question_id:
                    return 1
                suffix = question_id.rsplit("_r", 1)[-1]
                return int(suffix) if suffix.isdigit() else 1

            def _cost_per_correct(cost: float, is_correct: bool) -> float:
                return float(cost if is_correct else cost + 1000.0)

            candidate_scores = {
                name: _avg_score(judgment.scores.get(name, {}))
                for name in suite.candidates
            }
            candidate_variance: dict[str, float] = {}
            for name in suite.candidates:
                per_judge_scores = []
                for jr in suite.per_judge_results:
                    dims = jr.scores.get(name, {})
                    if dims:
                        per_judge_scores.append(_avg_score(dims))
                candidate_variance[name] = (
                    float(statistics.pvariance(per_judge_scores))
                    if len(per_judge_scores) > 1
                    else 0.0
                )

            ranked = judgment.ranking or sorted(
                candidate_scores.keys(),
                key=lambda cand: candidate_scores[cand],
                reverse=True,
            )
            baseline_candidate = ranked[0] if ranked else None

            async def _write():
                async with get_session() as session:
                    eval_run = DbEvalRun(
                        run_id=None,
                        experiment_key=run_id or suite.question_id,
                        rubric_name=self.rubric.name if hasattr(self.rubric, "name") else "unknown",
                        judge_backend=judgment.judge_model,
                        aggregate_score=sum(
                            sum(dims.values()) / max(len(dims), 1)
                            for dims in judgment.scores.values()
                        ) / max(len(judgment.scores), 1) if judgment.scores else 0.0,
                        scores_json=judgment.scores,
                        question_text=suite.question_text[:2000],
                    )
                    session.add(eval_run)
                    await session.flush()

                    baseline_score = candidate_scores.get(baseline_candidate, 0.0) if baseline_candidate else 0.0
                    baseline_variance = candidate_variance.get(baseline_candidate, 0.0) if baseline_candidate else 0.0
                    baseline_cost = suite.candidates.get(baseline_candidate).cost if baseline_candidate and baseline_candidate in suite.candidates else 0.0
                    baseline_correct = baseline_score >= scale_midpoint
                    baseline_cpc = _cost_per_correct(float(baseline_cost), baseline_correct)

                    for candidate_name, candidate in suite.candidates.items():
                        score = candidate_scores.get(candidate_name, 0.0)
                        variance = candidate_variance.get(candidate_name, 0.0)
                        is_correct = score >= scale_midpoint
                        sample = DbEvalSample(
                            eval_run_id=eval_run.id,
                            run_id=None,
                            question_id=suite.question_id,
                            candidate_name=candidate_name,
                            replication_index=_replication_index(suite.question_id),
                            aggregate_score=score,
                            score_variance=variance,
                            is_correct=is_correct,
                            is_baseline=candidate_name == baseline_candidate,
                            total_cost_usd=float(candidate.cost),
                            total_input_tokens=int(candidate.input_tokens),
                            total_output_tokens=int(candidate.output_tokens),
                            duration_seconds=float(candidate.duration_seconds),
                            metadata_json={
                                "judge_model": judgment.judge_model,
                                "rubric": self.rubric.name,
                            },
                        )
                        session.add(sample)

                        if baseline_candidate and candidate_name != baseline_candidate:
                            candidate_cpc = _cost_per_correct(float(candidate.cost), is_correct)
                            quality_delta = score - baseline_score
                            variance_delta = variance - baseline_variance
                            cpc_delta = candidate_cpc - baseline_cpc
                            status = "neutral"
                            if quality_delta < -0.25 or cpc_delta > 0.5:
                                status = "regressed"
                            elif quality_delta > 0.25 and cpc_delta <= 0.0:
                                status = "improved"
                            session.add(
                                DbEvalRegression(
                                    experiment_key=run_id or suite.question_id,
                                    question_id=suite.question_id,
                                    candidate_name=candidate_name,
                                    baseline_candidate=baseline_candidate,
                                    quality_delta=quality_delta,
                                    variance_delta=variance_delta,
                                    cost_per_correct_delta=cpc_delta,
                                    status=status,
                                    thresholds_json={
                                        "quality_delta": 0.25,
                                        "cost_per_correct_delta": 0.5,
                                    },
                                    metadata_json={
                                        "baseline_correct": baseline_correct,
                                        "candidate_correct": is_correct,
                                        "judge_model": judgment.judge_model,
                                    },
                                )
                            )

            asyncio.run(_write())
        except Exception as e:
            logger.debug("Eval persistence skipped: %s", e)

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
