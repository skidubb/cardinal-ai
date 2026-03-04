#!/usr/bin/env python3
"""Batch runner for P26-P48 protocols with synthesis report generation.

Usage:
    python scripts/run_batch_p26_p48.py
    python scripts/run_batch_p26_p48.py --protocols p26 p30 p40
    python scripts/run_batch_p26_p48.py --agents ceo cfo cto cmo
    python scripts/run_batch_p26_p48.py --dry-run

NOTE: This script costs API tokens. Run only when ready.
Default mode is --mode research (lightweight dicts) for cost efficiency.
Use --mode production to run with full SDK agents.
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
# Protocol definitions — P26–P48
# ---------------------------------------------------------------------------
# Constructor signatures across this range follow three patterns:
#   A) cls(agents=agents, ...)                  — standard (most protocols)
#   B) cls(thinking_model=..., ...)             — no agents param (p35, p41, p42, p43, p47)
#   C) cls(agents=agents, num_cycles=N, ...)    — extra loop param (p40 OODA)
#
# The "no_agents" flag in configs below signals pattern B.
# Special extra kwargs are captured in "extra_kwargs".

PROTOCOL_CONFIGS = [
    # --- Design Thinking ---
    {
        "id": "p26",
        "name": "Crazy Eights",
        "module": "protocols.p26_crazy_eights.orchestrator",
        "class": "CrazyEightsOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Design Thinking",
    },
    {
        "id": "p27",
        "name": "Affinity Mapping",
        "module": "protocols.p27_affinity_mapping.orchestrator",
        "class": "AffinityMappingOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Design Thinking",
    },
    # --- Wave 2: Philosophical / Analytical Frameworks ---
    {
        "id": "p28",
        "name": "Six Hats",
        "module": "protocols.p28_six_hats.orchestrator",
        "class": "SixHatsOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
    },
    {
        "id": "p29",
        "name": "PMI Enumeration",
        "module": "protocols.p29_pmi_enumeration.orchestrator",
        "class": "PMIOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
    },
    {
        "id": "p30",
        "name": "Llull Combinatorial",
        "module": "protocols.p30_llull_combinatorial.orchestrator",
        "class": "CombinatorialOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
    },
    {
        "id": "p31",
        "name": "Wittgenstein Language Game",
        "module": "protocols.p31_wittgenstein_language_game.orchestrator",
        "class": "LanguageGameOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
    },
    {
        "id": "p32",
        "name": "Tetlock Forecast",
        "module": "protocols.p32_tetlock_forecast.orchestrator",
        "class": "TetlockOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
    },
    {
        "id": "p33",
        "name": "Evaporation Cloud",
        "module": "protocols.p33_evaporation_cloud.orchestrator",
        "class": "EvaporationCloudOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
    },
    {
        "id": "p34",
        "name": "Current Reality Tree",
        "module": "protocols.p34_current_reality_tree.orchestrator",
        "class": "CRTOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
    },
    {
        "id": "p35",
        "name": "Satisficing",
        "module": "protocols.p35_satisficing.orchestrator",
        "class": "SatisficingOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
        # SatisficingOrchestrator accepts agents as optional but works without them
        # (it uses a single LLM to evaluate sequential options)
    },
    {
        "id": "p36",
        "name": "Peirce Abduction",
        "module": "protocols.p36_peirce_abduction.orchestrator",
        "class": "AbductionOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
        "extra_kwargs": {"max_cycles": 3},
    },
    {
        "id": "p37",
        "name": "Hegel Sublation",
        "module": "protocols.p37_hegel_sublation.orchestrator",
        "class": "SublationOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
    },
    {
        "id": "p38",
        "name": "Klein Pre-Mortem",
        "module": "protocols.p38_klein_premortem.orchestrator",
        "class": "PreMortemOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
    },
    {
        "id": "p39",
        "name": "Popper Falsification",
        "module": "protocols.p39_popper_falsification.orchestrator",
        "class": "FalsificationOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
    },
    {
        "id": "p40",
        "name": "Boyd OODA",
        "module": "protocols.p40_boyd_ooda.orchestrator",
        "class": "OODAOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
        "extra_kwargs": {"num_cycles": 2},
    },
    {
        "id": "p41",
        "name": "Duke Decision Quality",
        "module": "protocols.p41_duke_decision_quality.orchestrator",
        "class": "DecisionQualityOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
        "no_agents": True,  # constructor: (thinking_model, orchestration_model, thinking_budget)
    },
    {
        "id": "p42",
        "name": "Aristotle Square",
        "module": "protocols.p42_aristotle_square.orchestrator",
        "class": "SquareOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
        "no_agents": True,
    },
    {
        "id": "p43",
        "name": "Leibniz Audit",
        "module": "protocols.p43_leibniz_audit.orchestrator",
        "class": "AuditChainOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
        "no_agents": True,
    },
    {
        "id": "p44",
        "name": "Kant Pre-Router",
        "module": "protocols.p44_kant_pre_router.orchestrator",
        "class": "KantRouterOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
        "no_agents": True,
    },
    {
        "id": "p45",
        "name": "Whitehead Weights",
        "module": "protocols.p45_whitehead_weights.orchestrator",
        "class": "WhiteheadOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
    },
    {
        "id": "p46",
        "name": "Incubation",
        "module": "protocols.p46_incubation.orchestrator",
        "class": "IncubationOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
    },
    {
        "id": "p47",
        "name": "Polya Lookback",
        "module": "protocols.p47_polya_lookback.orchestrator",
        "class": "LookBackOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
        "no_agents": True,
    },
    {
        "id": "p48",
        "name": "Black Swan Detection",
        "module": "protocols.p48_black_swan_detection.orchestrator",
        "class": "BlackSwanOrchestrator",
        "question": "Should Cardinal Element expand into the European market?",
        "category": "Wave 2 Research",
    },
]


# ---------------------------------------------------------------------------
# Protocol descriptions for synthesis report generation
# ---------------------------------------------------------------------------

PROTOCOL_DESCRIPTIONS = {
    "p26": (
        "Crazy Eights (Design Thinking): Agents independently generate 8 rapid-fire ideas each "
        "(timed, divergent). Ideas are clustered thematically. Agents dot-vote on the full pool. "
        "Top-voted ideas are developed into structured concept cards with rationale, risk, and next step."
    ),
    "p27": (
        "Affinity Mapping: Agents independently generate observations, insights, or data points. "
        "An orchestrator clusters them into affinity groups (themes). Agents label and discuss each "
        "cluster. Synthesis identifies key patterns, tensions, and actionable themes."
    ),
    "p28": (
        "Six Thinking Hats (de Bono): Agents cycle through six structured lenses — White (facts/data), "
        "Red (emotions/gut), Black (caution/risks), Yellow (optimism/benefits), Green (creative/alternatives), "
        "Blue (process/meta). Each agent contributes from each hat perspective. Synthesis integrates "
        "all six dimensions into a balanced assessment."
    ),
    "p29": (
        "PMI Enumeration (Plus/Minus/Interesting): Agents independently enumerate Plus (benefits), "
        "Minus (drawbacks), and Interesting (unexpected or nuanced) points. Points are deduplicated "
        "and weighted by frequency. Synthesis produces a balanced PMI scorecard with executive recommendation."
    ),
    "p30": (
        "Llull Combinatorial Association: Agents define concept 'disks' (categories with elements). "
        "The protocol exhaustively combines elements across disks. Agents evaluate each combination "
        "for non-obvious strategic value. Synthesis surfaces the highest-value novel combinations."
    ),
    "p31": (
        "Wittgenstein Language Game: Agents examine how different 'language games' (professional frames, "
        "industry jargon, stakeholder vocabularies) construct different meanings of the question. "
        "The protocol surfaces hidden assumptions embedded in word choices and reframes the question "
        "from multiple epistemic standpoints."
    ),
    "p32": (
        "Tetlock Superforecasting: Agents make calibrated probability forecasts on key uncertainties. "
        "They provide base rates, inside/outside view adjustments, and confidence intervals. "
        "Aggregation uses the Tetlock method (extremizing the mean). Synthesis produces a structured "
        "forecast with scenario probabilities and key driver analysis."
    ),
    "p33": (
        "Evaporation Cloud (Theory of Constraints): Agents identify the core conflict blocking the "
        "decision (two mutually exclusive requirements). The protocol maps: Objective → Requirement A "
        "+ Requirement B → Conflict. Agents challenge assumptions underlying each arrow to 'evaporate' "
        "the cloud and find a win-win resolution."
    ),
    "p34": (
        "Current Reality Tree (Theory of Constraints): Agents identify Undesirable Effects (UDEs). "
        "The protocol traces causal chains backward to identify the Root Cause (core problem driving "
        "most UDEs). Agents validate the tree and identify the critical constraint to address first."
    ),
    "p35": (
        "Simon Satisficing: Rather than optimizing, the protocol sets 'good-enough' criteria thresholds. "
        "Options are evaluated sequentially until one meets all thresholds (satisfices). This models "
        "bounded rationality — the first acceptable solution is chosen, not the global optimum. "
        "Synthesis reflects on what thresholds were set and what was accepted or rejected."
    ),
    "p36": (
        "Peirce Abduction: Agents generate surprising observations about the question domain. "
        "For each observation, agents abduce the most plausible explanation (best hypothesis). "
        "Hypotheses are tested against additional evidence across cycles. The protocol converges "
        "on the most parsimonious explanatory hypothesis."
    ),
    "p37": (
        "Hegel Sublation (Dialectic): Agents articulate a Thesis (dominant view), then an Antithesis "
        "(contradicting view). The protocol generates a Synthesis (Aufhebung) that preserves truth "
        "from both while resolving the contradiction at a higher level. Multiple dialectical rounds "
        "deepen the synthesis."
    ),
    "p38": (
        "Klein Pre-Mortem: Agents imagine the decision was implemented and failed catastrophically "
        "(one year forward). Each agent writes a failure narrative from their role's perspective. "
        "Failure modes are clustered and probability-weighted. Synthesis produces a risk-adjusted "
        "action plan with mitigation for highest-probability failure modes."
    ),
    "p39": (
        "Popper Falsification: Agents generate bold conjectures about the question. For each conjecture, "
        "agents attempt to falsify it — what evidence would prove it wrong? Tests are designed. "
        "Only un-falsified conjectures survive as actionable hypotheses. Synthesis ranks surviving "
        "conjectures by corroboration strength."
    ),
    "p40": (
        "Boyd OODA Loop: Agents cycle through Observe (gather relevant signals), Orient (interpret "
        "through mental models), Decide (select action), Act (specify implementation). Multiple OODA "
        "cycles run sequentially, each informed by the previous cycle's outcomes. Final synthesis "
        "produces a rapid-response action plan."
    ),
    "p41": (
        "Duke Decision Quality (Annie Duke): Frames decisions as bets, not outcomes. Evaluates: "
        "Frame (is the right question being asked?), Alternatives (are all options considered?), "
        "Information (what do we know/not know?), Values (what are we optimizing?), Reasoning "
        "(is logic sound?), Commitment (can we commit and adjust?). Scores each dimension 1-10."
    ),
    "p42": (
        "Aristotle Square of Opposition: Maps logical relationships between propositions about the "
        "question — Universal Affirmative, Universal Negative, Particular Affirmative, Particular "
        "Negative. Tests for contradiction, contrariety, subcontrariety, and subalternation. "
        "Identifies which propositions can simultaneously be true and surfaces logical tensions."
    ),
    "p43": (
        "Leibniz Audit Chain: A sequential chain of auditors, each reviewing the previous agent's "
        "reasoning for logical consistency, hidden assumptions, and gaps. Applies Leibniz's principle "
        "of sufficient reason — every conclusion must have adequate justification. Final synthesis "
        "produces a confidence-scored reasoning audit."
    ),
    "p44": (
        "Kant Pre-Router: Before running a complex protocol, applies Kantian categorical analysis — "
        "could this decision be universalized? What duties are implicated? What maxims are at play? "
        "Acts as a meta-protocol that routes to the most appropriate reasoning framework based on "
        "the ethical and epistemic structure of the question."
    ),
    "p45": (
        "Whitehead Process Weights: Applies Whitehead's process philosophy — reality as events, not "
        "substances. Agents weight the 'process' factors: creativity (novelty), conformity (inheritance "
        "from past), and aesthetic aim (satisfaction/value). Synthesis balances continuity with "
        "discontinuous innovation for the decision at hand."
    ),
    "p46": (
        "Incubation Protocol: Agents do not immediately answer. Instead, they: (1) load the problem "
        "into working memory with all known constraints, (2) 'incubate' by exploring analogous domains, "
        "metaphors, and lateral associations, (3) report insights that emerged from non-linear "
        "thinking. Synthesis synthesizes cross-domain insights into strategic recommendations."
    ),
    "p47": (
        "Polya Look-Back: Applies Polya's problem-solving heuristic in reverse — after generating a "
        "solution, agents look back to verify: Does it actually solve the problem? Can the reasoning "
        "be simplified? Can the method be generalized? What was learned? Produces a solution quality "
        "audit and generalizable insights."
    ),
    "p48": (
        "Black Swan Detection (Santa Fe Systems Thinking): Agents map causal graphs of the system. "
        "Threshold scans identify tipping points and phase transitions. Confluence scenarios find "
        "combinations of events that could cascade non-linearly. Historical analogues are surfaced. "
        "Adversarial memo summarizes the highest-probability black swan risks."
    ),
}


# ---------------------------------------------------------------------------
# Report prompt (same structure as run_batch.py for consistency)
# ---------------------------------------------------------------------------

REPORT_PROMPT = """You are writing a synthesis report for a multi-agent coordination protocol run.
Your report will be published as a professional deliverable. It must be deeply analytical,
narrative-driven, and demonstrate the value of multi-agent reasoning.

## Protocol Details

**Protocol**: {protocol_id} — {protocol_name}
**Category**: {category}
**Question**: {question}
**Agents**: {agents}
**Total Runtime**: {elapsed}s
**Agent Mode**: {agent_mode}

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
   and include a timing table if available.

3. **Agent Contributions: Where They Converged and Diverged** — This is the MOST IMPORTANT section.
   Go phase by phase. For each phase where agents contributed:
   - What did each agent uniquely bring based on their role (CEO=strategy, CFO=economics, CTO=tech)?
   - Where did agents independently arrive at the same conclusion? (convergence = strong signal)
   - Where did they fundamentally disagree? (divergence = interesting tension)
   - What did one agent surface that no other did? (unique contribution)
   - Use specific examples from the raw data — quote or reference actual outputs.

4. **The Core Insight** — What is the single most important finding? Frame it as an executive-ready
   insight. If possible, identify something that emerged from the MULTI-agent process that no
   single agent would have produced alone.

5. **Emergent Properties** — What analytical value came from running multiple agents through this
   specific protocol structure? How did the protocol's mechanics produce insights beyond simple aggregation?

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_class(module_path: str, class_name: str):
    """Dynamically import an orchestrator class."""
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


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


# ---------------------------------------------------------------------------
# Core run logic
# ---------------------------------------------------------------------------


async def run_protocol(config: dict, agents: list[dict], agent_mode: str) -> dict:
    """Run a single protocol and return a results dict."""
    pid = config["id"]
    print(f"\n{'='*60}")
    print(f"  Running {pid.upper()}: {config['name']}")
    print(f"  Category: {config['category']}")
    print(f"  Question: {config['question'][:80]}...")
    print(f"  Mode: {agent_mode}")
    print(f"{'='*60}")

    cls = _import_class(config["module"], config["class"])
    extra_kwargs = config.get("extra_kwargs", {})
    no_agents = config.get("no_agents", False)

    t0 = time.time()

    if no_agents:
        # Orchestrators that do not accept an agents list (single-LLM protocols)
        orchestrator = cls(**extra_kwargs)
    else:
        orchestrator = cls(agents=agents, **extra_kwargs)

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
        "agent_mode": agent_mode,
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


async def generate_report(run_data: dict, output_dir: Path) -> Path:
    """Generate a deep narrative synthesis report using Opus."""
    pid = run_data["protocol_id"]
    name = run_data["protocol_name"]
    result = run_data["result"]
    timings = run_data["timings"]

    print(f"  Generating synthesis report for {pid}...")

    raw_output = _serialize_result(result)
    # Truncate if enormous (keep first 12K chars to fit in context)
    if len(raw_output) > 12000:
        raw_output = raw_output[:12000] + f"\n\n... [truncated — full output was {len(raw_output)} chars]"

    # Build timings block
    if timings:
        timings_block = "\n".join(f"- {phase}: {duration:.1f}s" for phase, duration in timings.items())
    else:
        timings_block = "(no phase timings available)"

    # Build agent list from result
    agents_str = "CEO, CFO, CTO"  # default for this batch
    if hasattr(result, "agents") and result.agents:
        agents_str = ", ".join(
            a.get("name", "?") if isinstance(a, dict) else str(a)
            for a in result.agents
        )

    prompt = REPORT_PROMPT.format(
        protocol_id=pid.upper(),
        protocol_name=name,
        category=run_data["category"],
        question=run_data["question"],
        agents=agents_str,
        elapsed=run_data["elapsed_seconds"],
        agent_mode=run_data["agent_mode"],
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

    # Extract text from response (skip thinking blocks)
    report_text = ""
    for block in resp.content:
        if hasattr(block, "text"):
            report_text += block.text

    # Write report
    safe_name = name.lower().replace("/", "_").replace(" ", "_")
    report_name = f"{pid}_{safe_name}_synthesis_report.md"
    report_path = output_dir / report_name
    report_path.write_text(report_text)
    print(f"  Report saved: {report_path} ({len(report_text)} chars)")
    return report_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch runner for P26-P48 protocols with synthesis report generation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--protocols", "-p", nargs="+", default=None,
        help="Specific protocol IDs to run (e.g., p26 p30 p40). Default: all P26-P48.",
    )
    parser.add_argument(
        "--agents", "-a", nargs="+", default=["ceo", "cfo", "cto"],
        help="Agent keys to use (default: ceo cfo cto).",
    )
    parser.add_argument(
        "--output-dir", "-o", default="smoke-tests",
        help="Output directory for reports and raw JSON (default: smoke-tests).",
    )
    parser.add_argument(
        "--mode", choices=["research", "production"], default="research",
        help=(
            "Agent mode: 'research' uses lightweight dicts (fast, cheap), "
            "'production' uses full SDK agents. Default: research."
        ),
    )
    parser.add_argument(
        "--skip-reports", action="store_true",
        help="Run protocols but skip Opus synthesis report generation (saves tokens).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would run without executing any LLM calls.",
    )
    args = parser.parse_args()

    # Build agent list
    agents = build_agents(args.agents, mode=args.mode)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Filter protocol configs
    configs = PROTOCOL_CONFIGS
    if args.protocols:
        selected = {p.lower() for p in args.protocols}
        configs = [c for c in configs if c["id"] in selected]
        if not configs:
            print(f"ERROR: No matching protocols found for: {args.protocols}")
            print(f"Valid IDs: {[c['id'] for c in PROTOCOL_CONFIGS]}")
            return

    if args.dry_run:
        print("DRY RUN — would execute:")
        for c in configs:
            no_agents_note = " [no-agents constructor]" if c.get("no_agents") else ""
            extra_note = f" {c['extra_kwargs']}" if c.get("extra_kwargs") else ""
            print(f"  {c['id']}: {c['name']}{no_agents_note}{extra_note}")
            print(f"    Q: {c['question'][:70]}...")
        print(f"\nAgents ({args.mode} mode): {[a['name'] for a in agents]}")
        print(f"Output dir: {output_dir}")
        print(f"Skip reports: {args.skip_reports}")
        print(f"\nTotal: {len(configs)} protocols")
        return

    print(f"Batch runner: P26-P48 | {len(configs)} protocols | mode={args.mode}")
    print(f"Agents: {[a['name'] for a in agents]}")
    print(f"Output: {output_dir}/")
    if args.skip_reports:
        print("Note: synthesis reports disabled (--skip-reports)")

    results = []
    for config in configs:
        try:
            run_data = await run_protocol(config, agents, args.mode)
            report_path = None
            if not args.skip_reports:
                report_path = await generate_report(run_data, output_dir)
            results.append({
                "protocol": config["id"],
                "name": config["name"],
                "status": "ok",
                "time": run_data["elapsed_seconds"],
                "report": str(report_path) if report_path else "skipped",
            })
        except Exception as e:
            print(f"\n  ERROR running {config['id']}: {e}")
            traceback.print_exc()
            results.append({
                "protocol": config["id"],
                "name": config["name"],
                "status": "error",
                "error": str(e),
            })

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("BATCH SUMMARY — P26-P48")
    print(f"{'='*60}")
    ok = sum(1 for r in results if r["status"] == "ok")
    fail = len(results) - ok
    print(f"  Completed: {ok}/{len(configs)}  |  Failed: {fail}")
    total_time = sum(r.get("time", 0) for r in results)
    print(f"  Total protocol time: {total_time:.1f}s")
    print()
    for r in results:
        if r["status"] == "ok":
            time_str = f"({r['time']:.1f}s)"
            report_str = f"  -> {r['report']}" if r.get("report") != "skipped" else ""
            print(f"  [OK]   {r['protocol']}: {r['name']} {time_str}{report_str}")
        else:
            print(f"  [FAIL] {r['protocol']}: {r['name']}  ERROR: {r.get('error', '?')}")

    if fail > 0:
        print(f"\n  {fail} protocol(s) failed. Re-run with --protocols {' '.join(r['protocol'] for r in results if r['status'] == 'error')} to retry.")


if __name__ == "__main__":
    asyncio.run(main())
