# P7: Wicked Questions Protocol

**Surface irresolvable paradoxes to sharpen strategic tensions.**

Category: Liberating Structures | Problem Type: Exploration / Strategic Framing | Tool Level: T0

## How It Works

1. **Tension Generation** — N agents independently surface paradoxes and competing truths (parallel, Opus)
2. **Wickedness Test** — 3-part filter: Both sides true? Cannot choose one? Creates real tension? (Haiku)
3. **Rank** — Score by urgency + impact + hiddenness (Haiku)
4. **Synthesize** — Paradox landscape, polarity management recommendations, conversation starters (Opus)

## Usage

### CLI

```bash
# Default agents (CEO, CFO, CTO, CMO)
python -m protocols.p07_wicked_questions.run \
  -q "Cardinal Element is scaling from boutique consultancy to mid-market platform company"

# Full C-Suite
python -m protocols.p07_wicked_questions.run \
  -q "We need to standardize delivery while keeping each engagement bespoke" \
  --agents ceo cfo cto cmo coo cpo
```

### Python

```python
import asyncio
from protocols.p07_wicked_questions import WickedQuestionsOrchestrator

agents = [
    {"name": "CEO", "system_prompt": "You are a CEO..."},
    {"name": "CFO", "system_prompt": "You are a CFO..."},
]

orchestrator = WickedQuestionsOrchestrator(agents=agents)
result = asyncio.run(orchestrator.run("Our AI strategy"))

print(result.synthesis)
for wq in result.wicked_questions:
    print(f"[{wq.composite}] {wq.wicked_question}")
```

## Output

`WickedQuestionsResult` contains:
- `wicked_questions` — Ranked list of `WickedQuestion` objects (side_a, side_b, formatted question, scores)
- `all_tensions_count` / `wicked_count` / `rejected_count` — Filter funnel metrics
- `synthesis` — Strategic briefing with polarity management recommendations
- `agent_contributions` — Raw tension analysis per agent

## Model Usage

| Stage | Model | Why |
|-------|-------|-----|
| Tension Generation | Opus 4.6 | Requires deep strategic reasoning |
| Wickedness Test | Haiku 4.5 | Structured boolean evaluation |
| Ranking | Haiku 4.5 | Scoring task |
| Synthesis | Opus 4.6 | Strategic writing needs depth |
