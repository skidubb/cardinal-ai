# P13: Ecocycle Planning

**Category:** Liberating Structures
**Purpose:** Map a portfolio of initiatives to lifecycle stages and generate stage-appropriate action plans.

## Overview

Ecocycle Planning uses the natural lifecycle metaphor (Birth -> Maturity -> Creative Destruction -> Renewal) to assess where each initiative sits and what actions are appropriate for its current stage. Multiple agents independently assess each initiative, consensus is built through voting, and stage-appropriate actions are generated.

## Lifecycle Stages

| Stage | Description | Actions |
|-------|------------|---------|
| **Birth** | Early-stage, needs nurturing | Invest, protect, set milestones |
| **Maturity** | Established, delivering value | Optimize, scale, defend position |
| **Destruction** | Declining, consuming resources | Sunset gracefully, harvest learnings |
| **Renewal** | Stagnant, ripe for reinvention | Experiment, pivot, prototype |

## Protocol Phases

1. **Assess** — Each agent independently assigns every initiative to a lifecycle stage with reasoning (parallel, Opus)
2. **Consensus** — Aggregate votes per initiative; >50% agreement = consensus, otherwise resolve via Haiku
3. **Action Plan** — Generate 3-5 stage-appropriate actions per initiative plus portfolio summary (Opus)

## Usage

```bash
python -m protocols.p13_ecocycle_planning.run \
  -q "How should we rebalance our product portfolio for 2026?" \
  -i "Legacy CRM" "AI Chatbot" "Mobile App v3" "Data Pipeline Rewrite" \
  -a ceo cfo cto cpo

# JSON output
python -m protocols.p13_ecocycle_planning.run \
  -q "Which initiatives deserve continued investment?" \
  -i "Project Alpha" "Project Beta" "Project Gamma" \
  --json
```

## Arguments

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `--question / -q` | Yes | — | Strategic context framing the assessment |
| `--initiatives / -i` | Yes | — | List of initiatives to assess (nargs=+) |
| `--agents / -a` | No | ceo cfo cto cmo | Agent keys to use |
| `--json` | No | false | Output raw JSON |
| `--thinking-model` | No | claude-opus-4-6 | Override thinking model |
| `--orchestration-model` | No | claude-haiku-4-5-20251001 | Override orchestration model |
