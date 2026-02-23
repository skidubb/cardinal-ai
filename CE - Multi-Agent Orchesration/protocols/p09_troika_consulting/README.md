# P9: Troika Consulting

**Rotating client/consultant advisory: each agent presents a problem, two consult while the client listens, then the client reflects.**

| Property | Value |
|---|---|
| **Category** | Liberating Structures |
| **Problem Type** | Advisory / Consultation |
| **Tool Level** | T0 (no tools) |
| **Agents** | 3+ (each takes a turn as Client) |

## How It Works

Each round follows the Troika Consulting structure from Liberating Structures:

1. **Present (Phase 1)** — One agent acts as the Client and presents the problem from their role's perspective. Uses the thinking model (Opus) with extended thinking for depth.
2. **Consult (Phase 2)** — Two Consultant agents discuss the problem while the Client is SILENT. Consultant 1 gives initial analysis, Consultant 2 responds and builds, then a consolidation pass produces clean advice. Uses the orchestration model (Haiku) for the back-and-forth.
3. **Reflect (Phase 3)** — The Client receives all consolidated advice and reflects: what resonated, what surprised them, what they will adopt, and their action plan. Uses the thinking model (Opus) with extended thinking.

With 3+ agents, the protocol runs multiple rounds — each agent rotates into the Client role with the next two agents as Consultants. After all rounds, a final synthesis combines insights across all consultations.

## Usage

```bash
# Default — 3 agents (CEO, CFO, CTO), 3 rounds
python -m protocols.p09_troika_consulting.run --question "Should we pivot from B2B to B2C?"

# Custom agent set — 4 agents, 4 rounds
python -m protocols.p09_troika_consulting.run \
  --question "How should we respond to new regulatory requirements?" \
  --agents ceo cfo cto coo

# Minimal — exactly 3 agents
python -m protocols.p09_troika_consulting.run -q "What's our hiring strategy?" -a ceo cpo cto

# JSON output
python -m protocols.p09_troika_consulting.run -q "Should we raise a Series B?" --json
```

## Output

The result includes full detail for every round:

- **Rounds** — Each round contains:
  - Client's problem statement
  - Consultant 1's initial analysis
  - Consultant 2's response and build
  - Consolidated advice
  - Client's reflection and action plan
- **Final synthesis** — Cross-round insights, top recommendations, unresolved tensions, next steps
- **Stats** — Elapsed time per round, model call counts

## Model Usage

| Phase | Model | Calls per Round | Purpose |
|---|---|---|---|
| Client presents | `claude-opus-4-6` | 1 | Deep problem framing with extended thinking |
| Consultant 1 initial | `claude-haiku-4-5-20251001` | 1 | First analysis pass |
| Consultant 2 responds | `claude-haiku-4-5-20251001` | 1 | Build on and challenge Consultant 1 |
| Consolidate advice | `claude-haiku-4-5-20251001` | 1 | Clean advisory output |
| Client reflects | `claude-opus-4-6` | 1 | Reflection with extended thinking |
| Final synthesis | `claude-opus-4-6` | 1 (total) | Cross-round synthesis (multi-round only) |

**Total per run (N agents):** N rounds x (2 Opus + 3 Haiku) + 1 Opus synthesis = 2N+1 Opus, 3N Haiku calls.
