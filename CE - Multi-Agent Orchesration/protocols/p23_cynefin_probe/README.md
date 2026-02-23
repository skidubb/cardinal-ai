# P23: Cynefin Probe-Sense-Respond

**Category:** Org Theory
**Source:** Dave Snowden's Cynefin Framework
**Key Innovation:** Domain-adaptive decision-making — the protocol classifies the situation first, then applies the appropriate decision approach rather than using a one-size-fits-all method.

## Protocol Flow

```
Phase 1: Domain Classification (parallel, Opus)
    Each agent independently classifies the situation into a Cynefin domain
    (Clear, Complicated, Complex, Chaotic, or Confused)
        │
Phase 2: Consensus
    Aggregate votes — majority wins, ties default to Confused
        │
Phase 3: Domain-Appropriate Response (parallel)
    ├── Clear → Sense-Categorize-Respond (Haiku — best practice)
    ├── Complicated → Sense-Analyze-Respond (Opus — expert analysis)
    ├── Complex → Probe-Sense-Respond (Opus — safe-to-fail experiments)
    ├── Chaotic → Act-Sense-Respond (Opus — immediate stabilization)
    └── Confused → Decompose into sub-problems (Opus)
        │
Phase 4: Synthesis (Opus)
    Combine responses into a domain-appropriate action plan
```

## Usage

```bash
# From the repo root
python -m protocols.p23_cynefin_probe.run \
    -q "Our main competitor just acquired our largest partner — what do we do?" \
    -a ceo cfo cto cmo

# JSON output
python -m protocols.p23_cynefin_probe.run \
    -q "Should we pivot from B2B to B2C?" \
    --json

# All agents
python -m protocols.p23_cynefin_probe.run \
    -q "Our cloud costs tripled overnight and customers are reporting outages" \
    -a ceo cfo cto cmo coo cpo cro
```

## Cynefin Domains

| Domain | Characteristics | Approach | Model |
|--------|----------------|----------|-------|
| Clear | Obvious cause-effect, best practices exist | Sense-Categorize-Respond | Haiku |
| Complicated | Requires expertise, good practices exist | Sense-Analyze-Respond | Opus |
| Complex | Emergent, unpredictable, no right answers | Probe-Sense-Respond | Opus |
| Chaotic | Crisis, no cause-effect, act immediately | Act-Sense-Respond | Opus |
| Confused | Unclear which domain applies | Decompose & re-classify | Opus |

## Result Structure

```python
CynefinResult(
    question="...",
    domain_votes=[DomainVote(agent_name, domain, reasoning, confidence), ...],
    consensus_domain="complex",
    was_contested=True,
    domain_responses={"CEO": {...}, "CFO": {...}, ...},
    action_plan={"domain_summary": "...", "action_plan": "...", "priority_actions": [...], ...},
    timings={"phase1_classify": 12.3, ...},
)
```

## When to Use

- When you are unsure whether a problem is simple, complicated, or genuinely complex
- When the team disagrees on how to approach a situation
- When standard analytical frameworks are not producing useful results
- When you need to decide between "analyze more" vs. "experiment" vs. "act now"
