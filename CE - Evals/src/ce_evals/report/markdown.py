"""Markdown report generator — rubric-driven tables with inter-rater agreement."""

from __future__ import annotations

import statistics
from pathlib import Path

from ce_evals.core.models import EvalSuite
from ce_evals.core.rubric import Rubric


def _load_protocol_descriptions() -> dict[str, str]:
    desc_file = Path(__file__).resolve().parent.parent.parent.parent / "protocols" / "descriptions.yaml"
    if desc_file.exists():
        import yaml
        return yaml.safe_load(desc_file.read_text()) or {}
    return {}


class MarkdownReport:
    """Generates evaluation reports with rubric-driven columns."""

    def __init__(self, rubric: Rubric) -> None:
        self.rubric = rubric
        self._protocol_descriptions = _load_protocol_descriptions()

    def _render_eval_design(self, suites: list[EvalSuite]) -> str:
        lines = ["## Evaluation Design\n"]

        # Questions tested
        lines.append("### Questions\n")
        for s in suites:
            lines.append(f"- **{s.question_id}:** {s.question_text}")
        lines.append("")

        # Protocols tested
        lines.append("### Protocols\n")
        candidates = sorted(self._all_candidate_names(suites))
        for cand in candidates:
            desc = self._protocol_descriptions.get(cand, cand.replace("_", " ").title())
            lines.append(f"- {desc}")
        lines.append("")

        # Judging criteria
        lines.append("### Judging Criteria (1-5 scale)\n")
        for dim in self.rubric.dimensions:
            lines.append(f"- **{dim.name.replace('_', ' ').title()}:** {dim.description}")
        lines.append("")

        return "\n".join(lines)

    def render(self, suites: list[EvalSuite], title: str = "Protocol Evaluation Report") -> str:
        sections = [
            f"# {title}\n",
            self._render_eval_design(suites),
            self._render_summary(suites),
            self._render_score_table(suites),
            self._render_inter_rater_agreement(suites),
            self._render_protocol_analysis(suites),
            self._render_cost_table(suites),
            self._render_ranking_summary(suites),
            self._render_per_question(suites),
            self._render_methodology(suites),
        ]
        return "\n\n".join(s for s in sections if s)

    def _render_summary(self, suites: list[EvalSuite]) -> str:
        lines = ["## Executive Summary\n"]

        mode_means = self._compute_candidate_means(suites)
        if mode_means:
            best = max(mode_means, key=mode_means.get)
            lines.append(
                f"**Best overall candidate:** {best} "
                f"(mean score: {mode_means[best]:.2f}/5.0)\n"
            )

        total_cost = sum(
            cr.cost for s in suites for cr in s.candidates.values()
        )
        judge_cost = sum(
            s.judgment.judge_cost for s in suites if s.judgment
        )
        judge_models_used = set()
        for s in suites:
            for jr in s.per_judge_results:
                if jr.judge_model:
                    judge_models_used.add(jr.judge_model)

        lines.append(f"**Total candidate cost:** ${total_cost:.2f}")
        lines.append(f"**Total judge cost:** ${judge_cost:.2f}")
        if judge_models_used:
            lines.append(f"**Judge models:** {', '.join(sorted(judge_models_used))}")
        lines.append(
            f"**Questions evaluated:** {len(suites)} | "
            f"**Candidates tested:** {len(self._all_candidate_names(suites))}"
        )

        # Prose conclusions
        if mode_means:
            best = max(mode_means, key=mode_means.get)
            worst = min(mode_means, key=mode_means.get)
            spread = mode_means[best] - mode_means[worst]
            lines.append("")

            # Dominance statement
            if spread > 0.5:
                lines.append(
                    f"{best} dominated the evaluation with a {spread:.2f}-point lead "
                    f"over {worst}, suggesting clear qualitative advantages across question types."
                )
            else:
                lines.append(
                    f"Results were tightly clustered (spread: {spread:.2f}), "
                    f"with {best} holding a narrow edge over the field."
                )

            # Inter-rater agreement pattern
            high_disagree = 0
            total_dims = 0
            for s in suites:
                if len(s.per_judge_results) > 1:
                    for jr in s.per_judge_results:
                        for cand, dscores in jr.scores.items():
                            total_dims += len(dscores)
                    # Count high-stdev dims
                    from collections import defaultdict
                    dim_vals: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
                    for jr in s.per_judge_results:
                        for cand, dscores in jr.scores.items():
                            for dim, score in dscores.items():
                                dim_vals[cand][dim].append(score)
                    for cand, dims in dim_vals.items():
                        for dim, vals in dims.items():
                            if len(vals) > 1 and statistics.stdev(vals) > 1.0:
                                high_disagree += 1

            if total_dims > 0:
                disagree_rate = high_disagree / max(total_dims // len(self.rubric.dimension_names), 1)
                if disagree_rate < 0.1:
                    lines.append("Judges showed strong agreement across most dimensions, lending confidence to the rankings.")
                elif disagree_rate < 0.3:
                    lines.append("Moderate inter-rater disagreement on select dimensions suggests some evaluation criteria may be more subjective.")
                else:
                    lines.append("Significant inter-rater disagreement indicates these protocols elicit genuinely different quality judgments depending on evaluator perspective.")

        return "\n".join(lines)

    def _render_score_table(self, suites: list[EvalSuite]) -> str:
        lines = ["## Score Table (Mean Across Questions)\n"]
        dims = self.rubric.dimension_names

        agg: dict[str, dict[str, list[float]]] = {}
        for s in suites:
            if not s.judgment:
                continue
            for cand, dim_scores in s.judgment.scores.items():
                agg.setdefault(cand, {})
                for dim, score in dim_scores.items():
                    agg[cand].setdefault(dim, []).append(score)

        short = [d[:14] for d in dims]
        header = "| Candidate | " + " | ".join(short) + " | Mean |"
        sep = "|-----------|" + "|".join(["------:" for _ in dims]) + "|------:|"
        lines.extend([header, sep])

        for cand in sorted(agg):
            vals = []
            for dim in dims:
                scores = agg[cand].get(dim, [])
                mean = sum(scores) / len(scores) if scores else 0
                vals.append(f"{mean:.1f}")
            all_scores = [s for dl in agg[cand].values() for s in dl]
            overall = sum(all_scores) / len(all_scores) if all_scores else 0
            row = f"| {cand} | " + " | ".join(vals) + f" | **{overall:.2f}** |"
            lines.append(row)

        return "\n".join(lines)

    def _render_inter_rater_agreement(self, suites: list[EvalSuite]) -> str:
        """Show per-dimension std dev across judges, flag high disagreement."""
        has_multi = any(len(s.per_judge_results) > 1 for s in suites)
        if not has_multi:
            return ""

        lines = ["## Inter-Rater Agreement\n"]
        dims = self.rubric.dimension_names

        # Collect per-candidate, per-dimension scores from each judge
        all_candidates = set()
        dim_stdevs: dict[str, dict[str, list[float]]] = {}  # cand -> dim -> [scores from judges]
        for s in suites:
            for jr in s.per_judge_results:
                for cand, dscores in jr.scores.items():
                    all_candidates.add(cand)
                    dim_stdevs.setdefault(cand, {})
                    for dim, score in dscores.items():
                        dim_stdevs[cand].setdefault(dim, []).append(score)

        short = [d[:14] for d in dims]
        header = "| Candidate | " + " | ".join(short) + " |"
        sep = "|-----------|" + "|".join(["------:" for _ in dims]) + "|"
        lines.extend([header, sep])

        flagged = []
        for cand in sorted(all_candidates):
            vals = []
            for dim in dims:
                scores = dim_stdevs.get(cand, {}).get(dim, [])
                sd = statistics.stdev(scores) if len(scores) > 1 else 0.0
                marker = " **!**" if sd > 1.0 else ""
                vals.append(f"{sd:.2f}{marker}")
                if sd > 1.0:
                    flagged.append(f"{cand}/{dim} (sd={sd:.2f})")
            lines.append(f"| {cand} | " + " | ".join(vals) + " |")

        if flagged:
            lines.append(f"\n**High disagreement (>1.0):** {', '.join(flagged)}")

        # Per-judge rankings side by side
        lines.append("\n### Per-Judge Rankings\n")
        judge_models = []
        for s in suites:
            for jr in s.per_judge_results:
                if jr.judge_model and jr.judge_model not in judge_models:
                    judge_models.append(jr.judge_model)

        if judge_models:
            header = "| Question | " + " | ".join(judge_models) + " |"
            sep = "|----------|" + "|".join(["--------" for _ in judge_models]) + "|"
            lines.extend([header, sep])
            for s in suites:
                judge_rankings = {}
                for jr in s.per_judge_results:
                    if jr.ranking:
                        judge_rankings[jr.judge_model] = " > ".join(jr.ranking)
                cols = [judge_rankings.get(m, "—") for m in judge_models]
                lines.append(f"| {s.question_id} | " + " | ".join(cols) + " |")

        return "\n".join(lines)

    def _render_cost_table(self, suites: list[EvalSuite]) -> str:
        lines = ["## Cost Efficiency\n"]
        header = "| Candidate | Total Cost | Mean Score | Score/Dollar |"
        sep = "|-----------|----------:|-----------:|------------:|"
        lines.extend([header, sep])

        means = self._compute_candidate_means(suites)
        costs: dict[str, float] = {}
        for s in suites:
            for name, cr in s.candidates.items():
                costs[name] = costs.get(name, 0) + cr.cost

        for cand in sorted(means):
            cost = costs.get(cand, 0)
            mean = means[cand]
            spd = mean / cost if cost > 0 else float("inf")
            cost_str = f"${cost:.2f}" if cost > 0 else "N/A"
            spd_str = f"{spd:.1f}" if cost > 0 else "N/A"
            lines.append(f"| {cand} | {cost_str} | {mean:.2f} | {spd_str} |")

        return "\n".join(lines)

    def _render_ranking_summary(self, suites: list[EvalSuite]) -> str:
        lines = ["## Forced Ranking Summary\n"]

        first_place: dict[str, int] = {}
        for s in suites:
            if s.judgment and s.judgment.ranking:
                winner = s.judgment.ranking[0]
                first_place[winner] = first_place.get(winner, 0) + 1

        header = "| Candidate | First-Place Wins |"
        sep = "|-----------|----------------:|"
        lines.extend([header, sep])

        for cand in sorted(first_place, key=first_place.get, reverse=True):
            lines.append(f"| {cand} | {first_place[cand]} |")

        return "\n".join(lines)

    def _render_protocol_analysis(self, suites: list[EvalSuite]) -> str:
        """Cross-question synthesis: what judges said about each protocol across all questions."""
        lines = ["## Protocol Analysis\n"]

        candidates = sorted(self._all_candidate_names(suites))
        if not candidates:
            return ""

        means = self._compute_candidate_means(suites)

        for cand in candidates:
            lines.append(f"### {cand}\n")

            # Collect all judge reasoning that mentions this candidate
            cand_reasoning: list[tuple[str, str, str]] = []  # (question_id, judge_model, reasoning)
            wins = 0
            total = 0
            dim_scores: dict[str, list[float]] = {}

            for s in suites:
                if not s.judgment:
                    continue
                total += 1
                if s.judgment.ranking and s.judgment.ranking[0] == cand:
                    wins += 1

                # Collect dimension scores
                for dim, score in s.judgment.scores.get(cand, {}).items():
                    dim_scores.setdefault(dim, []).append(score)

                for jr in s.per_judge_results:
                    if jr.judge_reasoning and not jr.judge_reasoning.startswith("Backend error"):
                        cand_reasoning.append((s.question_id, jr.judge_model or "unknown", jr.judge_reasoning))

            # Summary stats
            mean = means.get(cand, 0)
            lines.append(f"**Mean score:** {mean:.2f}/5.0 | **First-place wins:** {wins}/{total}\n")

            # Dimension strengths/weaknesses
            if dim_scores:
                best_dim = max(dim_scores, key=lambda d: statistics.mean(dim_scores[d]))
                worst_dim = min(dim_scores, key=lambda d: statistics.mean(dim_scores[d]))
                best_val = statistics.mean(dim_scores[best_dim])
                worst_val = statistics.mean(dim_scores[worst_dim])
                lines.append(
                    f"**Strongest dimension:** {best_dim.replace('_', ' ')} ({best_val:.1f}) | "
                    f"**Weakest:** {worst_dim.replace('_', ' ')} ({worst_val:.1f})\n"
                )

            # Check for high disagreement on this candidate
            disagree_dims = []
            for s in suites:
                if len(s.per_judge_results) > 1:
                    from collections import defaultdict
                    dv: dict[str, list[float]] = defaultdict(list)
                    for jr in s.per_judge_results:
                        for dim, score in jr.scores.get(cand, {}).items():
                            dv[dim].append(score)
                    for dim, vals in dv.items():
                        if len(vals) > 1 and statistics.stdev(vals) > 1.0:
                            disagree_dims.append(f"{s.question_id}/{dim}")

            if disagree_dims:
                lines.append(f"**High disagreement:** {', '.join(disagree_dims)}\n")

            lines.append("")

        return "\n".join(lines)

    def _render_per_question(self, suites: list[EvalSuite]) -> str:
        lines = ["## Per-Question Results\n"]

        for s in suites:
            lines.append(f"### {s.question_id}\n")
            lines.append(f"**Question:** {s.question_text}\n")

            if not s.judgment:
                lines.append("_No judge scores available._\n")
                continue

            header = "| Candidate | Score | Cost | Duration |"
            sep = "|-----------|------:|-----:|---------:|"
            lines.extend([header, sep])

            for name, cr in s.candidates.items():
                scores = s.judgment.scores.get(name, {})
                mean = sum(scores.values()) / len(scores) if scores else 0
                cost_str = f"${cr.cost:.2f}" if cr.cost > 0 else "N/A"
                lines.append(
                    f"| {name} | {mean:.2f} | {cost_str} | {cr.duration_seconds:.0f}s |"
                )

            if s.judgment.ranking:
                ranked = " > ".join(s.judgment.ranking)
                lines.append(f"\n**Ranking:** {ranked}")

            # Per-judge reasoning blockquotes
            if s.per_judge_results:
                lines.append("\n#### Judge Reasoning\n")
                for jr in s.per_judge_results:
                    if jr.judge_reasoning and not jr.judge_reasoning.startswith("Backend error"):
                        model_name = jr.judge_model or "Unknown"
                        # Indent multi-line reasoning as blockquote
                        quoted = jr.judge_reasoning.replace("\n", "\n> ")
                        lines.append(f"> **{model_name}:** {quoted}\n")

            lines.append("")

        return "\n".join(lines)

    def _render_methodology(self, suites: list[EvalSuite]) -> str:
        dims = self.rubric.dimension_names
        dim_list = ", ".join(d.replace("_", " ") for d in dims)

        judge_models_used = set()
        for s in suites:
            for jr in s.per_judge_results:
                if jr.judge_model:
                    judge_models_used.add(jr.judge_model)

        model_note = ""
        if judge_models_used:
            model_note = f"- **Judge models:** {', '.join(sorted(judge_models_used))}\n"

        return (
            f"## Methodology\n\n"
            f"- **Rubric:** {self.rubric.name} ({len(dims)} dimensions: {dim_list})\n"
            f"{model_note}"
            f"- Outputs anonymized and randomized before judging\n"
            f"- Each dimension scored 1-5 by blind judges\n"
            f"- Scores aggregated via mean across judges; rankings via Borda count\n"
            f"- Inter-rater agreement measured by std dev across judges\n\n"
            f"*Generated by CE-Evals*"
        )

    # --- helpers ---

    def _compute_candidate_means(self, suites: list[EvalSuite]) -> dict[str, float]:
        agg: dict[str, list[float]] = {}
        for s in suites:
            if not s.judgment:
                continue
            for cand, dim_scores in s.judgment.scores.items():
                agg.setdefault(cand, []).extend(dim_scores.values())
        return {c: sum(v) / len(v) for c, v in agg.items() if v}

    def _all_candidate_names(self, suites: list[EvalSuite]) -> set[str]:
        return {name for s in suites for name in s.candidates}
