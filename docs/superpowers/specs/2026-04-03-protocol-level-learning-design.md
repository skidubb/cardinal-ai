# Protocol-Level Learning Layer — Design Spec

**Date:** 2026-04-03
**Status:** Approved
**Scope:** Internal tool for CE consulting runs
**Inspired by:** HyperAgents (Meta FAIR, 2603.19461) + "Agentic AI and the Next Intelligence Explosion" (Google, 2603.20639)

## Problem

Protocol runs are stateless — each run starts from scratch with no knowledge of past performance. The system captures rich telemetry (Langfuse traces, Postgres run records, cost tracking, eval scores) but never feeds it back into future runs. HyperAgents demonstrated that persistent performance tracking and contextual priming from past runs dramatically improve agent output quality, and these meta-improvements transfer across domains.

## Solution

A Postgres-first learning layer that wraps around existing protocol execution as pre/post hooks. No changes to orchestrator logic. Three learning dimensions:

1. **Protocol selection insights** — which protocol works best for which question category
2. **Configuration tuning** — optimal round counts, agent combos, thinking budgets per protocol+category
3. **Contextual priming** — inject high-scoring past synthesis excerpts as institutional memory into agent prompts

## Architecture Overview

```
Question Input
  |
  v
classify_question() -----> question_categories (Haiku, ~$0.001)
  |
  v
retrieve_insights() -----> RunInsights (DB queries, free)
  |                          - protocol_scores
  |                          - optimal config
  |                          - institutional_memory
  v
[Log protocol recommendation if differs from selected]
[Auto-apply config if confidence > 0.6 and user didn't specify]
[Inject institutional_memory into ServerAgent system prompt]
  |
  v
Orchestrator.run() -------> (UNCHANGED — existing protocol logic)
  |
  v
persist_run() ------------> (EXISTING — Postgres + Langfuse)
  |
  v
evaluate_multiagent() ----> eval_score (EXISTING — Langfuse judge)
  |
  v
record_learning() --------> (NEW — store run outcome for future learning)
  |                          - upsert run-learning record
  |                          - update best synthesis if new high score
  |                          - recompute aggregated insights every 5 runs
  v
Done
```

## Data Model

### New table: `protocol_insights`

Location: `ce-db/src/ce_db/models/insights.py`

```python
class ProtocolInsight(Base):
    __tablename__ = "protocol_insights"

    id: Mapped[uuid] = mapped_column(primary_key=True, default=uuid4)

    # What this insight is about
    protocol_key: Mapped[str]                    # "p06_triz"
    question_category: Mapped[str]               # "innovation"
    insight_type: Mapped[str]                    # "protocol_comparison" | "config_tuning" | "contextual"

    # The insight
    insight_json: Mapped[dict] = mapped_column(JSONB)
    confidence: Mapped[float]                    # 0.0-1.0, based on sample size
    sample_size: Mapped[int]                     # runs this is derived from

    # Best synthesis excerpt (for contextual priming)
    best_synthesis: Mapped[str | None]           # top-scoring synthesis text
    best_score: Mapped[float | None]             # score of that synthesis

    # Lifecycle
    computed_at: Mapped[datetime]
    expires_at: Mapped[datetime | None]          # recompute after N new runs

    __table_args__ = (
        Index("ix_insights_lookup", "protocol_key", "question_category", "insight_type"),
    )
```

### New table: `run_learnings`

Lightweight per-run record used for aggregation. Separate from the `runs` table to avoid schema changes to existing infrastructure.

```python
class RunLearning(Base):
    __tablename__ = "run_learnings"

    id: Mapped[uuid] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[uuid] = mapped_column(ForeignKey("runs.id"))

    protocol_key: Mapped[str]
    question_categories: Mapped[list[str]] = mapped_column(JSONB)
    eval_score: Mapped[float]
    config_json: Mapped[dict] = mapped_column(JSONB)   # {"rounds": 3, "agents": [...], "thinking_model": "opus"}
    cost_usd: Mapped[float]
    synthesis_excerpt: Mapped[str | None]               # first 2000 chars of synthesis

    created_at: Mapped[datetime] = mapped_column(default=func.now())

    __table_args__ = (
        Index("ix_run_learnings_protocol", "protocol_key"),
        Index("ix_run_learnings_score", "eval_score"),
    )
```

### Alembic migration

New migration in `ce-db/alembic/versions/` adding both tables. No changes to existing `runs` or `agent_outputs` tables.

## Question Classification

Location: `CE - Multi-Agent Orchestration/protocols/learning/classifier.py`

```python
QUESTION_CATEGORIES = [
    "innovation",      # New products, features, market entry
    "pricing",         # Revenue models, pricing strategy, unit economics
    "risk",            # Risk assessment, scenario planning, threats
    "strategy",        # Long-term direction, competitive positioning
    "operations",      # Process, efficiency, scaling, execution
    "growth",          # GTM, demand gen, pipeline, expansion
    "talent",          # Hiring, org design, culture
    "technology",      # Architecture, build vs buy, tech debt
    "financial",       # Cash flow, margins, investment decisions
]

async def classify_question(client: AsyncAnthropic, question: str) -> list[str]:
    """Classify question into 1-2 categories using Haiku. ~$0.001/call."""
    response = await llm_complete(
        client,
        agent_name="classifier",
        model=ORCHESTRATION_MODEL,
        messages=[{
            "role": "user",
            "content": (
                f"Classify this business question into 1-2 categories.\n"
                f"Categories: {', '.join(QUESTION_CATEGORIES)}\n\n"
                f"Question: {question}\n\n"
                f"Return ONLY a JSON array: [\"category1\"] or [\"category1\", \"category2\"]"
            ),
        }],
        max_tokens=50,
    )
    return _parse_categories(response)
```

## Post-Run: `record_learning()`

Location: `CE - Multi-Agent Orchestration/protocols/learning/recorder.py`

Called after `persist_run()` completes successfully. Non-blocking — failures are logged as warnings, never halt the run.

```python
async def record_learning(
    run_id: str,
    protocol_key: str,
    question: str,
    question_categories: list[str],
    eval_score: float,
    config: dict,
    synthesis_text: str,
    cost_summary: dict,
) -> None:
    """Store run outcome for future learning. Non-blocking."""
    try:
        async with get_session() as session:
            # 1. Store run-learning record
            learning = RunLearning(
                run_id=run_id,
                protocol_key=protocol_key,
                question_categories=question_categories,
                eval_score=eval_score,
                config_json=config,
                cost_usd=cost_summary.get("total_usd", 0.0),
                synthesis_excerpt=synthesis_text[:2000] if synthesis_text else None,
            )
            session.add(learning)

            # 2. Update best synthesis if this is a new high score
            for cat in question_categories:
                existing = await _get_contextual_insight(session, protocol_key, cat)
                if existing is None or eval_score > (existing.best_score or 0):
                    await _upsert_contextual_insight(
                        session, protocol_key, cat,
                        best_synthesis=synthesis_text[:3000],
                        best_score=eval_score,
                    )

            # 3. Recompute aggregated insights if enough new data
            new_run_count = await _count_runs_since_last_compute(
                session, protocol_key, question_categories
            )
            if new_run_count >= 5:
                await _recompute_insights(session, protocol_key, question_categories)

            await session.commit()
    except Exception as e:
        logger.warning(f"record_learning failed (non-blocking): {e}")
```

### Insight Recomputation (`_recompute_insights`)

Queries `run_learnings` table to compute:

**Protocol comparison** (per category):
```sql
SELECT protocol_key, 
       AVG(eval_score) as avg_score, 
       COUNT(*) as n
FROM run_learnings
WHERE question_categories @> '["innovation"]'
GROUP BY protocol_key
HAVING COUNT(*) >= 3
ORDER BY avg_score DESC
```

**Config tuning** (per protocol+category):
```sql
SELECT config_json->>'rounds' as rounds,
       AVG(eval_score) as avg_score,
       AVG(cost_usd) as avg_cost,
       COUNT(*) as n  
FROM run_learnings
WHERE protocol_key = 'p04_multi_round_debate'
  AND question_categories @> '["strategy"]'
GROUP BY config_json->>'rounds'
```

**Confidence calculation**: `min(1.0, sample_size / 20)` — full confidence at 20+ runs.

## Pre-Run: `retrieve_insights()`

Location: `CE - Multi-Agent Orchestration/protocols/learning/retriever.py`

```python
@dataclass
class RunInsights:
    protocol_scores: dict[str, float]       # {"p06_triz": 4.2, "p04_debate": 3.1}
    recommended_protocol: str | None
    optimal_rounds: int | None
    optimal_agents: list[str] | None
    thinking_budget: int | None
    institutional_memory: str | None        # Best past synthesis excerpt
    confidence: float                       # 0-1
    sample_size: int

    @property
    def has_recommendations(self) -> bool:
        return self.confidence > 0.3 and self.sample_size >= 3

async def retrieve_insights(
    protocol_key: str,
    question: str,
    question_categories: list[str],
) -> RunInsights:
    """Retrieve relevant learning before a protocol run. Returns empty insights on failure."""
    try:
        async with get_session() as session:
            protocol_scores = await _get_protocol_scores(session, question_categories)
            config = await _get_config_insight(session, protocol_key, question_categories)
            contextual = await _get_contextual_insight(session, protocol_key, question_categories)

            sample_size = sum(protocol_scores.values()) if protocol_scores else 0

            return RunInsights(
                protocol_scores={k: v["avg_score"] for k, v in protocol_scores.items()},
                recommended_protocol=_pick_best(protocol_scores, protocol_key),
                optimal_rounds=config.get("optimal_rounds") if config else None,
                optimal_agents=config.get("optimal_agents") if config else None,
                thinking_budget=config.get("thinking_budget") if config else None,
                institutional_memory=contextual.best_synthesis if contextual else None,
                confidence=min(1.0, sample_size / 20),
                sample_size=sample_size,
            )
    except Exception as e:
        logger.warning(f"retrieve_insights failed (degrading gracefully): {e}")
        return RunInsights(
            protocol_scores={}, recommended_protocol=None,
            optimal_rounds=None, optimal_agents=None, thinking_budget=None,
            institutional_memory=None, confidence=0.0, sample_size=0,
        )
```

## Injection Points

### Orchestrator-level (CLI/API)

In `protocols/run.py` (CLI) and `api/runner.py` (API), before `orchestrator.run()`:

```python
# Classify + retrieve
categories = await classify_question(client, question)
insights = await retrieve_insights(protocol_key, question, categories)

# Log protocol recommendation
if insights.recommended_protocol and insights.recommended_protocol != protocol_key:
    logger.info(
        f"[Learning] {insights.recommended_protocol} scored "
        f"{insights.protocol_scores.get(insights.recommended_protocol, '?'):.1f} avg "
        f"vs {protocol_key} at {insights.protocol_scores.get(protocol_key, '?')} "
        f"for {categories} (n={insights.sample_size})"
    )

# Auto-apply config if confident and user didn't override
if insights.confidence > 0.6:
    if insights.optimal_rounds and not args.rounds:
        args.rounds = insights.optimal_rounds
        logger.info(f"[Learning] Auto-set rounds={insights.optimal_rounds}")

# Pass institutional memory to orchestrator for agent injection
orchestrator.institutional_memory = insights.institutional_memory
```

### Agent-level (ServerAgent system prompt)

In `server_agent.py`, `_build_system_prompt()`:

```python
# After existing memory/lessons/preferences sections:
if self.institutional_memory:
    sections.append(
        "## Institutional Memory -- Past Protocol Insights\n\n"
        "The following is a high-quality synthesis from a previous run on a similar question. "
        "Use it as context, not as a template. Build on its strengths and address its gaps.\n\n"
        f"{self.institutional_memory}"
    )
```

The `institutional_memory` attribute is set by the orchestrator before calling `agent.chat()`. Orchestrators pass it through from the pre-run insights.

## Graceful Degradation

Every component degrades silently — matching the existing pattern in Langfuse tracing, Postgres persistence, and Pinecone memory:

| Component | On Failure | Behavior |
|-----------|-----------|----------|
| `classify_question()` | Returns `["strategy"]` (safe default) | Broad matching, slightly less precise |
| `retrieve_insights()` | Returns empty `RunInsights` | No recommendations, no priming — runs as today |
| `record_learning()` | Logs warning, returns None | Run data lost for learning but run itself unaffected |
| DB unavailable | All learning functions no-op | Full system works exactly as current behavior |

## Files to Create/Modify

### New files:
- `CE - Multi-Agent Orchestration/protocols/learning/__init__.py`
- `CE - Multi-Agent Orchestration/protocols/learning/classifier.py` — question classification
- `CE - Multi-Agent Orchestration/protocols/learning/recorder.py` — post-run learning
- `CE - Multi-Agent Orchestration/protocols/learning/retriever.py` — pre-run insights
- `ce-db/src/ce_db/models/insights.py` — ProtocolInsight + RunLearning models
- `ce-db/alembic/versions/xxx_add_learning_tables.py` — migration

### Modified files:
- `ce-db/src/ce_db/models/__init__.py` — export new models
- `CE - Multi-Agent Orchestration/protocols/server_agent.py` — add `institutional_memory` attribute + system prompt injection (~5 lines)
- `CE - Multi-Agent Orchestration/protocols/persistence.py` — call `record_learning()` after `persist_run()` (~10 lines)
- CLI `run.py` files (per protocol) — add classify + retrieve + inject before orchestrator.run() (~15 lines each, or extract to shared helper)

### Not modified:
- No orchestrator changes (p04, p06, etc.)
- No changes to `llm.py`, `cost_tracker.py`, `langfuse_tracing.py`
- No changes to agent registry or agent prompts

## Cold Start Behavior

With 0 past runs:
- `retrieve_insights()` returns empty RunInsights (confidence=0, no recommendations)
- No institutional memory injected
- System behaves identically to current behavior
- Every run stores a learning record, building the corpus

With 1-4 runs per protocol+category:
- Contextual priming works (best synthesis stored on first run)
- Protocol comparison and config tuning wait for 5+ runs to recompute (low confidence)

With 5+ runs:
- Full learning active — protocol recommendations, config auto-tuning, contextual priming

## Future Extensions (Not In Scope)

- **Pinecone semantic layer**: Embed synthesis excerpts for content-similar matching (vs. category matching). Add when category matching proves insufficient.
- **A/B testing**: Deliberately run alternative protocols on the same question to build comparison data faster.
- **Learning decay**: Weight recent runs higher than older ones. Currently all runs are weighted equally.
- **Multi-tenant**: Scope insights per client/engagement. Currently all runs contribute to the same learning pool.

## Verification Plan

1. **Unit tests**: Test classifier, recorder, retriever in isolation with mock DB
2. **Integration test**: Run a protocol, verify run_learning record is created, run the same protocol category again, verify insights are retrieved
3. **Smoke test**: Run 5+ protocols on similar questions, verify insights table populates and recommendations appear in logs
4. **Regression test**: Verify existing protocol behavior is unchanged when learning tables are empty (cold start)
5. **Graceful degradation test**: Disconnect Postgres, verify protocols still run without errors
