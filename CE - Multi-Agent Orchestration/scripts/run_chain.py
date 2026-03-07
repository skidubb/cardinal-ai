"""Run a 4-protocol strategic decision chain with shared Langfuse session.

Chain: P23 Cynefin → P06 TRIZ → P39 Popper → P38 Klein Premortem

Each protocol's output feeds into the next protocol's input:
  1. Cynefin classifies the domain → enriches TRIZ question with domain context
  2. TRIZ finds failure modes + solutions → builds recommendation for Popper
  3. Popper stress-tests the recommendation → verdict informs Premortem framing
  4. Klein Premortem imagines failure modes given the full chain context

Usage:
    python scripts/run_chain.py -q "Should we acquire a competitor to enter the healthcare vertical?"
"""

import argparse
import asyncio
import json
import time

from protocols.langfuse_tracing import set_session_id, get_trace_id, flush
from protocols.agents import BUILTIN_AGENTS


AGENT_KEYS = ["ceo", "cfo", "cto"]
SESSION_ID = f"chain-{int(time.time())}"


def get_agents():
    return [BUILTIN_AGENTS[k] for k in AGENT_KEYS]


async def run_chain(question: str):
    set_session_id(SESSION_ID)
    print(f"Session: {SESSION_ID}")
    print(f"Question: {question}")
    print(f"Agents: {AGENT_KEYS}")
    print("=" * 70)

    traces = {}

    # ── Step 1: Cynefin — classify the domain ──
    print("\n[1/4] P23 Cynefin Probe-Sense-Respond — classifying domain...")
    from protocols.p23_cynefin_probe.orchestrator import CynefinOrchestrator
    cynefin = CynefinOrchestrator(agents=get_agents())
    cynefin_result = await cynefin.run(question)
    traces["p23"] = getattr(cynefin_result, "_langfuse_trace_id", None)
    domain = cynefin_result.consensus_domain
    print(f"  Domain: {domain} (contested: {cynefin_result.was_contested})")
    print(f"  Trace: {traces['p23']}")

    # ── Step 2: TRIZ — generate failure modes + solutions ──
    # Feed Cynefin's domain classification into TRIZ as context
    cynefin_context = (
        f"[Cynefin domain: {domain}"
        f"{' (contested — agents disagreed)' if cynefin_result.was_contested else ''}] "
    )
    action_plan = cynefin_result.action_plan
    if isinstance(action_plan, dict):
        approach = action_plan.get("approach", action_plan.get("strategy", ""))
        if approach:
            cynefin_context += f"Recommended approach: {str(approach)[:300]}. "
    triz_question = f"{cynefin_context}{question}"

    print(f"\n[2/4] P06 TRIZ — generating failure modes and solutions...")
    print(f"  Enriched with Cynefin domain: {domain}")
    from protocols.p06_triz.orchestrator import TRIZOrchestrator
    triz = TRIZOrchestrator(agents=get_agents())
    triz_result = await triz.run(triz_question)
    traces["p06"] = getattr(triz_result, "_langfuse_trace_id", None)
    print(f"  Failure modes: {len(triz_result.failure_modes)}")
    print(f"  Solutions: {len(triz_result.solutions)}")
    print(f"  Trace: {traces['p06']}")

    # ── Step 3: Popper Falsification — stress-test the top solution ──
    # Build recommendation from TRIZ solutions for Popper to falsify
    recommendation = ""
    if triz_result.solutions:
        top = triz_result.solutions[0]
        recommendation = f"{top.title}: {top.description}"
    elif triz_result.synthesis:
        recommendation = triz_result.synthesis[:500]
    else:
        recommendation = f"Proceed with strategy: {question}"

    # Add TRIZ context so Popper knows what it's stress-testing
    popper_context = (
        f"{question}\n\n"
        f"Context from prior analysis:\n"
        f"- Cynefin domain: {domain}\n"
        f"- TRIZ identified {len(triz_result.failure_modes)} failure modes "
        f"and {len(triz_result.solutions)} solutions\n"
        f"- Top recommendation being tested: {recommendation[:200]}"
    )

    print(f"\n[3/4] P39 Popper Falsification — stress-testing recommendation...")
    print(f"  Testing: {recommendation[:100]}...")
    from protocols.p39_popper_falsification.orchestrator import FalsificationOrchestrator
    popper = FalsificationOrchestrator(agents=get_agents())
    popper_result = await popper.run(recommendation=recommendation, question=popper_context)
    traces["p39"] = getattr(popper_result, "_langfuse_trace_id", None)
    verdict = popper_result.verdict if hasattr(popper_result, "verdict") else "unknown"
    print(f"  Verdict: {verdict}")
    print(f"  Conditions tested: {len(popper_result.conditions)}")
    print(f"  Trace: {traces['p39']}")

    # ── Step 4: Klein Premortem — imagine failure given full chain context ──
    # Feed the entire chain's findings into the premortem
    activated_conditions = [
        c["condition"] for c in popper_result.conditions
        if c.get("activated")
    ]
    premortem_question = (
        f"{question}\n\n"
        f"Prior analysis context (imagine this strategy has FAILED):\n"
        f"- Cynefin domain: {domain}\n"
        f"- TRIZ top solution: {recommendation[:200]}\n"
        f"- Popper verdict: {verdict}"
    )
    if activated_conditions:
        premortem_question += (
            f"\n- Falsification conditions triggered: "
            + "; ".join(activated_conditions[:3])
        )
    if popper_result.verdict_reasoning:
        premortem_question += f"\n- Verdict reasoning: {popper_result.verdict_reasoning[:300]}"

    print(f"\n[4/4] P38 Klein Premortem — imagining failure modes...")
    print(f"  Informed by Popper verdict: {verdict}")
    from protocols.p38_klein_premortem.orchestrator import PreMortemOrchestrator
    klein = PreMortemOrchestrator(agents=get_agents())
    klein_result = await klein.run(premortem_question)
    traces["p38"] = getattr(klein_result, "_langfuse_trace_id", None)
    failures = klein_result.failure_modes if hasattr(klein_result, "failure_modes") else []
    print(f"  Failure modes: {len(failures)}")
    print(f"  Trace: {traces['p38']}")

    # ── Summary ──
    print("\n" + "=" * 70)
    print("CHAIN COMPLETE — Output Cascade:")
    print("=" * 70)
    print(f"  Q: {question[:80]}")
    print(f"  1. Cynefin domain: {domain} → fed into TRIZ framing")
    print(f"  2. TRIZ top solution: {recommendation[:80]} → fed into Popper")
    print(f"  3. Popper verdict: {verdict} → fed into Premortem")
    print(f"  4. Premortem failures: {len(failures)} modes identified")
    print(f"\nSession: {SESSION_ID}")
    print(f"Traces:")
    for proto, tid in traces.items():
        print(f"  {proto}: {tid}")
    print(f"\nAll 4 traces share session '{SESSION_ID}' in Langfuse.")

    flush()


def main():
    parser = argparse.ArgumentParser(description="4-protocol strategic decision chain")
    parser.add_argument("--question", "-q", required=True, help="Strategic question")
    args = parser.parse_args()
    asyncio.run(run_chain(args.question))


if __name__ == "__main__":
    main()
