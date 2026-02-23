# P22: Sequential Pipeline

**Agent A -> Agent B -> Agent C — each builds on prior output.**

| Field | Value |
|-------|-------|
| **Category** | Org Theory |
| **Problem Type** | Structured Analysis |
| **Tool Level** | T0 (no tools) |

## How It Works

1. **Sequential Execution** — Agents process one at a time in a user-specified order. Each agent receives the original question plus all accumulated prior stage outputs with full lineage tracking.
2. **Lineage Tracking** — Every stage output is labeled with the agent name and stage number so downstream agents can reference and build on specific prior contributions.
3. **Quality Gate** — After all stages complete, a lightweight model assesses whether the pipeline output adequately addresses the question. If it fails, the weakest stage is re-run (max 1 retry).
4. **Final Synthesis** — A synthesis pass compiles all stage outputs into a single cohesive response, acknowledging the lineage of key insights.

## Usage

```bash
# Default pipeline: CEO -> CFO -> CTO
python -m protocols.p22_sequential_pipeline.run \
  --question "Should we acquire this competitor?" \
  --agents ceo cfo cto

# Custom pipeline order (4 agents)
python -m protocols.p22_sequential_pipeline.run \
  -q "How should we enter the European market?" \
  -a cmo ceo cfo coo

# All 7 agents
python -m protocols.p22_sequential_pipeline.run \
  -q "What should our 3-year strategy be?" \
  -a ceo cpo cto cfo cmo coo cro
```

## Output

- **Processing Lineage** — Each stage's output with agent attribution
- **Quality Gate** — Pass/fail with reasoning
- **Final Synthesized Output** — Cohesive response integrating all stages

## Model Usage

| Component | Model | Purpose |
|-----------|-------|---------|
| Stage processing | `claude-opus-4-6` | Deep analysis with extended thinking |
| Quality gate | `claude-haiku-4-5-20251001` | Fast pass/fail assessment |
| Final synthesis | `claude-opus-4-6` | Coherent integration of all stages |
