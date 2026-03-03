#!/usr/bin/env python3
"""Batch runner for P16-P25 protocols with synthesis report generation.

Usage:
    python scripts/run_batch.py
    python scripts/run_batch.py --agent-model "gemini/gemini-3.1-pro-preview"
    python scripts/run_batch.py --protocols p16 p17 p20
    python scripts/run_batch.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import time
import traceback
from pathlib import Path

from protocols.agents import build_agents

# ---------------------------------------------------------------------------
# Protocol definitions
# ---------------------------------------------------------------------------

PROTOCOL_CONFIGS = [
    {
        "id": "p16",
        "name": "ACH",
        "module": "protocols.p16_ach.orchestrator",
        "class": "ACHOrchestrator",
        "question": "What is the most likely reason our enterprise pipeline has stalled — market timing, pricing, competition, or product-market fit?",
        "category": "Intelligence Analysis",
    },
    {
        "id": "p17",
        "name": "Red/Blue/White Team",
        "module": "protocols.p17_red_blue_white.orchestrator",
        "class": "RedBlueWhiteOrchestrator",
        "question": "How vulnerable is our AI consulting model to disruption by hyperscaler bundling?",
        "plan": "Cardinal Element will differentiate through bespoke multi-agent orchestration IP, deep vertical expertise, and white-glove implementation services that hyperscalers cannot replicate at scale.",
        "category": "Intelligence Analysis",
    },
    {
        "id": "p18",
        "name": "Delphi Method",
        "module": "protocols.p18_delphi_method.orchestrator",
        "class": "DelphiOrchestrator",
        "question": "What will the AI consulting market look like in 24 months?",
        "category": "Intelligence Analysis",
    },
    {
        "id": "p19",
        "name": "Vickrey Auction",
        "module": "protocols.p19_vickrey_auction.orchestrator",
        "class": "VickreyOrchestrator",
        "question": "Which of our three service lines (audits, implementations, training) deserves the next $100K investment?",
        "options": ["Growth Architecture Audits", "AI Implementation Services", "Executive AI Training Programs"],
        "category": "Game Theory",
    },
    {
        "id": "p20",
        "name": "Borda Count",
        "module": "protocols.p20_borda_count.orchestrator",
        "class": "BordaCountOrchestrator",
        "question": "Rank our expansion options: vertical SaaS, geographic expansion, partner program, or productized IP",
        "options": ["Vertical SaaS Product", "Geographic Expansion", "Partner Program", "Productized IP"],
        "category": "Game Theory",
    },
    {
        "id": "p21",
        "name": "Interests Negotiation",
        "module": "protocols.p21_interests_negotiation.orchestrator",
        "class": "InterestsNegotiationOrchestrator",
        "question": "How should we split resources between landing new clients vs. expanding existing accounts?",
        "category": "Game Theory",
    },
    {
        "id": "p22",
        "name": "Sequential Pipeline",
        "module": "protocols.p22_sequential_pipeline.orchestrator",
        "class": "SequentialPipelineOrchestrator",
        "question": "Design our ideal client onboarding process from first call to kickoff",
        "category": "Org Theory",
    },
    {
        "id": "p23",
        "name": "Cynefin Probe",
        "module": "protocols.p23_cynefin_probe.orchestrator",
        "class": "CynefinOrchestrator",
        "question": "How should we handle the growing demand for AI governance consulting?",
        "category": "Org Theory",
    },
    {
        "id": "p24",
        "name": "Causal Loop Mapping",
        "module": "protocols.p24_causal_loop_mapping.orchestrator",
        "class": "CausalLoopOrchestrator",
        "question": "What feedback loops drive our client retention and expansion?",
        "category": "Systems Thinking",
    },
    {
        "id": "p25",
        "name": "System Archetype Detection",
        "module": "protocols.p25_system_archetype_detection.orchestrator",
        "class": "ArchetypeDetector",
        "question": "What systemic patterns explain why our best clients eventually churn?",
        "category": "Systems Thinking",
    },
]


def _import_class(module_path: str, class_name: str):
    """Dynamically import an orchestrator class."""
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


async def run_protocol(config: dict, agents: list[dict], agent_model: str | None) -> dict:
    """Run a single protocol and return results dict."""
    pid = config["id"]
    print(f"\n{'='*60}")
    print(f"  Running {pid.upper()}: {config['name']}")
    print(f"  Category: {config['category']}")
    print(f"  Question: {config['question'][:80]}...")
    print(f"{'='*60}")

    # Apply agent model if specified
    run_agents = [dict(a) for a in agents]  # shallow copy
    if agent_model:
        for a in run_agents:
            a["model"] = agent_model

    cls = _import_class(config["module"], config["class"])
    t0 = time.time()

    # Each protocol has a slightly different constructor/run signature
    if pid == "p17":
        # Red/Blue/White has separate agent groups
        mid = len(run_agents) // 2
        orchestrator = cls(
            red_agents=run_agents[:mid],
            blue_agents=run_agents[mid:],
            white_agent=run_agents[0],
        )
        result = await orchestrator.run(config["question"], config["plan"])
    elif pid == "p19":
        orchestrator = cls(agents=run_agents)
        result = await orchestrator.run(config["question"], config["options"])
    elif pid == "p20":
        orchestrator = cls(agents=run_agents)
        result = await orchestrator.run(config["question"], config["options"])
    elif pid == "p22":
        orchestrator = cls()
        result = await orchestrator.run(config["question"], run_agents)
    else:
        orchestrator = cls(agents=run_agents)
        result = await orchestrator.run(config["question"])

    elapsed = time.time() - t0
    print(f"  Completed in {elapsed:.1f}s")

    # Extract timings from result if available
    timings = {}
    if hasattr(result, "timings"):
        timings = result.timings

    return {
        "protocol_id": pid,
        "protocol_name": config["name"],
        "category": config["category"],
        "question": config["question"],
        "elapsed_seconds": round(elapsed, 1),
        "timings": timings,
        "result": result,
        "agent_model": agent_model or "anthropic-default",
    }


def generate_report(run_data: dict, output_dir: Path) -> Path:
    """Generate a synthesis report for a single protocol run."""
    pid = run_data["protocol_id"]
    name = run_data["protocol_name"]
    result = run_data["result"]
    timings = run_data["timings"]

    report_lines = [
        f"# {pid.upper()}: {name} — Synthesis Report",
        "",
        f"**Category:** {run_data['category']}",
        f"**Question:** {run_data['question']}",
        f"**Agent Model:** {run_data['agent_model']}",
        f"**Total Time:** {run_data['elapsed_seconds']}s",
        "",
        "---",
        "",
        "## Protocol Execution",
        "",
    ]

    # Phase timings
    if timings:
        report_lines.append("### Phase Timings")
        report_lines.append("")
        report_lines.append("| Phase | Duration |")
        report_lines.append("|-------|----------|")
        for phase, duration in timings.items():
            report_lines.append(f"| {phase} | {duration:.1f}s |")
        report_lines.append("")

    # Protocol-specific content
    report_lines.append("## Key Findings")
    report_lines.append("")

    if hasattr(result, "synthesis") and result.synthesis:
        syn = result.synthesis
        if isinstance(syn, dict):
            if syn.get("conclusion"):
                report_lines.append(f"**Conclusion:** {syn['conclusion']}")
                report_lines.append("")
            if syn.get("confidence"):
                report_lines.append(f"**Confidence:** {syn['confidence']}")
                report_lines.append("")
            if syn.get("key_uncertainties"):
                report_lines.append("**Key Uncertainties:**")
                for u in syn["key_uncertainties"]:
                    report_lines.append(f"- {u}")
                report_lines.append("")

    if hasattr(result, "surviving") and result.surviving:
        report_lines.append("### Surviving Hypotheses")
        for h in result.surviving:
            label = h.label if hasattr(h, "label") else str(h)
            report_lines.append(f"- {label}")
        report_lines.append("")

    if hasattr(result, "action_plan") and result.action_plan:
        report_lines.append("### Action Plan")
        ap = result.action_plan
        if isinstance(ap, dict):
            for k, v in ap.items():
                report_lines.append(f"**{k}:** {v}")
                report_lines.append("")

    if hasattr(result, "final_output") and result.final_output:
        report_lines.append("### Final Output")
        report_lines.append("")
        report_lines.append(result.final_output[:2000])
        report_lines.append("")

    if hasattr(result, "winner") and result.winner:
        report_lines.append(f"**Winner:** {result.winner}")
        if hasattr(result, "winning_option"):
            report_lines.append(f"**Winning Option:** {result.winning_option}")
        report_lines.append("")

    if hasattr(result, "final_ranking") and result.final_ranking:
        report_lines.append("### Final Ranking")
        for i, opt in enumerate(result.final_ranking, 1):
            score = ""
            if hasattr(result, "borda_scores") and result.borda_scores:
                score = f" ({result.borda_scores.get(opt, 0)} pts)"
            report_lines.append(f"{i}. {opt}{score}")
        report_lines.append("")

    if hasattr(result, "leverage_points") and result.leverage_points:
        report_lines.append("### Leverage Points")
        lp = result.leverage_points
        if isinstance(lp, dict):
            for k, v in lp.items():
                report_lines.append(f"**{k}:** {v}")
                report_lines.append("")

    if hasattr(result, "best_matches") and result.best_matches:
        report_lines.append("### Best Archetype Matches")
        for m in result.best_matches:
            archetype = m.archetype if hasattr(m, "archetype") else str(m)
            score = m.score if hasattr(m, "score") else ""
            report_lines.append(f"- **{archetype}** (score: {score})")
            if hasattr(m, "reasoning") and m.reasoning:
                report_lines.append(f"  {m.reasoning[:200]}")
        report_lines.append("")

    if hasattr(result, "recommendations") and result.recommendations:
        report_lines.append("### Recommendations")
        for i, rec in enumerate(result.recommendations, 1):
            report_lines.append(f"{i}. {rec}")
        report_lines.append("")

    # Footer
    report_lines.extend([
        "---",
        "",
        f"*Generated by CE Multi-Agent Orchestration batch runner*",
    ])

    # Write report
    report_name = f"{pid}_{name.lower().replace('/', '_').replace(' ', '_')}_synthesis_report.md"
    report_path = output_dir / report_name
    report_path.write_text("\n".join(report_lines))
    print(f"  Report saved: {report_path}")
    return report_path


async def main() -> None:
    parser = argparse.ArgumentParser(description="Batch runner for P16-P25 protocols")
    parser.add_argument(
        "--protocols", "-p", nargs="+", default=None,
        help="Specific protocol IDs to run (e.g., p16 p17 p20). Default: all P16-P25.",
    )
    parser.add_argument(
        "--agents", "-a", nargs="+", default=["ceo", "cfo", "cto", "cmo"],
        help="Agent keys to use (default: ceo cfo cto cmo).",
    )
    parser.add_argument(
        "--agent-model", default=None,
        help="Override LLM model for all agents (e.g., 'gemini/gemini-3.1-pro-preview').",
    )
    parser.add_argument(
        "--output-dir", "-o", default="smoke-tests",
        help="Output directory for reports (default: smoke-tests).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would run without executing.",
    )
    args = parser.parse_args()

    agents = build_agents(args.agents)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Filter protocols
    configs = PROTOCOL_CONFIGS
    if args.protocols:
        selected = {p.lower() for p in args.protocols}
        configs = [c for c in configs if c["id"] in selected]

    if args.dry_run:
        print("DRY RUN — would execute:")
        for c in configs:
            print(f"  {c['id']}: {c['name']} — {c['question'][:60]}...")
        print(f"\nAgents: {[a['name'] for a in agents]}")
        print(f"Agent model: {args.agent_model or 'default (Anthropic)'}")
        return

    print(f"Running {len(configs)} protocols with agents: {[a['name'] for a in agents]}")
    if args.agent_model:
        print(f"Agent model override: {args.agent_model}")

    results = []
    for config in configs:
        try:
            run_data = await run_protocol(config, agents, args.agent_model)
            report_path = generate_report(run_data, output_dir)
            results.append({"protocol": config["id"], "status": "ok", "time": run_data["elapsed_seconds"], "report": str(report_path)})
        except Exception as e:
            print(f"  ERROR running {config['id']}: {e}")
            traceback.print_exc()
            results.append({"protocol": config["id"], "status": "error", "error": str(e)})

    # Summary
    print(f"\n{'='*60}")
    print("BATCH SUMMARY")
    print(f"{'='*60}")
    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"  Completed: {ok}/{len(configs)}")
    total_time = sum(r.get("time", 0) for r in results)
    print(f"  Total time: {total_time:.1f}s")
    for r in results:
        status = "OK" if r["status"] == "ok" else f"FAIL: {r.get('error', '?')}"
        time_str = f" ({r['time']:.1f}s)" if "time" in r else ""
        print(f"  {r['protocol']}: {status}{time_str}")


if __name__ == "__main__":
    asyncio.run(main())
