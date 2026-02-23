"""
Evaluation report generator.

Produces markdown comparison tables from benchmark results and judge scores.
"""

from __future__ import annotations

from csuite.evaluation.benchmark import BenchmarkResult
from csuite.evaluation.judge import DIMENSIONS, JudgeResult

MODE_LABELS = {
    "single": "A: Single",
    "context": "B: Single+Context",
    "synthesize": "C: Synthesize",
    "debate": "D: Debate",
    "negotiate": "E: Negotiate",
}


class EvaluationReport:
    """Generates markdown comparison table from benchmark results."""

    def render(self, benchmark: BenchmarkResult, judge_results: dict[str, JudgeResult]) -> str:
        """Render full evaluation report.

        Args:
            benchmark: Results from BenchmarkRunner.run_full_benchmark()
            judge_results: Dict of question_id -> JudgeResult
        """
        sections = [
            "# Multi-Agent Evaluation Report\n",
            self._render_summary(benchmark, judge_results),
            self._render_score_table(judge_results),
            self._render_cost_table(benchmark, judge_results),
            self._render_structural_metrics(benchmark),
            self._render_ranking_summary(judge_results),
            self._render_per_question(benchmark, judge_results),
            self._render_methodology(),
        ]
        return "\n\n".join(sections)

    def _render_summary(
        self, benchmark: BenchmarkResult, judge_results: dict[str, JudgeResult]
    ) -> str:
        lines = ["## Executive Summary\n"]

        # Compute mean score per mode across all questions and dimensions
        mode_means = _compute_mode_means(judge_results)
        if mode_means:
            best = max(mode_means, key=mode_means.get)  # type: ignore[arg-type]
            lines.append(
                f"**Best overall mode:** {MODE_LABELS.get(best, best)} "
                f"(mean score: {mode_means[best]:.2f}/5.0)\n"
            )

        # Total cost
        total_cost = 0.0
        for q_results in benchmark.results.values():
            for mr in q_results.values():
                total_cost += mr.cost
        lines.append(f"**Total benchmark cost:** ${total_cost:.2f}")

        num_q = len(benchmark.results)
        num_modes = len({m for qr in benchmark.results.values() for m in qr})
        lines.append(f"**Questions evaluated:** {num_q} | **Modes tested:** {num_modes}")

        return "\n".join(lines)

    def _render_score_table(self, judge_results: dict[str, JudgeResult]) -> str:
        lines = ["## Score Table (Mean Across Questions)\n"]

        # Aggregate scores per mode per dimension
        agg: dict[str, dict[str, list[float]]] = {}
        for jr in judge_results.values():
            for mode, dim_scores in jr.scores.items():
                agg.setdefault(mode, {})
                for dim, score in dim_scores.items():
                    agg[mode].setdefault(dim, []).append(score)

        # Header
        dim_short = [d[:12] for d in DIMENSIONS]
        header = "| Mode | " + " | ".join(dim_short) + " | Mean |"
        sep = "|------|" + "|".join(["------:" for _ in DIMENSIONS]) + "|------:|"
        lines.extend([header, sep])

        for mode in ["single", "context", "synthesize", "debate", "negotiate"]:
            if mode not in agg:
                continue
            label = MODE_LABELS.get(mode, mode)
            vals = []
            for dim in DIMENSIONS:
                scores = agg[mode].get(dim, [])
                mean = sum(scores) / len(scores) if scores else 0
                vals.append(f"{mean:.1f}")
            all_scores = [s for dim_list in agg[mode].values() for s in dim_list]
            overall = sum(all_scores) / len(all_scores) if all_scores else 0
            row = f"| {label} | " + " | ".join(vals) + f" | **{overall:.2f}** |"
            lines.append(row)

        return "\n".join(lines)

    def _render_cost_table(
        self, benchmark: BenchmarkResult, judge_results: dict[str, JudgeResult]
    ) -> str:
        lines = ["## Cost Efficiency\n"]
        header = "| Mode | Total Cost | Mean Score | Score/Dollar |"
        sep = "|------|----------:|-----------:|------------:|"
        lines.extend([header, sep])

        mode_means = _compute_mode_means(judge_results)
        mode_costs: dict[str, float] = {}
        for q_results in benchmark.results.values():
            for mode, mr in q_results.items():
                mode_costs[mode] = mode_costs.get(mode, 0) + mr.cost

        for mode in ["single", "context", "synthesize", "debate", "negotiate"]:
            cost = mode_costs.get(mode, 0)
            mean = mode_means.get(mode, 0)
            spd = mean / cost if cost > 0 else 0
            label = MODE_LABELS.get(mode, mode)
            lines.append(f"| {label} | ${cost:.2f} | {mean:.2f} | {spd:.1f} |")

        return "\n".join(lines)

    def _render_structural_metrics(self, benchmark: BenchmarkResult) -> str:
        lines = ["## Structural Metrics (Debate/Negotiate Only)\n"]
        header = "| Question | Mode | Nodes | Revisions | Constraints |"
        sep = "|----------|------|------:|----------:|------------:|"
        lines.extend([header, sep])

        for q_id, q_results in benchmark.results.items():
            for mode in ["debate", "negotiate"]:
                if mode not in q_results:
                    continue
                mr = q_results[mode]
                tm = mr.trace_metrics
                label = MODE_LABELS.get(mode, mode)
                lines.append(
                    f"| {q_id} | {label} | "
                    f"{tm.get('node_count', 0)} | "
                    f"{tm.get('revision_count', 0)} | "
                    f"{tm.get('constraint_count', 0)} |"
                )

        return "\n".join(lines)

    def _render_ranking_summary(self, judge_results: dict[str, JudgeResult]) -> str:
        lines = ["## Forced Ranking Summary\n"]
        lines.append("Which response would you present to a $15M company's CEO?\n")

        # Count first-place finishes per mode
        first_place: dict[str, int] = {}
        for jr in judge_results.values():
            if jr.ranking:
                winner = jr.ranking[0]
                first_place[winner] = first_place.get(winner, 0) + 1

        header = "| Mode | First-Place Wins |"
        sep = "|------|----------------:|"
        lines.extend([header, sep])

        for mode in ["single", "context", "synthesize", "debate", "negotiate"]:
            label = MODE_LABELS.get(mode, mode)
            wins = first_place.get(mode, 0)
            lines.append(f"| {label} | {wins} |")

        return "\n".join(lines)

    def _render_per_question(
        self, benchmark: BenchmarkResult, judge_results: dict[str, JudgeResult]
    ) -> str:
        lines = ["## Per-Question Results\n"]

        for q_id, q_results in benchmark.results.items():
            lines.append(f"### Question: {q_id}\n")

            jr = judge_results.get(q_id)
            if not jr:
                lines.append("_No judge scores available._\n")
                continue

            # Mini score table
            header = "| Mode | Score | Cost | Duration |"
            sep = "|------|------:|-----:|---------:|"
            lines.extend([header, sep])

            for mode, mr in q_results.items():
                label = MODE_LABELS.get(mode, mode)
                scores = jr.scores.get(mode, {})
                mean = sum(scores.values()) / len(scores) if scores else 0
                lines.append(
                    f"| {label} | {mean:.2f} | ${mr.cost:.2f} | {mr.duration_seconds:.0f}s |"
                )

            if jr.ranking:
                ranked = ' > '.join(MODE_LABELS.get(m, m) for m in jr.ranking)
                lines.append(f"\n**Ranking:** {ranked}")
            if jr.judge_reasoning:
                lines.append(f"\n**Judge notes:** {jr.judge_reasoning}")
            lines.append("")

        return "\n".join(lines)

    def _render_methodology(self) -> str:
        return """## Methodology

- **5 execution modes** compared: single, single+context, synthesis, debate, negotiate
- **7 evaluation dimensions** scored 1-5 by a blind Opus judge
- Outputs anonymized and randomized before judging
- Dimensions 2-4 (consistency, tension, constraints) hypothesized to favor multi-agent
- Cost calculated using February 2026 Anthropic pricing

*Generated by C-Suite Evaluation Framework*"""


def _compute_mode_means(judge_results: dict[str, JudgeResult]) -> dict[str, float]:
    """Compute mean score per mode across all questions and dimensions."""
    agg: dict[str, list[float]] = {}
    for jr in judge_results.values():
        for mode, dim_scores in jr.scores.items():
            agg.setdefault(mode, []).extend(dim_scores.values())
    return {mode: sum(s) / len(s) for mode, s in agg.items() if s}
