# P15: What / So What / Now What

**Category:** Liberating Structures
**Agents:** Any (default: CEO, CFO, CTO, CMO)
**Models:** Opus (thinking phases) + Haiku (consolidation)

## Protocol Overview

Three-frame temporal sensemaking protocol that moves a group from raw observations through implications to concrete actions.

| Phase | Frame | Model | Parallelism |
|-------|-------|-------|-------------|
| 1 | WHAT — observations | Opus (thinking) | Parallel across agents |
| 2 | Consolidate observations | Haiku | Single call |
| 3 | SO WHAT — implications | Opus (thinking) | Parallel across agents |
| 4 | Consolidate implications | Haiku | Single call |
| 5 | NOW WHAT — actions | Opus (thinking) | Parallel across agents |
| 6 | Final synthesis | Opus (thinking) | Single call |

## Usage

```bash
# Default (4 agents)
python -m protocols.p15_what_so_what_now_what.run \
  -q "Our largest customer just announced they're building our core feature in-house"

# All 7 agents
python -m protocols.p15_what_so_what_now_what.run \
  -q "Revenue growth has stalled for two consecutive quarters" \
  -a ceo cfo cto cmo coo cpo cro

# JSON output
python -m protocols.p15_what_so_what_now_what.run \
  -q "A major competitor just acquired our key technology partner" \
  --json
```

## Result Structure

```
WhatSoWhatNowWhatResult:
  question                    — original input
  what_observations           — dict[agent_name → observations text]
  consolidated_observations   — themed summary of all observations
  so_what_implications        — dict[agent_name → implications text]
  consolidated_implications   — themed summary of all implications
  now_what_actions            — dict[agent_name → action items text]
  final_synthesis             — structured final output
  timings                     — dict[phase → seconds]
  model_calls                 — dict[model → call count]
```

## Cost Profile (4 agents)

- Opus calls: 4 + 4 + 4 + 1 = **13** (thinking phases + synthesis)
- Haiku calls: 1 + 1 = **2** (consolidation)
- Total: **15 API calls**
