# P6: TRIZ Inversion Protocol

**"What would guarantee failure?" — then invert to find solutions.**

Category: Liberating Structures | Problem Type: Risk / Pre-Mortem | Tool Level: T1

## How It Works

1. **Reframe** — The user's plan is reframed as "How would you guarantee this fails?"
2. **Failure Generation** — N agents independently brainstorm failure modes (parallel, Opus)
3. **Deduplicate & Categorize** — Merge duplicates, assign categories (Haiku)
4. **Invert** — Each failure mode becomes a specific solution/mitigation (Haiku)
5. **Rank** — Score severity (1-5) × likelihood (1-5), sort by composite (Haiku)
6. **Synthesize** — Final actionable briefing with top risks and mitigations (Opus)

## Usage

### CLI

```bash
# Default agents (CEO, CFO, CTO, CMO)
python -m protocols.p06_triz.run \
  -q "We've decided to take the $500K enterprise engagement outside our ICP. What kills us?"

# Custom agent set
python -m protocols.p06_triz.run \
  -q "We're launching a self-serve product tier alongside our services business" \
  --agents ceo cfo cto cpo cro

# Custom agents from JSON
python -m protocols.p06_triz.run \
  -q "..." \
  --agent-config my-agents.json
```

### Python

```python
import asyncio
from protocols.p06_triz import TRIZOrchestrator

agents = [
    {"name": "CEO", "system_prompt": "You are a CEO focused on strategy..."},
    {"name": "CFO", "system_prompt": "You are a CFO focused on financial risk..."},
]

orchestrator = TRIZOrchestrator(agents=agents)
result = asyncio.run(orchestrator.run(
    "We've decided to take the $500K enterprise engagement outside our ICP"
))

print(result.synthesis)
for f in result.failure_modes:
    print(f"[{f.composite}] {f.title} ({f.category})")
```

### Custom Agent Config (JSON)

```json
[
  {"name": "Sales Lead", "system_prompt": "You are a VP Sales focused on pipeline and deal execution."},
  {"name": "CS Lead", "system_prompt": "You are a CS leader focused on retention and client health."},
  {"name": "Eng Lead", "system_prompt": "You are an engineering lead focused on delivery and technical risk."}
]
```

## Output

`TRIZResult` contains:
- `failure_modes` — Ranked list of `FailureMode` objects (title, description, category, severity, likelihood, composite score)
- `solutions` — Corresponding `Solution` objects mapped to each failure
- `synthesis` — Final strategic briefing (markdown)
- `agent_contributions` — Which agent surfaced which raw analysis

## Model Usage

| Stage | Model | Why |
|-------|-------|-----|
| Failure Generation | Opus 4.6 | Creative reasoning needs depth |
| Dedup & Categorize | Haiku 4.5 | Mechanical clustering task |
| Inversion | Haiku 4.5 | Structured transformation |
| Ranking | Haiku 4.5 | Scoring task |
| Synthesis | Opus 4.6 | Strategic writing needs depth |
