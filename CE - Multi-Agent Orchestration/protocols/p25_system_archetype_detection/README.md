# P25: System Archetype Detection

**Category:** Systems Thinking
**Agents:** N pattern observers + 1 archetype matcher
**Key Mechanism:** Match observed dynamics to 8 standard system archetypes

## Purpose

Identify which classic system archetype (Fixes That Fail, Shifting the Burden, Limits to Growth, etc.) best explains the recurring problematic dynamics in a given situation, then recommend archetype-specific interventions.

## The 8 Archetypes

1. **Fixes That Fail** — Quick fix worsens the problem via side effects
2. **Shifting the Burden** — Symptomatic solution undermines fundamental solution
3. **Limits to Growth** — Growth hits a constraint
4. **Eroding Goals** — Goals lowered instead of performance improved
5. **Escalation** — Competitive spiral between parties
6. **Success to the Successful** — Winner-take-all resource allocation
7. **Tragedy of the Commons** — Shared resource depletion
8. **Growth and Underinvestment** — Delayed capacity investment

## Phases

1. **Observe Dynamics** (parallel, Opus) — Each agent describes dynamic patterns from their perspective
2. **Merge Dynamics** (Haiku) — Deduplicate into canonical list
3. **Match Archetypes** (parallel, Opus) — Each agent scores all 8 archetypes (0-100)
4. **Synthesize** (Opus) — Select best-fit, explain structural mapping, recommend interventions

## Usage

```bash
python -m protocols.p25_system_archetype_detection.run --question "Our engineering team keeps applying hotfixes that create more bugs"
python -m protocols.p25_system_archetype_detection.run -q "..." --json
```
