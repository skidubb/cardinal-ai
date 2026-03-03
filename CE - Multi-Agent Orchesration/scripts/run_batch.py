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
import json
import time
import traceback
from dataclasses import asdict, is_dataclass
from pathlib import Path

import anthropic

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

    run_data = {
        "protocol_id": pid,
        "protocol_name": config["name"],
        "category": config["category"],
        "question": config["question"],
        "elapsed_seconds": round(elapsed, 1),
        "timings": timings,
        "result": result,
        "agent_model": agent_model or "anthropic-default",
    }

    # Persist raw results so reports can be regenerated without re-running protocols
    raw_path = Path("smoke-tests") / f"{pid}_raw_result.json"
    raw_path.parent.mkdir(exist_ok=True)
    serialized = _serialize_result(result)
    raw_json = {k: v for k, v in run_data.items() if k != "result"}
    raw_json["raw_output"] = serialized
    raw_path.write_text(json.dumps(raw_json, indent=2, default=str))
    print(f"  Raw result saved: {raw_path}")

    return run_data


def _serialize_result(obj, depth: int = 0) -> str:
    """Deep-serialize a protocol result dataclass to readable text for the report LLM."""
    if depth > 4:
        return str(obj)[:500]
    if is_dataclass(obj) and not isinstance(obj, type):
        lines = []
        for k, v in asdict(obj).items():
            lines.append(f"{k}: {_serialize_result(v, depth + 1)}")
        return "\n".join(lines)
    if isinstance(obj, dict):
        lines = []
        for k, v in obj.items():
            lines.append(f"{k}: {_serialize_result(v, depth + 1)}")
        return "\n".join(lines)
    if isinstance(obj, list):
        if not obj:
            return "[]"
        items = []
        for i, v in enumerate(obj):
            items.append(f"[{i}] {_serialize_result(v, depth + 1)}")
        return "\n".join(items)
    if isinstance(obj, tuple):
        return str(obj)
    return str(obj)


REPORT_PROMPT = """You are writing a synthesis report for a multi-agent coordination protocol run.
Your report will be published as a professional deliverable. It must be deeply analytical,
narrative-driven, and demonstrate the value of multi-agent reasoning.

## Protocol Details

**Protocol**: {protocol_id} — {protocol_name}
**Category**: {category}
**Question**: {question}
**Agents**: {agents}
**Total Runtime**: {elapsed}s
**Agent Model**: {agent_model}

## Protocol Description

{protocol_description}

## Phase Timings

{timings_block}

## Full Protocol Output (raw data from all phases)

{raw_output}

## Report Requirements

Write a comprehensive synthesis report in markdown following this EXACT structure.
Every section must contain substantive analytical content — not just restating data.

### Required Sections:

1. **Header block** — Protocol name, question, agents, runtime, date (today is 2026-03-03)

2. **How the Protocol Worked** — Describe each phase: what happened, which model tier was used
   (Opus for reasoning, Haiku for mechanical), how agents operated (parallel vs sequential),
   and include a timing table.

3. **Agent Contributions: Where They Converged and Diverged** — This is the MOST IMPORTANT section.
   Go phase by phase. For each phase where agents contributed:
   - What did each agent uniquely bring based on their role (CEO=strategy, CFO=economics, CTO=tech, CMO=market)?
   - Where did agents independently arrive at the same conclusion? (convergence = strong signal)
   - Where did they fundamentally disagree? (divergence = interesting tension)
   - What did one agent surface that no other did? (unique contribution)
   - Use specific examples from the raw data — quote or reference actual outputs.

4. **The Core Insight** — What is the single most important finding? Frame it as an executive-ready
   insight. If possible, identify something that emerged from the MULTI-agent process that no
   single agent would have produced alone.

5. **Emergent Properties** — What analytical value came from running multiple agents through this
   specific protocol structure? How did the protocol's mechanics (elimination, voting, sequential
   building, adversarial testing, etc.) produce insights beyond simple aggregation?

6. **Recommended Actions** — 3-5 concrete, specific next steps for Cardinal Element based on findings.

7. **Protocol Performance Assessment** — How well did this protocol work for this question type?
   Strengths, weaknesses, and whether you'd recommend this protocol for similar questions.

### Quality Standards:
- Minimum 1500 words
- Use specific data points and quotes from the raw output
- Every claim must be traceable to the protocol data
- Write in analytical prose, not bullet-point summaries
- The report should be publishable as a standalone strategic analysis document
"""

PROTOCOL_DESCRIPTIONS = {
    "p16": "ACH (Analysis of Competing Hypotheses): Agents generate hypotheses in parallel, then independently list evidence. A matrix scores each evidence item against each hypothesis (Consistent/Inconsistent/Neutral). Hypotheses with the most inconsistencies are eliminated. Surviving hypotheses undergo sensitivity analysis.",
    "p17": "Red/Blue/White Team: Adversarial stress-testing. Red team agents independently attack a plan (identify vulnerabilities). Blue team agents defend (propose mitigations). White team agent adjudicates each vulnerability — is the defense adequate? Final assessment scores plan strength and identifies open risks.",
    "p18": "Delphi Method: Iterative expert estimation. Round 1: agents independently estimate. Statistics computed (median, IQR). Round 2+: agents see anonymous group stats and reasoning, then revise. Converges when IQR < 15% of median. Final synthesis explains convergence/divergence patterns.",
    "p19": "Vickrey Auction (Second-Price Sealed-Bid): Agents independently select an option and bid confidence (0-100). Winner is highest bidder but 'pays' the second-highest bid (calibrated justification at that confidence level). Reveals true preference intensity and consensus.",
    "p20": "Borda Count: Ranked-choice voting. Each agent independently ranks all options with reasoning. Borda scoring (1st = K-1 points, last = 0). Ties broken by Condorcet head-to-head comparison. Final report analyzes voting patterns and reasoning clusters.",
    "p21": "Interests-Based Negotiation: Phase 1 surfaces each agent's underlying interests (needs, fears, aspirations). Phase 2 categorizes as shared/compatible/conflicting. Phase 3 generates mutual-gains options. Phase 4 scores options against all agents' interests and checks Pareto-optimality. Phase 5 synthesizes agreement.",
    "p22": "Sequential Pipeline: Agents process in strict sequence — each receives the question plus ALL prior agents' outputs. Agent 1 sets the frame, Agent 2 builds on it, etc. Quality gate checks coherence. Final synthesis integrates all stage contributions.",
    "p23": "Cynefin Probe-Sense-Respond: Each agent independently classifies the situation into a Cynefin domain (Clear/Complicated/Complex/Chaotic/Confused). Consensus determined by majority vote. Then agents apply the domain-appropriate decision approach. Synthesis produces an action plan.",
    "p24": "Causal Loop Mapping: Phase 1 extracts system variables (parallel). Phase 2 deduplicates. Phase 3 identifies causal links with polarity (+/-) between variables. Phase 4 computationally traces feedback loops (reinforcing and balancing). Phase 5 analyzes leverage points.",
    "p25": "System Archetype Detection: Agents observe dynamics/patterns. Merged and deduplicated. Each agent matches observations against known system archetypes (Fixes That Fail, Shifting the Burden, Limits to Growth, etc.) with confidence scores. Synthesis identifies best matches and recommends archetype-specific interventions.",
}


async def generate_report(run_data: dict, output_dir: Path) -> Path:
    """Generate a deep narrative synthesis report using Opus."""
    pid = run_data["protocol_id"]
    name = run_data["protocol_name"]
    result = run_data["result"]
    timings = run_data["timings"]

    print(f"  Generating synthesis report for {pid}...")

    # Serialize the full result
    raw_output = _serialize_result(result)
    # Truncate if enormous (keep first 12K chars to fit in context)
    if len(raw_output) > 12000:
        raw_output = raw_output[:12000] + f"\n\n... [truncated — full output was {len(raw_output)} chars]"

    # Build timings block
    timings_block = ""
    if timings:
        timings_block = "\n".join(f"- {phase}: {duration:.1f}s" for phase, duration in timings.items())
    else:
        timings_block = "(no phase timings available)"

    # Build agent list from result
    agents_str = "CEO, CFO, CTO, CMO"  # default
    if hasattr(result, "agents") and result.agents:
        agents_str = ", ".join(a.get("name", "?") for a in result.agents)

    prompt = REPORT_PROMPT.format(
        protocol_id=pid.upper(),
        protocol_name=name,
        category=run_data["category"],
        question=run_data["question"],
        agents=agents_str,
        elapsed=run_data["elapsed_seconds"],
        agent_model=run_data["agent_model"],
        protocol_description=PROTOCOL_DESCRIPTIONS.get(pid, "Multi-agent coordination protocol."),
        timings_block=timings_block,
        raw_output=raw_output,
    )

    client = anthropic.AsyncAnthropic()
    resp = await client.messages.create(
        model="claude-opus-4-6",
        max_tokens=16384,
        thinking={"type": "enabled", "budget_tokens": 10000},
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract text from response
    report_text = ""
    for block in resp.content:
        if hasattr(block, "text"):
            report_text += block.text

    # Write report
    report_name = f"{pid}_{name.lower().replace('/', '_').replace(' ', '_')}_synthesis_report.md"
    report_path = output_dir / report_name
    report_path.write_text(report_text)
    print(f"  Report saved: {report_path} ({len(report_text)} chars)")
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
        "--mode", choices=["research", "production"], default=None,
        help="Agent mode: research (lightweight dicts) or production (real SDK agents). Default: production (override with AGENT_MODE env var).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would run without executing.",
    )
    args = parser.parse_args()

    agents = build_agents(args.agents, mode=args.mode)
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
            report_path = await generate_report(run_data, output_dir)
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
