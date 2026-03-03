"""Emergence Certificate Generator — client-facing quality proof for protocol outputs.

Produces a structured certification document showing that a multi-agent coordination
protocol achieved genuine emergent properties (Zone D) that no single agent could produce.

Usage:
    # From evaluation result JSON:
    python scripts/emergence_certificate.py evaluations/emergence/pair7_Q2.1_*.json

    # From a live protocol run:
    python scripts/emergence_certificate.py \
        --protocol p04_multi_round_debate \
        --question "Should we expand into Europe?" \
        --agents ceo cfo cto \
        --baseline p03_parallel_synthesis
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def generate_certificate(result: dict, output_format: str = "markdown") -> str:
    """Generate a client-facing emergence certificate from an EmergenceResult dict."""

    complex_scores = result.get("complex_scores", {})
    baseline_scores = result.get("baseline_scores", {})

    concrete = complex_scores.get("concrete_composite", 0)
    perceptual = complex_scores.get("perceptual_composite", 0)
    zone = complex_scores.get("zone", "A")
    zone_transition = result.get("zone_transition", "?->?")

    baseline_zone = baseline_scores.get("zone", "A")
    baseline_concrete = baseline_scores.get("concrete_composite", 0)
    baseline_perceptual = baseline_scores.get("perceptual_composite", 0)

    # Zone descriptions
    zone_labels = {
        "A": "Insufficient Emergence — output not meaningfully different from single-agent",
        "B": "Operational Emergence — actionable multi-perspective synthesis achieved",
        "C": "Conceptual Emergence — novel insights generated but not operationally executable",
        "D": "Full Emergence — both novel insights AND actionable synthesis achieved",
    }

    # Score breakdown
    scores = complex_scores.get("scores", {})
    concrete_items = {k: v for k, v in scores.items() if k.startswith("C")}
    perceptual_items = {k: v for k, v in scores.items() if k.startswith("P")}

    criterion_labels = {
        "C1": "Structural Novelty",
        "C2": "Epistemic Breadth",
        "C3": "Constraints Surfaced",
        "C4": "Implementation Readiness",
        "C5": "Trade-off Clarity",
        "C6": "Failure Modes Identified",
        "P1": "Coherence",
        "P2": "Stakeholder Value Proposition",
        "P3": "Systems Thinking Depth",
        "P4": "Intellectual Humility",
        "P5": "Actionability",
        "P6": "Narrative Integration",
    }

    # Build certificate
    protocol = result.get("complex_protocol", "Unknown Protocol")
    baseline = result.get("baseline_protocol", "Single-Agent Baseline")
    question = result.get("question", "")
    timestamp = result.get("timestamp", datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))

    lines = []
    lines.append("# Emergence Quality Certificate")
    lines.append("")
    lines.append(f"**Date**: {timestamp[:8]}")
    lines.append(f"**Protocol**: {protocol}")
    lines.append(f"**Baseline**: {baseline}")
    lines.append(f"**Question**: {question[:200]}")
    lines.append("")

    # Zone classification (the headline)
    lines.append("---")
    lines.append("")
    lines.append(f"## Classification: Zone {zone}")
    lines.append(f"**{zone_labels.get(zone, 'Unknown')}**")
    lines.append("")
    lines.append(f"- Concrete Composite: **{concrete:.2f}** / 4.00")
    lines.append(f"- Perceptual Composite: **{perceptual:.2f}** / 4.00")
    lines.append(f"- Zone Transition: {zone_transition} (baseline {baseline_zone} → protocol {zone})")
    lines.append("")

    # Improvement over baseline
    concrete_delta = concrete - baseline_concrete
    perceptual_delta = perceptual - baseline_perceptual
    lines.append("## Improvement Over Baseline")
    lines.append("")
    lines.append("| Dimension | Baseline | Protocol | Delta |")
    lines.append("|-----------|----------|----------|-------|")
    lines.append(f"| Concrete | {baseline_concrete:.2f} | {concrete:.2f} | {'+' if concrete_delta >= 0 else ''}{concrete_delta:.2f} |")
    lines.append(f"| Perceptual | {baseline_perceptual:.2f} | {perceptual:.2f} | {'+' if perceptual_delta >= 0 else ''}{perceptual_delta:.2f} |")
    lines.append("")

    # Detailed scores
    lines.append("## Detailed Scores")
    lines.append("")
    lines.append("### Concrete Criteria (operational quality)")
    lines.append("")
    lines.append("| Criterion | Score | Description |")
    lines.append("|-----------|-------|-------------|")
    for k in sorted(concrete_items.keys()):
        v = concrete_items[k]
        score = v.get("score", 0) if isinstance(v, dict) else v
        label = criterion_labels.get(k, k)
        lines.append(f"| {k} | {score:.1f}/4 | {label} |")
    lines.append("")

    lines.append("### Perceptual Criteria (insight quality)")
    lines.append("")
    lines.append("| Criterion | Score | Description |")
    lines.append("|-----------|-------|-------------|")
    for k in sorted(perceptual_items.keys()):
        v = perceptual_items[k]
        score = v.get("score", 0) if isinstance(v, dict) else v
        label = criterion_labels.get(k, k)
        lines.append(f"| {k} | {score:.1f}/4 | {label} |")
    lines.append("")

    # Coordination indicators
    indicators = result.get("coordination_indicators", {})
    if indicators:
        lines.append("## Coordination Indicators")
        lines.append("")
        for k, v in indicators.items():
            status = "Present" if v else "Absent"
            lines.append(f"- **{k.replace('_', ' ').title()}**: {status}")
        lines.append("")

    # Judge reasoning
    reasoning = result.get("judge_reasoning", "")
    if reasoning:
        lines.append("## Judge Assessment")
        lines.append("")
        lines.append(reasoning)
        lines.append("")

    # What this means (client-facing explanation)
    lines.append("---")
    lines.append("")
    lines.append("## What This Means")
    lines.append("")
    if zone == "D":
        lines.append("This recommendation achieved **Full Emergence** — the multi-agent coordination")
        lines.append("produced insights and actionable recommendations that no single perspective could")
        lines.append("generate independently. The output reflects genuine synthesis across multiple")
        lines.append("expert viewpoints, with both novel strategic framing AND executable specificity.")
    elif zone == "B":
        lines.append("This recommendation achieved **Operational Emergence** — the multi-agent process")
        lines.append("produced actionable, well-coordinated recommendations with strong operational")
        lines.append("specificity. The strategic framing could be deeper, but the output is immediately")
        lines.append("executable.")
    elif zone == "C":
        lines.append("This recommendation achieved **Conceptual Emergence** — the multi-agent process")
        lines.append("produced novel strategic insights and reframings. However, the output needs")
        lines.append("additional operationalization to be directly executable.")
    else:
        lines.append("This recommendation did not achieve measurable emergence above a single-agent")
        lines.append("baseline. The coordination protocol may not be the right fit for this question type.")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate Emergence Quality Certificate")
    parser.add_argument(
        "result_file",
        nargs="?",
        help="Path to emergence result JSON file",
    )
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument(
        "--format", choices=["markdown", "json"], default="markdown",
        help="Output format",
    )
    args = parser.parse_args()

    if not args.result_file:
        # List available results
        emergence_dir = ROOT / "evaluations" / "emergence"
        if emergence_dir.exists():
            files = sorted(emergence_dir.glob("pair*.json"))
            if files:
                print("Available emergence results:")
                for f in files:
                    print(f"  {f.name}")
                print(f"\nUsage: python scripts/emergence_certificate.py {files[0]}")
            else:
                print("No emergence results found in evaluations/emergence/")
        else:
            print("No evaluations/emergence/ directory found.")
        sys.exit(0)

    result_path = Path(args.result_file)
    if not result_path.exists():
        print(f"File not found: {result_path}")
        sys.exit(1)

    result = json.loads(result_path.read_text())

    if args.format == "json":
        # Add certificate metadata to the result
        result["certificate_generated"] = datetime.now(timezone.utc).isoformat()
        result["certificate_zone_label"] = {
            "A": "Insufficient Emergence",
            "B": "Operational Emergence",
            "C": "Conceptual Emergence",
            "D": "Full Emergence",
        }.get(result.get("complex_scores", {}).get("zone", "A"), "Unknown")
        output = json.dumps(result, indent=2)
    else:
        output = generate_certificate(result)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Certificate saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
