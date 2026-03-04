"""Stage prompts for P48: Black Swan Detection & Santa Fe Systems Thinking."""

CAUSAL_GRAPH_PROMPT = """\
You are participating in a Black Swan Detection analysis — an adversarial \
epistemic hygiene process that surfaces catastrophic-but-improbable scenarios \
mainstream framing misses.

LAYER 1: CAUSAL GRAPH CONSTRUCTION

Build a directional causal graph for the system described below. Your analysis \
MUST include:

1. **Key Variables**: Identify 8-15 variables that drive the system's behavior. \
Include variables from adjacent systems that interact with this one.

2. **Causal Links**: For each pair of connected variables, specify direction \
and polarity (reinforcing + or balancing -).

3. **Feedback Loops**: Map ALL reinforcing (amplifying) and balancing \
(stabilizing) feedback loops. Label each loop and classify it.

4. **Emergence Analysis**: Identify properties that appear in the INTERACTION \
of subsystems but are NOT present in any individual subsystem. What behaviors \
emerge only when these systems couple?

5. **Non-Linear Relationships**: Flag any variables where small changes can \
produce disproportionate effects (leverage points, tipping points).

CRITICAL RULES:
- Single-cause explanations are PROHIBITED. Every outcome must trace through \
multiple causal paths.
- You must include at least 2 reinforcing loops and 2 balancing loops.
- Include cross-system interactions (e.g., how market dynamics interact with \
technology adoption, regulatory response, or social behavior).

Present your causal graph as a structured list of: Variables, Links (A → B, \
polarity), Feedback Loops (named, classified), and Emergent Properties.

THE SYSTEM TO ANALYZE:
{question}
"""

THRESHOLD_SCAN_PROMPT = """\
You are participating in a Black Swan Detection analysis.

LAYER 2: THRESHOLD & PHASE TRANSITION SCANNING

Given the causal graph below, identify variables approaching critical values \
and potential phase transitions.

For each variable in the causal graph:

1. **Current State Assessment**: Where is this variable relative to known or \
estimated thresholds? Is it in a stable basin, approaching an edge, or already \
in transition?

2. **Phase Transition Points**: What value or condition would trigger a \
qualitative shift in system behavior? What does the system look like BEFORE \
vs AFTER the transition? These are not gradual changes — they are regime shifts.

3. **Threshold Proximity**: Rate each variable's distance from its critical \
threshold (FAR / APPROACHING / NEAR / AT_THRESHOLD).

4. **Post-Transition State**: If the threshold is breached, what is the new \
equilibrium? Is it reversible or irreversible?

5. **Hidden Thresholds**: Are there thresholds that are invisible in normal \
monitoring but would be catastrophic if crossed? What would make them visible?

Focus especially on variables in reinforcing feedback loops — these are where \
runaway dynamics emerge.

THE ORIGINAL QUESTION:
{question}

CAUSAL GRAPH FROM LAYER 1:
{causal_graphs}
"""

CONFLUENCE_PROMPT = """\
You are a mechanical extraction system. Your job is to identify confluence \
scenarios from the threshold analysis below.

A CONFLUENCE is a scenario where 3 or more threshold variables activate \
simultaneously or in rapid cascade. These are the conditions under which \
black swan events emerge — not from single failures but from combinatorial \
instability.

Extract every plausible confluence scenario. For each one, output:
- "id": a short identifier (e.g., "C1", "C2")
- "name": a descriptive name for the scenario
- "variables": list of 3+ variables involved
- "trigger_sequence": how one threshold breach cascades to others
- "estimated_probability": your estimate (use "very_low", "low", "medium")
- "estimated_impact": severity if it occurs ("high", "severe", "catastrophic")
- "time_horizon": how quickly the cascade unfolds

Output a JSON array of confluence objects. No commentary outside the JSON.

THRESHOLD ANALYSIS:
{threshold_scans}
"""

HISTORICAL_ANALOGUE_PROMPT = """\
You are participating in a Black Swan Detection analysis.

LAYER 4: HISTORICAL ANALOGUE MINING

For each confluence scenario below, identify the closest historical analogues \
— past events where similar combinations of threshold breaches produced \
unexpected outcomes.

For each analogue:

1. **The Event**: What happened? When and where?
2. **The Confluence**: Which variables crossed thresholds simultaneously?
3. **What Was Missed**: What did mainstream analysis fail to see? Why?
4. **The Warning Signal**: What early indicator existed but was ignored or \
misinterpreted? How much lead time did it provide?
5. **The Mechanism**: How did the cascade actually unfold? What was the \
sequence of failures?
6. **Transferability**: How closely does this analogue map to the current \
scenario? What's similar and what's different?

Prioritize analogues where the MECHANISM of failure matches, not just surface \
similarity. A financial crisis and an ecosystem collapse can share the same \
cascade dynamics even if the domains differ.

THE ORIGINAL QUESTION:
{question}

CONFLUENCE SCENARIOS:
{confluences}
"""

ADVERSARIAL_MEMO_PROMPT = """\
You are a senior adversarial analyst producing the final Black Swan Detection \
memo. Your job is to synthesize all prior layers into a structured adversarial \
briefing that challenges mainstream assumptions.

Your analytical prior is INVERTED from normal analysis: you are rewarded for \
surfacing outliers, not penalized. Absence of evidence is not evidence of \
absence. Improbable does not mean impossible.

Produce a structured adversarial memo with these sections:

## 1. EXECUTIVE SUMMARY
One paragraph: what black swan risks exist and why they matter.

## 2. SYSTEM FRAGILITY MAP
Key feedback loops, leverage points, and hidden coupling between subsystems. \
Where is the system most brittle?

## 3. BLACK SWAN SCENARIOS (ranked by impact × proximity)
For each scenario:
- **Scenario Name**: Descriptive title
- **Causal Chain**: The sequence of threshold breaches that triggers it
- **Probability Assessment**: Very Low / Low / Medium (never "impossible")
- **Impact Assessment**: High / Severe / Catastrophic
- **Time Horizon**: Months / Quarters / Years
- **Historical Precedent**: The closest analogue and what it teaches us
- **Why It's Being Missed**: The cognitive or structural blind spot

## 4. EARLY WARNING SIGNALS
For each scenario, what observable indicators would confirm the risk is \
materializing? Be specific — these should be monitorable.

## 5. CONFIRMATION EVENTS
What would need to happen for us to upgrade each scenario from "possible" to \
"probable"? Define concrete trigger conditions.

## 6. RECOMMENDED ACTIONS
What should be done NOW (before any scenario materializes) to reduce fragility?

THE ORIGINAL QUESTION:
{question}

CAUSAL GRAPHS:
{causal_graphs}

THRESHOLD ANALYSIS:
{threshold_scans}

CONFLUENCE SCENARIOS:
{confluences}

HISTORICAL ANALOGUES:
{historical_analogues}
"""
