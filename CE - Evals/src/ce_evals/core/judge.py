"""Blind judge — rubric-driven evaluation with multi-model support."""

from __future__ import annotations

import json
import logging
import re
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

from ce_evals.config import get_settings

logger = logging.getLogger(__name__)
from ce_evals.core.judge_backends import get_backend
from ce_evals.core.models import JudgeResult
from ce_evals.core.rubric import Rubric
from ce_evals.protocols.blind import anonymize, strip_metadata


class BlindJudge:
    """Scores anonymized candidate outputs using a rubric across multiple judge models."""

    def __init__(
        self,
        rubric: Rubric,
        judge_models: list[str] | None = None,
        model: str | None = None,
    ) -> None:
        self.rubric = rubric
        settings = get_settings()
        if judge_models:
            self.judge_models = judge_models
        elif model:
            self.judge_models = [model]
        else:
            self.judge_models = settings.judge_models

    def evaluate(
        self, responses: dict[str, str], question: str = ""
    ) -> tuple[JudgeResult, list[JudgeResult]]:
        """Evaluate candidate responses with blind scoring across all judge models.

        Returns:
            (aggregated_result, per_judge_results)
        """
        for name, text in responses.items():
            wc = len(text.split())
            logger.info(f"    [{name}] word count: {wc}")

        labeled_parts, label_to_candidate = anonymize(responses)
        parts = []
        for label, text in labeled_parts:
            parts.append(f"## {label}\n\n{strip_metadata(text)}")

        user_prompt = ""
        if question:
            user_prompt += f"**Question asked:** {question}\n\n"
        user_prompt += (
            "Please evaluate the following responses.\n\n"
            + "\n\n---\n\n".join(parts)
        )

        system_prompt = self.rubric.build_judge_prompt()

        def _judge_one(model_id: str) -> JudgeResult:
            logger.info(f"    Judging with {model_id}...")
            backend = get_backend(model_id)
            try:
                raw, in_tok, out_tok = backend.call(
                    system_prompt, user_prompt, model_id, temperature=0.0
                )
                result = _parse_judge_response(raw, label_to_candidate)
                result.judge_model = model_id
                result.judge_input_tokens = in_tok
                result.judge_output_tokens = out_tok
            except Exception as e:
                logger.warning(f"    {model_id} failed: {e}")
                result = JudgeResult(
                    judge_model=model_id,
                    judge_reasoning=f"Backend error: {e}",
                )
            return result

        per_judge: list[JudgeResult] = []
        if len(self.judge_models) == 1:
            per_judge.append(_judge_one(self.judge_models[0]))
        else:
            with ThreadPoolExecutor(max_workers=len(self.judge_models)) as pool:
                futures = {pool.submit(_judge_one, m): m for m in self.judge_models}
                for future in as_completed(futures):
                    per_judge.append(future.result())
            # Preserve consistent ordering by model list
            model_order = {m: i for i, m in enumerate(self.judge_models)}
            per_judge.sort(key=lambda r: model_order.get(r.judge_model, 0))

        aggregated = _aggregate_results(per_judge, label_to_candidate)
        return aggregated, per_judge


def _aggregate_results(
    per_judge: list[JudgeResult],
    label_to_candidate: dict[str, str],
) -> JudgeResult:
    """Aggregate scores across judges: mean scores, std dev, Borda ranking."""
    valid = [r for r in per_judge if r.scores]
    if not valid:
        return JudgeResult(
            judge_reasoning="No valid judge results to aggregate.",
            label_to_candidate=label_to_candidate,
        )

    # Mean scores per candidate per dimension
    all_candidates = set()
    all_dims = set()
    for r in valid:
        for cand, dims in r.scores.items():
            all_candidates.add(cand)
            all_dims.update(dims.keys())

    agg_scores: dict[str, dict[str, float]] = {}
    score_stdevs: dict[str, dict[str, float]] = {}
    for cand in sorted(all_candidates):
        agg_scores[cand] = {}
        score_stdevs[cand] = {}
        for dim in sorted(all_dims):
            vals = [r.scores[cand][dim] for r in valid if cand in r.scores and dim in r.scores[cand]]
            agg_scores[cand][dim] = statistics.mean(vals) if vals else 0.0
            score_stdevs[cand][dim] = statistics.stdev(vals) if len(vals) > 1 else 0.0

    # Borda count ranking
    borda: dict[str, int] = {c: 0 for c in all_candidates}
    n_cands = len(all_candidates)
    for r in valid:
        if r.ranking:
            for i, cand in enumerate(r.ranking):
                borda[cand] += n_cands - 1 - i
    ranking = sorted(borda, key=lambda c: borda[c], reverse=True)

    # Build reasoning summary
    disagreements = []
    for cand in sorted(all_candidates):
        for dim in sorted(all_dims):
            sd = score_stdevs.get(cand, {}).get(dim, 0.0)
            if sd > 1.0:
                disagreements.append(f"{cand}/{dim} (sd={sd:.2f})")

    reasoning_parts = [f"Aggregated across {len(valid)} judges."]
    if disagreements:
        reasoning_parts.append(f"High disagreement: {', '.join(disagreements)}")

    total_in = sum(r.judge_input_tokens for r in per_judge)
    total_out = sum(r.judge_output_tokens for r in per_judge)

    return JudgeResult(
        scores=agg_scores,
        ranking=ranking,
        judge_reasoning=" ".join(reasoning_parts),
        judge_model="multi:" + "+".join(r.judge_model for r in per_judge if r.judge_model),
        label_to_candidate=label_to_candidate,
        judge_input_tokens=total_in,
        judge_output_tokens=total_out,
    )


def _parse_judge_response(
    raw: str, label_to_candidate: dict[str, str]
) -> JudgeResult:
    """Parse judge JSON and map labels back to candidate names."""
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if not json_match:
        return JudgeResult(
            judge_reasoning=f"Failed to parse judge response: {raw[:300]}"
        )

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        return JudgeResult(
            judge_reasoning=f"Invalid JSON from judge: {raw[:300]}"
        )

    scores: dict[str, dict[str, float]] = {}
    for label, candidate in label_to_candidate.items():
        if label in data.get("scores", {}):
            scores[candidate] = data["scores"][label]

    ranking: list[str] = []
    for label in data.get("ranking", []):
        if label in label_to_candidate:
            ranking.append(label_to_candidate[label])

    return JudgeResult(
        scores=scores,
        ranking=ranking,
        judge_reasoning=data.get("reasoning", ""),
        label_to_candidate=label_to_candidate,
    )
