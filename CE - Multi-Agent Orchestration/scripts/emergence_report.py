#!/usr/bin/env python3
"""Aggregate emergence results and generate a markdown report.

Usage:
    python scripts/emergence_report.py
    python scripts/emergence_report.py > report.md
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMERGENCE_DIR = ROOT / "evaluations" / "emergence"


def load_results() -> list[dict]:
    """Load all emergence JSON files."""
    if not EMERGENCE_DIR.exists():
        return []
    results = []
    for f in sorted(EMERGENCE_DIR.glob("*.json")):
        try:
            results.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            print(f"Warning: skipping invalid JSON: {f.name}", file=sys.stderr)
    return results


def extract_pair_id(result: dict) -> str:
    """Extract pair ID from filename convention or protocol names."""
    cp = result.get("complex_protocol", "")
    bp = result.get("baseline_protocol", "")
    return f"{cp}_vs_{bp}"


def main() -> None:
    results = load_results()
    if not results:
        print("No emergence results found in evaluations/emergence/")
        return

    # Group by pair
    by_pair: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        pair_key = extract_pair_id(r)
        by_pair[pair_key].append(r)

    # Header
    print("# Emergence Detection Report")
    print()
    print(f"**Total evaluations**: {len(results)}")
    print(f"**Pairs evaluated**: {len(by_pair)}")
    print()

    # Zone distribution overall
    zones = defaultdict(int)
    transitions = defaultdict(int)
    for r in results:
        cs = r.get("complex_scores", {})
        bs = r.get("baseline_scores", {})
        zones[f"complex_{cs.get('zone', '?')}"] += 1
        zones[f"baseline_{bs.get('zone', '?')}"] += 1
        zt = r.get("zone_transition", "?->?")
        transitions[zt] += 1

    print("## Overall Zone Distribution")
    print()
    print("| Zone | Complex | Baseline |")
    print("|------|---------|----------|")
    for z in ["A", "B", "C", "D"]:
        print(f"| {z} | {zones.get(f'complex_{z}', 0)} | {zones.get(f'baseline_{z}', 0)} |")
    print()

    print("## Zone Transitions")
    print()
    print("| Transition | Count |")
    print("|------------|-------|")
    for t, c in sorted(transitions.items(), key=lambda x: -x[1]):
        marker = " **" if t.endswith("->D") else ""
        print(f"| {t}{marker} | {c} |")
    print()

    # Per-pair details
    print("## Per-Pair Results")
    print()
    for pair_key, pair_results in sorted(by_pair.items()):
        print(f"### {pair_key}")
        print()

        # Zone distribution
        pair_zones = defaultdict(int)
        concrete_deltas = []
        perceptual_deltas = []
        indicators = defaultdict(int)

        for r in pair_results:
            cs = r.get("complex_scores", {})
            bs = r.get("baseline_scores", {})
            pair_zones[cs.get("zone", "?")] += 1

            cc = cs.get("concrete_composite", 0)
            bc = bs.get("concrete_composite", 0)
            cp = cs.get("perceptual_composite", 0)
            bp = bs.get("perceptual_composite", 0)
            concrete_deltas.append(cc - bc)
            perceptual_deltas.append(cp - bp)

            for k, v in r.get("coordination_indicators", {}).items():
                if v:
                    indicators[k] += 1

        n = len(pair_results)
        mean_cd = sum(concrete_deltas) / n if n else 0
        mean_pd = sum(perceptual_deltas) / n if n else 0

        print(f"- **Questions**: {n}")
        print(f"- **Complex zone distribution**: {dict(pair_zones)}")
        print(f"- **Mean concrete delta**: {mean_cd:+.3f}")
        print(f"- **Mean perceptual delta**: {mean_pd:+.3f}")
        if indicators:
            print(f"- **Coordination indicators**: {', '.join(f'{k} ({v}/{n})' for k, v in sorted(indicators.items()))}")
        print()

        # Per-question table
        print("| Question | Complex Zone | Baseline Zone | Transition | Concrete Delta | Perceptual Delta |")
        print("|----------|-------------|---------------|------------|----------------|------------------|")
        for r in pair_results:
            qid = r.get("question_id", "?")
            cs = r.get("complex_scores", {})
            bs = r.get("baseline_scores", {})
            cz = cs.get("zone", "?")
            bz = bs.get("zone", "?")
            zt = r.get("zone_transition", "?->?")
            cd = cs.get("concrete_composite", 0) - bs.get("concrete_composite", 0)
            pd = cs.get("perceptual_composite", 0) - bs.get("perceptual_composite", 0)
            print(f"| {qid} | {cz} | {bz} | {zt} | {cd:+.3f} | {pd:+.3f} |")
        print()

    # Cross-pair summary: which protocol families produce Zone D
    print("## Protocol Families — Zone D Rates")
    print()
    protocol_zones = defaultdict(lambda: {"total": 0, "zone_d": 0})
    for r in results:
        cp = r.get("complex_protocol", "?")
        cs = r.get("complex_scores", {})
        protocol_zones[cp]["total"] += 1
        if cs.get("zone") == "D":
            protocol_zones[cp]["zone_d"] += 1

    print("| Protocol | Total | Zone D | Rate |")
    print("|----------|-------|--------|------|")
    for p, stats in sorted(protocol_zones.items(), key=lambda x: -x[1]["zone_d"]):
        rate = stats["zone_d"] / stats["total"] if stats["total"] else 0
        print(f"| {p} | {stats['total']} | {stats['zone_d']} | {rate:.0%} |")
    print()


if __name__ == "__main__":
    main()
