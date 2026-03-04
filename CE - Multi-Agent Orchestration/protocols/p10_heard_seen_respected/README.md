# P10: Heard-Seen-Respected

**Empathy-driven perspective translation: narrative sharing, reflective listening, and bridge-building across stakeholder divides.**

| Property | Value |
|---|---|
| **Category** | Liberating Structures |
| **Problem Type** | Multi-Stakeholder Alignment |
| **Tool Level** | T0 (no tools) |
| **Agents** | N (minimum 2; works best with 3-7) |

## How It Works

1. **Share (Phase 1)** — Each agent writes a first-person experiential narrative about the challenge from their role's perspective. This is not analysis — it is an emotionally honest account of pressures, trade-offs, and invisible concerns. All agents run in parallel using the thinking model (Opus).
2. **Reflect (Phase 2)** — Each agent reads another agent's narrative and reflects it back using three lenses: "What I heard you saying was...", "What I noticed was...", "What I respect about your position is..." Agents are paired circularly (A reflects B, B reflects C, ... N reflects A). All reflections run in parallel using the orchestration model (Haiku).
3. **Bridge (Phase 3)** — The thinking model (Opus) synthesizes all narratives and reflections into a Bridge Synthesis containing: common ground across perspectives, key differences and genuine tensions, and a translation guide that maps each stakeholder's concerns into language the others can understand.

## Usage

```bash
# Default — 4 agents (CEO, CFO, CTO, CMO)
python -m protocols.p10_heard_seen_respected.run --question "How do we handle the tension between rapid growth and engineering sustainability?"

# Full C-Suite — 7 agents
python -m protocols.p10_heard_seen_respected.run \
  --question "Should we pursue the acquisition even though it strains our balance sheet?" \
  --agents ceo cfo cto cmo coo cpo cro

# Minimal — 2 agents (single pair)
python -m protocols.p10_heard_seen_respected.run -q "How should we prioritize security vs speed-to-market?" -a cto cmo
```

## Output

The result includes all intermediate outputs for full empathy tracing:

- **Narratives** — Each agent's first-person experiential account
- **Reflections** — Each agent's structured reflection of another's narrative (heard / noticed / respected)
- **Common Ground** — Shared concerns and values across all perspectives
- **Key Differences** — Genuine tensions and trade-offs between perspectives
- **Translation Guide** — Maps each role's language and concerns into terms the others understand
- **Stats** — Per-phase timings and model call counts

## Model Usage

| Phase | Model | Calls | Purpose |
|---|---|---|---|
| Share (narratives) | `claude-opus-4-6` | N | Experiential narrative with extended thinking |
| Reflect | `claude-haiku-4-5-20251001` | N | Structured reflective listening |
| Bridge synthesis | `claude-opus-4-6` | 1 | Common ground, differences, translation guide |
