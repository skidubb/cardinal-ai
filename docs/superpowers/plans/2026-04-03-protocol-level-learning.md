# Protocol-Level Learning Layer Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Postgres-first learning layer that feeds past protocol run outcomes (eval scores, costs, synthesis quality) back into future runs via pre/post hooks.

**Architecture:** Pre/post hooks wrap existing protocol execution. Post-run records learnings to new DB tables. Pre-run retrieves insights and injects them into ServerAgent system prompts. Zero orchestrator changes.

**Tech Stack:** SQLAlchemy async + asyncpg (existing), Pydantic v2, Alembic migrations, Anthropic Haiku for classification

**Spec:** `docs/superpowers/specs/2026-04-03-protocol-level-learning-design.md`

---

## Chunk 1: Database Models + Migration

### Task 1: Create ProtocolInsight and RunLearning models

**Files:**
- Create: `ce-db/src/ce_db/models/insights.py`
- Modify: `ce-db/src/ce_db/models/__init__.py:1-6`
- Test: `ce-db/tests/test_insights_models.py`

- [ ] **Step 1: Write the failing test for model imports**

```python
# ce-db/tests/test_insights_models.py
import uuid
from datetime import datetime

import pytest
from sqlalchemy import inspect

from ce_db.models import Base, ProtocolInsight, RunLearning


def test_protocol_insight_columns():
    mapper = inspect(ProtocolInsight)
    col_names = {c.key for c in mapper.columns}
    assert "protocol_key" in col_names
    assert "question_category" in col_names
    assert "insight_type" in col_names
    assert "insight_json" in col_names
    assert "confidence" in col_names
    assert "sample_size" in col_names
    assert "best_synthesis" in col_names
    assert "best_score" in col_names
    assert "computed_at" in col_names


def test_run_learning_columns():
    mapper = inspect(RunLearning)
    col_names = {c.key for c in mapper.columns}
    assert "run_id" in col_names
    assert "protocol_key" in col_names
    assert "question_categories" in col_names
    assert "eval_score" in col_names
    assert "config_json" in col_names
    assert "cost_usd" in col_names
    assert "synthesis_excerpt" in col_names


def test_protocol_insight_has_unique_constraint():
    constraints = ProtocolInsight.__table__.constraints
    unique_names = {c.name for c in constraints if hasattr(c, "name")}
    assert "uq_insights_lookup" in unique_names


def test_run_learning_has_gin_index():
    indexes = ProtocolInsight.__table__.indexes
    # Just verify indexes exist — GIN type is Postgres-specific
    index_names = {idx.name for idx in RunLearning.__table__.indexes}
    assert "ix_run_learnings_categories" in index_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "ce-db" && python -m pytest tests/test_insights_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'ProtocolInsight'`

- [ ] **Step 3: Create the models file**

```python
# ce-db/src/ce_db/models/insights.py
"""Protocol learning models — stores run outcomes and aggregated insights."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ce_db.models.core import Base


class ProtocolInsight(Base):
    """Aggregated learning from past protocol runs."""

    __tablename__ = "protocol_insights"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    protocol_key: Mapped[str] = mapped_column(String(100))
    question_category: Mapped[str] = mapped_column(String(50))
    insight_type: Mapped[str] = mapped_column(String(50))
    insight_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence: Mapped[float] = mapped_column(default=0.0)
    sample_size: Mapped[int] = mapped_column(default=0)
    best_synthesis: Mapped[str | None] = mapped_column(default=None)
    best_score: Mapped[float | None] = mapped_column(default=None)
    computed_at: Mapped[datetime] = mapped_column(default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        UniqueConstraint(
            "protocol_key", "question_category", "insight_type",
            name="uq_insights_lookup",
        ),
        Index(
            "ix_insights_lookup",
            "protocol_key", "question_category", "insight_type",
        ),
    )


class RunLearning(Base):
    """Per-run learning record for aggregation into insights."""

    __tablename__ = "run_learnings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String(100))  # Loose coupling — stores UUID or int as string
    protocol_key: Mapped[str] = mapped_column(String(100))
    question_categories: Mapped[list] = mapped_column(JSONB, default=list)
    eval_score: Mapped[float | None] = mapped_column(default=None)
    config_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    synthesis_excerpt: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    __table_args__ = (
        Index("ix_run_learnings_protocol", "protocol_key"),
        Index("ix_run_learnings_score", "eval_score"),
        Index(
            "ix_run_learnings_categories", "question_categories",
            postgresql_using="gin",
        ),
    )
```

- [ ] **Step 4: Update models __init__.py to export new models**

In `ce-db/src/ce_db/models/__init__.py`, add:
```python
from ce_db.models.insights import ProtocolInsight, RunLearning
```
And add both to `__all__`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd "ce-db" && python -m pytest tests/test_insights_models.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 6: Commit**

```bash
git add ce-db/src/ce_db/models/insights.py ce-db/src/ce_db/models/__init__.py ce-db/tests/test_insights_models.py
git commit -m "feat(ce-db): add ProtocolInsight and RunLearning models"
```

### Task 2: Create Alembic migration

**Files:**
- Create: `ce-db/alembic/versions/003_add_learning_tables.py`

- [ ] **Step 1: Generate migration**

Run: `cd "ce-db" && alembic revision -m "add_learning_tables"` and rename to `003_add_learning_tables.py`.

If autogenerate doesn't work (no DB connection), write manually:

```python
# ce-db/alembic/versions/003_add_learning_tables.py
"""Add protocol_insights and run_learnings tables."""

revision = "003"
down_revision = "002"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


def upgrade() -> None:
    op.create_table(
        "protocol_insights",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("protocol_key", sa.String(100), nullable=False),
        sa.Column("question_category", sa.String(50), nullable=False),
        sa.Column("insight_type", sa.String(50), nullable=False),
        sa.Column("insight_json", JSONB, server_default="{}"),
        sa.Column("confidence", sa.Float(), server_default="0.0"),
        sa.Column("sample_size", sa.Integer(), server_default="0"),
        sa.Column("best_synthesis", sa.Text(), nullable=True),
        sa.Column("best_score", sa.Float(), nullable=True),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "protocol_key", "question_category", "insight_type",
            name="uq_insights_lookup",
        ),
    )
    op.create_index(
        "ix_insights_lookup",
        "protocol_insights",
        ["protocol_key", "question_category", "insight_type"],
    )

    op.create_table(
        "run_learnings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.String(100), nullable=False),  # No FK — loose coupling across DB backends
        sa.Column("protocol_key", sa.String(100), nullable=False),
        sa.Column("question_categories", JSONB, server_default="[]"),
        sa.Column("eval_score", sa.Float(), nullable=True),
        sa.Column("config_json", JSONB, server_default="{}"),
        sa.Column("cost_usd", sa.Float(), server_default="0.0"),
        sa.Column("synthesis_excerpt", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_run_learnings_protocol", "run_learnings", ["protocol_key"])
    op.create_index("ix_run_learnings_score", "run_learnings", ["eval_score"])
    op.create_index(
        "ix_run_learnings_categories", "run_learnings",
        ["question_categories"], postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_table("run_learnings")
    op.drop_table("protocol_insights")
```

- [ ] **Step 2: Commit**

```bash
git add ce-db/alembic/versions/003_add_learning_tables.py
git commit -m "feat(ce-db): add migration for learning tables"
```

---

## Chunk 2: Question Classifier

### Task 3: Create classifier module

**Files:**
- Create: `CE - Multi-Agent Orchestration/protocols/learning/__init__.py`
- Create: `CE - Multi-Agent Orchestration/protocols/learning/classifier.py`
- Test: `CE - Multi-Agent Orchestration/tests/test_classifier.py`

- [ ] **Step 1: Create learning package**

```python
# CE - Multi-Agent Orchestration/protocols/learning/__init__.py
"""Protocol-level learning layer — pre/post hooks for run-to-run improvement."""
```

- [ ] **Step 2: Write failing tests for classifier**

```python
# CE - Multi-Agent Orchestration/tests/test_classifier.py
"""Tests for question classifier — unit tests only (no API calls)."""

import pytest

from protocols.learning.classifier import (
    QUESTION_CATEGORIES,
    _parse_categories,
)


class TestParseCategories:
    def test_valid_json_single(self):
        assert _parse_categories('["innovation"]') == ["innovation"]

    def test_valid_json_multiple(self):
        assert _parse_categories('["pricing", "financial"]') == ["pricing", "financial"]

    def test_markdown_fenced(self):
        assert _parse_categories('```json\n["risk"]\n```') == ["risk"]

    def test_invalid_category_filtered(self):
        assert _parse_categories('["innovation", "bogus"]') == ["innovation"]

    def test_all_invalid_returns_unclassified(self):
        assert _parse_categories('["bogus", "fake"]') == ["unclassified"]

    def test_malformed_json_returns_unclassified(self):
        assert _parse_categories("not json at all") == ["unclassified"]

    def test_empty_string_returns_unclassified(self):
        assert _parse_categories("") == ["unclassified"]

    def test_empty_array_returns_unclassified(self):
        assert _parse_categories("[]") == ["unclassified"]


def test_question_categories_is_nonempty_list():
    assert len(QUESTION_CATEGORIES) >= 5
    assert all(isinstance(c, str) for c in QUESTION_CATEGORIES)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd "CE - Multi-Agent Orchestration" && python -m pytest tests/test_classifier.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'protocols.learning'`

- [ ] **Step 4: Implement classifier**

```python
# CE - Multi-Agent Orchestration/protocols/learning/classifier.py
"""Classify questions into categories for insight matching."""

from __future__ import annotations

import json
import logging
import re

from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

QUESTION_CATEGORIES = [
    "innovation",
    "pricing",
    "risk",
    "strategy",
    "operations",
    "growth",
    "talent",
    "technology",
    "financial",
]

_CATEGORIES_STR = ", ".join(QUESTION_CATEGORIES)


async def classify_question(
    client: AsyncAnthropic,
    question: str,
    model: str = "claude-haiku-4-5-20251001",
) -> list[str]:
    """Classify question into 1-2 categories using Haiku. ~$0.001/call."""
    try:
        from protocols.llm import llm_complete

        response = await llm_complete(
            client,
            agent_name="classifier",
            model=model,
            messages=[{
                "role": "user",
                "content": (
                    f"Classify this business question into 1-2 categories.\n"
                    f"Categories: {_CATEGORIES_STR}\n\n"
                    f"Question: {question}\n\n"
                    f'Return ONLY a JSON array: ["category1"] or ["category1", "category2"]'
                ),
            }],
            max_tokens=50,
        )
        return _parse_categories(response)
    except Exception as e:
        logger.warning(f"classify_question failed: {e}")
        return ["unclassified"]


def _parse_categories(raw: str) -> list[str]:
    """Parse classifier response. Handles JSON, markdown fences, invalid categories."""
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            valid = [c for c in parsed if c in QUESTION_CATEGORIES]
            return valid if valid else ["unclassified"]
    except (json.JSONDecodeError, TypeError):
        pass
    return ["unclassified"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd "CE - Multi-Agent Orchestration" && python -m pytest tests/test_classifier.py -v`
Expected: PASS (all 9 tests)

- [ ] **Step 6: Commit**

```bash
git add "CE - Multi-Agent Orchestration/protocols/learning/__init__.py" \
       "CE - Multi-Agent Orchestration/protocols/learning/classifier.py" \
       "CE - Multi-Agent Orchestration/tests/test_classifier.py"
git commit -m "feat: add question classifier for protocol learning"
```

---

## Chunk 3: Retriever (Pre-Run Insights)

### Task 4: Create retriever module

**Files:**
- Create: `CE - Multi-Agent Orchestration/protocols/learning/retriever.py`
- Test: `CE - Multi-Agent Orchestration/tests/test_retriever.py`

- [ ] **Step 1: Write failing tests**

```python
# CE - Multi-Agent Orchestration/tests/test_retriever.py
"""Tests for insight retriever — unit tests with mock DB."""

import pytest
from unittest.mock import AsyncMock, patch

from protocols.learning.retriever import RunInsights, retrieve_insights


class TestRunInsights:
    def test_empty_insights_has_no_recommendations(self):
        insights = RunInsights(
            protocol_scores={},
            recommended_protocol=None,
            optimal_rounds=None,
            optimal_agents=None,
            thinking_budget=None,
            institutional_memory=None,
            confidence=0.0,
            sample_size=0,
        )
        assert not insights.has_recommendations

    def test_confident_insights_has_recommendations(self):
        insights = RunInsights(
            protocol_scores={"p06_triz": 4.2},
            recommended_protocol="p06_triz",
            optimal_rounds=3,
            optimal_agents=["ceo", "cfo"],
            thinking_budget=10000,
            institutional_memory="Past synthesis...",
            confidence=0.5,
            sample_size=5,
        )
        assert insights.has_recommendations

    def test_serializes_to_dict(self):
        insights = RunInsights(
            protocol_scores={}, recommended_protocol=None,
            optimal_rounds=None, optimal_agents=None, thinking_budget=None,
            institutional_memory=None, confidence=0.0, sample_size=0,
        )
        d = insights.model_dump()
        assert "protocol_scores" in d
        assert "confidence" in d


@pytest.mark.asyncio
async def test_retrieve_insights_graceful_on_db_failure():
    """When DB is unavailable, returns empty insights (not an exception)."""
    with patch("protocols.learning.retriever.get_session", side_effect=Exception("no db")):
        result = await retrieve_insights("p06_triz", "test question", ["innovation"])
    assert result.confidence == 0.0
    assert result.sample_size == 0
    assert result.institutional_memory is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "CE - Multi-Agent Orchestration" && python -m pytest tests/test_retriever.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement retriever**

```python
# CE - Multi-Agent Orchestration/protocols/learning/retriever.py
"""Retrieve learning insights before a protocol run."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select, text

logger = logging.getLogger(__name__)


class RunInsights(BaseModel):
    """Pre-run insights retrieved from past protocol runs."""

    protocol_scores: dict[str, float] = {}
    recommended_protocol: str | None = None
    optimal_rounds: int | None = None
    optimal_agents: list[str] | None = None
    thinking_budget: int | None = None
    institutional_memory: str | None = None
    confidence: float = 0.0
    sample_size: int = 0

    @property
    def has_recommendations(self) -> bool:
        return self.confidence > 0.3 and self.sample_size >= 3


_EMPTY = RunInsights()


async def retrieve_insights(
    protocol_key: str,
    question: str,
    question_categories: list[str],
) -> RunInsights:
    """Retrieve relevant learning before a protocol run. Returns empty on failure."""
    try:
        from ce_db.session import get_session
        from ce_db.models.insights import ProtocolInsight

        async with get_session() as session:
            scores = await _get_protocol_scores(session, question_categories)
            config = await _get_config_insight(session, protocol_key, question_categories)
            contextual = await _get_best_contextual(session, protocol_key, question_categories)

            sample_size = sum(v["n"] for v in scores.values()) if scores else 0

            return RunInsights(
                protocol_scores={k: v["avg_score"] for k, v in scores.items()},
                recommended_protocol=_pick_best(scores, protocol_key),
                optimal_rounds=config.get("optimal_rounds") if config else None,
                optimal_agents=config.get("optimal_agents") if config else None,
                thinking_budget=config.get("thinking_budget") if config else None,
                institutional_memory=contextual.best_synthesis if contextual else None,
                confidence=min(1.0, sample_size / 20),
                sample_size=sample_size,
            )
    except Exception as e:
        logger.warning(f"retrieve_insights failed (degrading gracefully): {e}")
        return _EMPTY


async def _get_protocol_scores(
    session: Any, categories: list[str],
) -> dict[str, dict[str, float]]:
    """Get avg scores per protocol for given categories."""
    from ce_db.models.insights import ProtocolInsight

    stmt = (
        select(ProtocolInsight)
        .where(
            ProtocolInsight.question_category.in_(categories),
            ProtocolInsight.insight_type == "protocol_comparison",
        )
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()

    scores: dict[str, dict] = {}
    for row in rows:
        pk = row.protocol_key
        data = row.insight_json or {}
        if pk not in scores:
            scores[pk] = {"avg_score": data.get("avg_score", 0), "n": row.sample_size}
        else:
            # Average across categories
            existing = scores[pk]
            total_n = existing["n"] + row.sample_size
            existing["avg_score"] = (
                (existing["avg_score"] * existing["n"] + data.get("avg_score", 0) * row.sample_size)
                / total_n
            ) if total_n > 0 else 0
            existing["n"] = total_n
    return scores


async def _get_config_insight(
    session: Any, protocol_key: str, categories: list[str],
) -> dict | None:
    """Get config tuning insight for a specific protocol+categories."""
    from ce_db.models.insights import ProtocolInsight

    stmt = (
        select(ProtocolInsight)
        .where(
            ProtocolInsight.protocol_key == protocol_key,
            ProtocolInsight.question_category.in_(categories),
            ProtocolInsight.insight_type == "config_tuning",
        )
        .order_by(ProtocolInsight.confidence.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return row.insight_json if row else None


async def _get_best_contextual(
    session: Any, protocol_key: str, categories: list[str],
) -> Any | None:
    """Get highest-scored contextual insight across categories."""
    from ce_db.models.insights import ProtocolInsight

    stmt = (
        select(ProtocolInsight)
        .where(
            ProtocolInsight.protocol_key == protocol_key,
            ProtocolInsight.question_category.in_(categories),
            ProtocolInsight.insight_type == "contextual",
            ProtocolInsight.best_score.isnot(None),
        )
        .order_by(ProtocolInsight.best_score.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _pick_best(
    scores: dict[str, dict[str, float]], current_protocol: str,
) -> str | None:
    """Pick the best-performing protocol, or None if current is already best."""
    if not scores:
        return None
    best_key = max(scores, key=lambda k: scores[k]["avg_score"])
    if best_key == current_protocol:
        return None
    # Only recommend if meaningfully better (>0.3 score gap)
    current_score = scores.get(current_protocol, {}).get("avg_score", 0)
    if scores[best_key]["avg_score"] - current_score > 0.3:
        return best_key
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "CE - Multi-Agent Orchestration" && python -m pytest tests/test_retriever.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
git add "CE - Multi-Agent Orchestration/protocols/learning/retriever.py" \
       "CE - Multi-Agent Orchestration/tests/test_retriever.py"
git commit -m "feat: add pre-run insight retriever for protocol learning"
```

---

## Chunk 4: Recorder (Post-Run Learning)

### Task 5: Create recorder module

**Files:**
- Create: `CE - Multi-Agent Orchestration/protocols/learning/recorder.py`
- Test: `CE - Multi-Agent Orchestration/tests/test_recorder.py`

- [ ] **Step 1: Write failing tests**

```python
# CE - Multi-Agent Orchestration/tests/test_recorder.py
"""Tests for post-run learning recorder — unit tests with mock DB."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from protocols.learning.recorder import record_learning


@pytest.mark.asyncio
async def test_record_learning_graceful_on_db_failure():
    """When DB is unavailable, logs warning and returns None."""
    with patch("protocols.learning.recorder.get_session", side_effect=Exception("no db")):
        result = await record_learning(
            run_id=uuid.uuid4(),
            protocol_key="p06_triz",
            question="test",
            question_categories=["innovation"],
            eval_score=4.0,
            config={"rounds": 3},
            synthesis_text="Great synthesis",
            cost_summary={"total_usd": 1.0},
        )
    assert result is None


@pytest.mark.asyncio
async def test_record_learning_stores_without_score():
    """Runs with eval_score=None are stored but don't update best synthesis."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("protocols.learning.recorder.get_session", return_value=mock_session):
        await record_learning(
            run_id=uuid.uuid4(),
            protocol_key="p06_triz",
            question="test",
            question_categories=["innovation"],
            eval_score=None,
            config={},
            synthesis_text="Some output",
            cost_summary={"total_usd": 0.5},
        )
    # Should have added a RunLearning record and committed
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "CE - Multi-Agent Orchestration" && python -m pytest tests/test_recorder.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement recorder**

```python
# CE - Multi-Agent Orchestration/protocols/learning/recorder.py
"""Record protocol run outcomes for future learning."""

from __future__ import annotations

import logging
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select

logger = logging.getLogger(__name__)


async def record_learning(
    run_id: str | int | None,
    protocol_key: str,
    question: str,
    question_categories: list[str],
    eval_score: float | None,
    config: dict,
    synthesis_text: str,
    cost_summary: dict,
) -> None:
    """Store run outcome for future learning. Non-blocking."""
    try:
        from ce_db.session import get_session
        from ce_db.models.insights import ProtocolInsight, RunLearning

        async with get_session() as session:
            learning = RunLearning(
                run_id=str(run_id) if run_id else "unknown",
                protocol_key=protocol_key,
                question_categories=question_categories,
                eval_score=eval_score,
                config_json=config,
                cost_usd=cost_summary.get("total_usd", 0.0),
                synthesis_excerpt=synthesis_text[:2000] if synthesis_text else None,
            )
            session.add(learning)

            # Don't update insights without a score — record still saved
            if eval_score is None:
                return

            for cat in question_categories:
                existing = await _get_contextual_insight_single(session, protocol_key, cat)
                if existing is None or eval_score > (existing.best_score or 0):
                    await _upsert_contextual_insight(
                        session, protocol_key, cat,
                        best_synthesis=synthesis_text[:3000] if synthesis_text else None,
                        best_score=eval_score,
                    )

            run_count = await _count_runs_since_last_compute(
                session, protocol_key, question_categories,
            )
            if run_count >= 5:
                await _recompute_insights(session, protocol_key, question_categories)

            # No explicit commit — get_session() context manager auto-commits on exit
    except Exception as e:
        logger.warning(f"record_learning failed (non-blocking): {e}")


async def _get_contextual_insight_single(
    session: Any, protocol_key: str, category: str,
) -> Any | None:
    from ce_db.models.insights import ProtocolInsight

    stmt = select(ProtocolInsight).where(
        ProtocolInsight.protocol_key == protocol_key,
        ProtocolInsight.question_category == category,
        ProtocolInsight.insight_type == "contextual",
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _upsert_contextual_insight(
    session: Any,
    protocol_key: str,
    category: str,
    best_synthesis: str | None,
    best_score: float,
) -> None:
    from ce_db.models.insights import ProtocolInsight

    existing = await _get_contextual_insight_single(session, protocol_key, category)
    if existing:
        existing.best_synthesis = best_synthesis
        existing.best_score = best_score
        existing.computed_at = datetime.now(timezone.utc)
    else:
        session.add(ProtocolInsight(
            protocol_key=protocol_key,
            question_category=category,
            insight_type="contextual",
            insight_json={},
            confidence=0.0,
            sample_size=1,
            best_synthesis=best_synthesis,
            best_score=best_score,
            computed_at=datetime.now(timezone.utc),
        ))


async def _count_runs_since_last_compute(
    session: Any, protocol_key: str, categories: list[str],
) -> int:
    from ce_db.models.insights import ProtocolInsight, RunLearning

    last_compute_stmt = (
        select(func.max(ProtocolInsight.computed_at))
        .where(
            ProtocolInsight.protocol_key == protocol_key,
            ProtocolInsight.insight_type == "protocol_comparison",
        )
    )
    result = await session.execute(last_compute_stmt)
    last_computed = result.scalar_one_or_none()

    count_stmt = (
        select(func.count())
        .select_from(RunLearning)
        .where(RunLearning.protocol_key == protocol_key)
    )
    if last_computed:
        count_stmt = count_stmt.where(RunLearning.created_at > last_computed)
    result = await session.execute(count_stmt)
    return result.scalar_one()


async def _recompute_insights(
    session: Any, protocol_key: str, categories: list[str],
) -> None:
    """Recompute protocol_comparison and config_tuning insights."""
    from ce_db.models.insights import ProtocolInsight, RunLearning

    now = datetime.now(timezone.utc)

    for cat in categories:
        if cat == "unclassified":
            continue

        # Protocol comparison: avg score per protocol for this category
        comparison_stmt = (
            select(
                RunLearning.protocol_key,
                func.avg(RunLearning.eval_score).label("avg_score"),
                func.count().label("n"),
            )
            .where(
                RunLearning.eval_score.isnot(None),
                RunLearning.question_categories.op("@>")(f'["{cat}"]'),
            )
            .group_by(RunLearning.protocol_key)
            .having(func.count() >= 3)
        )
        result = await session.execute(comparison_stmt)
        for row in result:
            sample_size = row.n
            await _upsert_insight(
                session,
                protocol_key=row.protocol_key,
                category=cat,
                insight_type="protocol_comparison",
                insight_json={"avg_score": float(row.avg_score), "n": sample_size},
                confidence=min(1.0, sample_size / 20),
                sample_size=sample_size,
                now=now,
            )

        # Config tuning: avg score by rounds for this protocol+category
        config_stmt = (
            select(
                RunLearning.config_json["rounds"].as_string().label("rounds"),
                func.avg(RunLearning.eval_score).label("avg_score"),
                func.avg(RunLearning.cost_usd).label("avg_cost"),
                func.count().label("n"),
            )
            .where(
                RunLearning.protocol_key == protocol_key,
                RunLearning.eval_score.isnot(None),
                RunLearning.question_categories.op("@>")(f'["{cat}"]'),
            )
            .group_by(RunLearning.config_json["rounds"].as_string())
        )
        result = await session.execute(config_stmt)
        configs = {row.rounds: {"avg_score": float(row.avg_score), "avg_cost": float(row.avg_cost), "n": row.n} for row in result}

        if configs:
            best_rounds = max(configs, key=lambda k: configs[k]["avg_score"])
            total_n = sum(c["n"] for c in configs.values())
            await _upsert_insight(
                session,
                protocol_key=protocol_key,
                category=cat,
                insight_type="config_tuning",
                insight_json={
                    "optimal_rounds": int(best_rounds) if best_rounds and best_rounds != "None" else None,
                    "scores_by_rounds": configs,
                },
                confidence=min(1.0, total_n / 20),
                sample_size=total_n,
                now=now,
            )


async def _upsert_insight(
    session: Any, protocol_key: str, category: str,
    insight_type: str, insight_json: dict, confidence: float,
    sample_size: int, now: datetime,
) -> None:
    from ce_db.models.insights import ProtocolInsight

    stmt = select(ProtocolInsight).where(
        ProtocolInsight.protocol_key == protocol_key,
        ProtocolInsight.question_category == category,
        ProtocolInsight.insight_type == insight_type,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.insight_json = insight_json
        existing.confidence = confidence
        existing.sample_size = sample_size
        existing.computed_at = now
    else:
        session.add(ProtocolInsight(
            protocol_key=protocol_key,
            question_category=category,
            insight_type=insight_type,
            insight_json=insight_json,
            confidence=confidence,
            sample_size=sample_size,
            computed_at=now,
        ))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "CE - Multi-Agent Orchestration" && python -m pytest tests/test_recorder.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add "CE - Multi-Agent Orchestration/protocols/learning/recorder.py" \
       "CE - Multi-Agent Orchestration/tests/test_recorder.py"
git commit -m "feat: add post-run learning recorder with insight recomputation"
```

---

## Chunk 5: Hooks + Integration

### Task 6: Create hooks helper

**Files:**
- Create: `CE - Multi-Agent Orchestration/protocols/learning/hooks.py`
- Test: `CE - Multi-Agent Orchestration/tests/test_hooks.py`

- [ ] **Step 1: Write failing tests**

```python
# CE - Multi-Agent Orchestration/tests/test_hooks.py
"""Tests for pre/post run hooks."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from protocols.learning.hooks import pre_run_hook, post_run_hook


@pytest.mark.asyncio
async def test_pre_run_hook_returns_categories():
    with patch("protocols.learning.hooks.classify_question", return_value=["innovation"]), \
         patch("protocols.learning.hooks.retrieve_insights") as mock_retrieve:
        mock_retrieve.return_value = MagicMock(
            recommended_protocol=None,
            confidence=0.0,
            institutional_memory=None,
            optimal_rounds=None,
        )
        config, cats = await pre_run_hook(
            client=AsyncMock(),
            protocol_key="p06_triz",
            question="How to innovate?",
            agents=[],
            user_config={},
        )
    assert cats == ["innovation"]


@pytest.mark.asyncio
async def test_pre_run_hook_injects_memory_into_agents():
    mock_agent = MagicMock()
    mock_agent.institutional_memory = None

    with patch("protocols.learning.hooks.classify_question", return_value=["strategy"]), \
         patch("protocols.learning.hooks.retrieve_insights") as mock_retrieve:
        mock_retrieve.return_value = MagicMock(
            recommended_protocol=None,
            confidence=0.8,
            institutional_memory="Past synthesis text",
            optimal_rounds=None,
            protocol_scores={},
            sample_size=10,
        )
        _, _ = await pre_run_hook(
            client=AsyncMock(),
            protocol_key="p04_multi_round_debate",
            question="Strategy question",
            agents=[mock_agent],
            user_config={},
        )
    assert mock_agent.institutional_memory == "Past synthesis text"


@pytest.mark.asyncio
async def test_post_run_hook_graceful_on_failure():
    with patch("protocols.learning.hooks.record_learning", side_effect=Exception("boom")):
        # Should not raise
        await post_run_hook(
            run_id=uuid.uuid4(),
            protocol_key="p06_triz",
            question="test",
            question_categories=["innovation"],
            eval_score=4.0,
            config={},
            synthesis_text="",
            cost_summary={},
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "CE - Multi-Agent Orchestration" && python -m pytest tests/test_hooks.py -v`
Expected: FAIL

- [ ] **Step 3: Implement hooks**

```python
# CE - Multi-Agent Orchestration/protocols/learning/hooks.py
"""Pre/post run hooks for protocol learning layer."""

from __future__ import annotations

import logging
import uuid as uuid_mod
from typing import Any

from anthropic import AsyncAnthropic

from protocols.learning.classifier import classify_question
from protocols.learning.recorder import record_learning
from protocols.learning.retriever import RunInsights, retrieve_insights

logger = logging.getLogger(__name__)


async def pre_run_hook(
    client: AsyncAnthropic,
    protocol_key: str,
    question: str,
    agents: list[Any],
    user_config: dict,
) -> tuple[dict, list[str]]:
    """Pre-run: classify, retrieve insights, inject into agents."""
    try:
        categories = await classify_question(client, question)
        insights = await retrieve_insights(protocol_key, question, categories)

        if insights.recommended_protocol and insights.recommended_protocol != protocol_key:
            logger.info(
                f"[Learning] {insights.recommended_protocol} scored "
                f"{insights.protocol_scores.get(insights.recommended_protocol, '?'):.1f} avg "
                f"vs {protocol_key} at "
                f"{insights.protocol_scores.get(protocol_key, '?')} "
                f"for {categories} (n={insights.sample_size})"
            )

        updated_config = dict(user_config)
        if insights.confidence > 0.6:
            if insights.optimal_rounds and not user_config.get("rounds"):
                updated_config["rounds"] = insights.optimal_rounds
                logger.info(f"[Learning] Auto-set rounds={insights.optimal_rounds}")

        if insights.institutional_memory:
            for agent in agents:
                if hasattr(agent, "institutional_memory"):
                    agent.institutional_memory = insights.institutional_memory

        return updated_config, categories
    except Exception as e:
        logger.warning(f"pre_run_hook failed (degrading): {e}")
        return dict(user_config), ["unclassified"]


async def post_run_hook(
    run_id: str | int | None,
    protocol_key: str,
    question: str,
    question_categories: list[str],
    eval_score: float | None,
    config: dict,
    synthesis_text: str,
    cost_summary: dict,
) -> None:
    """Post-run: record learning. Non-blocking."""
    try:
        await record_learning(
            run_id=run_id,
            protocol_key=protocol_key,
            question=question,
            question_categories=question_categories,
            eval_score=eval_score,
            config=config,
            synthesis_text=synthesis_text,
            cost_summary=cost_summary,
        )
    except Exception as e:
        logger.warning(f"post_run_hook failed (non-blocking): {e}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "CE - Multi-Agent Orchestration" && python -m pytest tests/test_hooks.py -v`
Expected: PASS (all 3 tests)

- [ ] **Step 5: Commit**

```bash
git add "CE - Multi-Agent Orchestration/protocols/learning/hooks.py" \
       "CE - Multi-Agent Orchestration/tests/test_hooks.py"
git commit -m "feat: add pre/post run hooks for protocol learning"
```

### Task 7: Modify ServerAgent to accept institutional_memory

**Files:**
- Modify: `CE - Multi-Agent Orchestration/protocols/server_agent.py:182-191` (init) and `:199-236` (build_system_prompt)

- [ ] **Step 1: Add `institutional_memory` attribute to `__init__`**

At line ~191 in `server_agent.py`, after `self._client`, add:
```python
self.institutional_memory: str | None = None
```

- [ ] **Step 2: Add institutional memory section to `_build_system_prompt`**

At line ~235, before the final `return "\n\n".join(sections)` (line 236), add:
```python
if self.institutional_memory:
    sections.append(
        "## Institutional Memory -- Past Protocol Insights\n\n"
        "The following is a high-quality synthesis from a previous run "
        "on a similar question. Use it as context, not as a template. "
        "Build on its strengths and address its gaps.\n\n"
        f"{self.institutional_memory}"
    )
```

- [ ] **Step 3: Verify existing tests still pass**

Run: `cd "CE - Multi-Agent Orchestration" && python -m pytest tests/ -m "not integration" -v --timeout=30 -x`
Expected: All existing tests PASS (no regression)

- [ ] **Step 4: Commit**

```bash
git add "CE - Multi-Agent Orchestration/protocols/server_agent.py"
git commit -m "feat: add institutional_memory support to ServerAgent system prompt"
```

### Task 8: Integrate hooks into api/runner.py

**Files:**
- Modify: `CE - Multi-Agent Orchestration/api/runner.py`

The runner function is `run_protocol_stream()` (line 209). Key variable names from the actual code:
- `run_id: int` — SQLModel auto-increment ID (NOT uuid)
- `protocol_key: str`, `question: str`, `agent_keys: list[str]`
- `agents` — built at line 237 via `build_production_agents(agent_keys)`
- `kwargs` — orchestrator kwargs dict (line 244), includes `rounds` if set
- `cost_tracker` — the ProtocolCostTracker instance
- `envelope` — RunEnvelope with `.result_summary`
- `verdict` — scoped inside judge try/except block (line 364), may not exist
- `persist_outcome` — from `persist_run()` at line 437, has `.run_id: str | None`

- [ ] **Step 1: Add import at top of runner.py**

Near the other protocol imports (around line 33-36), add:
```python
from protocols.learning.hooks import pre_run_hook, post_run_hook
```

- [ ] **Step 2: Add pre_run_hook after agents are built (line ~237)**

After `agents = build_production_agents(agent_keys)` (line 237), add:
```python
        # Protocol learning: classify question + retrieve insights + inject memory
        _learning_categories = ["unclassified"]
        try:
            from protocols.tracing import make_client as _make_learning_client
            _learning_client = _make_learning_client(protocol_id="learning")
            _user_config = {"rounds": rounds}
            _user_config, _learning_categories = await pre_run_hook(
                client=_learning_client,
                protocol_key=protocol_key,
                question=question,
                agents=agents,
                user_config=_user_config,
            )
            if _user_config.get("rounds") and rounds is None:
                rounds = _user_config["rounds"]
        except Exception:
            pass  # Learning hooks are non-blocking
```

- [ ] **Step 3: Add post_run_hook after persist_run block (after line ~454)**

After the `persist_outcome` block (after line 454), add. Note: `verdict` is scoped inside the judge try/except, so capture it at a higher scope first.

At line ~354 (before the judge block), add:
```python
        _judge_overall: float | None = None
```

Inside the judge try/except, after `verdict = await judge.evaluate(...)` (line 364), add:
```python
                _judge_overall = float(verdict.overall)
```

Then after the persist_outcome block (after line ~464), add:
```python
        # Protocol learning: record run outcome
        await post_run_hook(
            run_id=persist_outcome.run_id if persist_outcome and persist_outcome.run_id else str(run_id),
            protocol_key=protocol_key,
            question=question,
            question_categories=_learning_categories,
            eval_score=_judge_overall,
            config={"rounds": rounds, "agents": agent_keys, "thinking_model": thinking_model},
            synthesis_text=envelope.result_summary or "",
            cost_summary=cost_tracker.summary() if cost_tracker else {},
        )
```

- [ ] **Step 4: Run existing tests**

Run: `cd "CE - Multi-Agent Orchestration" && python -m pytest tests/ -m "not integration" -v --timeout=30 -x`
Expected: PASS (no regression)

- [ ] **Step 5: Commit**

```bash
git add "CE - Multi-Agent Orchestration/api/runner.py"
git commit -m "feat: integrate protocol learning hooks into API runner"
```

> **Deferred:** `LEARNING_AUTO_SCORE` env-var-gated auto-scoring for CLI runs without QualityJudge. CLI runs will store `eval_score=None` and be excluded from score-based aggregations. Add auto-scoring when CLI usage warrants it.
>
> **Note:** Pipeline runs (`run_pipeline_stream`) are explicitly deferred. Pipelines chain multiple protocols — the learning layer should first prove value on single-protocol runs before adding pipeline complexity. Pipeline integration can be added later with the same `pre_run_hook/post_run_hook` pattern per pipeline step.

---

## Chunk 6: End-to-End Verification

### Task 9: Run all tests and verify cold start behavior

- [ ] **Step 1: Run full test suite**

```bash
cd "CE - Multi-Agent Orchestration" && python -m pytest tests/ -m "not integration" -v --timeout=60
```
Expected: All tests PASS

- [ ] **Step 2: Run ce-db tests**

```bash
cd "ce-db" && python -m pytest tests/ -v --timeout=30
```
Expected: All tests PASS

- [ ] **Step 3: Verify cold start — import learning modules**

```bash
cd "CE - Multi-Agent Orchestration" && python -c "
from protocols.learning.hooks import pre_run_hook, post_run_hook
from protocols.learning.classifier import classify_question, _parse_categories
from protocols.learning.retriever import RunInsights, retrieve_insights
from protocols.learning.recorder import record_learning
print('All learning modules import successfully')
"
```
Expected: Prints success message with no errors

- [ ] **Step 4: Verify graceful degradation without DB**

```bash
cd "CE - Multi-Agent Orchestration" && python -c "
import asyncio
from protocols.learning.retriever import retrieve_insights, RunInsights
result = asyncio.run(retrieve_insights('p06_triz', 'test', ['innovation']))
assert isinstance(result, RunInsights)
assert result.confidence == 0.0
assert result.institutional_memory is None
print('Graceful degradation: PASS')
"
```
Expected: Prints "Graceful degradation: PASS"

- [ ] **Step 5: Final commit with all tests passing**

```bash
git add -A
git commit -m "test: verify protocol learning layer end-to-end"
```

- [ ] **Step 6: Push**

```bash
git push
```
