# Codebase Conventions

Purpose: Document code style, naming patterns, error handling, import conventions, async patterns, Pydantic usage, and prompt patterns across the CE-AGENTS monorepo.

---

## 1. Python Version and Build Systems

All projects target **Python >= 3.11**. The monorepo uses two build backends:

| Project | Build Backend | Config File |
|---------|---------------|-------------|
| CE - Agent Builder | hatchling | `CE - Agent Builder/pyproject.toml` |
| CE - Evals | setuptools | `CE - Evals/pyproject.toml` |
| ce-db | setuptools | `ce-db/pyproject.toml` |
| CE - Multi-Agent Orchestration | none (script-based) | `requirements.txt` |

Source layout uses `src/` for installable packages:
- `CE - Agent Builder/src/csuite/`
- `CE - Evals/src/ce_evals/`
- `ce-db/src/ce_db/`

The orchestration project has no `src/` layout -- protocols are imported as `protocols.*` with `sys.path` manipulation.

---

## 2. Linting and Formatting (Ruff)

Configured in `CE - Agent Builder/pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.ruff.lint.per-file-ignores]
"src/csuite/prompts/*.py" = ["E501"]  # Long lines allowed in prompt files
```

Rules enabled:
- **E** / **W**: pycodestyle errors and warnings
- **F**: pyflakes (unused imports, undefined names)
- **I**: isort (import ordering)
- **N**: pep8-naming
- **UP**: pyupgrade (modernize syntax for Python 3.11+)

Orchestration CI runs ruff with `--ignore E402` (module-level imports not at top) because protocol modules manipulate `sys.path` before imports.

---

## 3. Type Checking (mypy)

Configured in `CE - Agent Builder/pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.11"
warn_unused_configs = true
warn_redundant_casts = true
check_untyped_defs = true
disable_error_code = ["union-attr", "no-any-return"]
```

Key decisions:
- **Not strict mode** -- uses `check_untyped_defs` rather than full `--strict`.
- `union-attr` disabled globally because Anthropic SDK response blocks return union types.
- `no-any-return` disabled globally for tool modules with dynamic dict returns.
- Tool modules (`csuite.tools.*`) have broad error code suppression (see `pyproject.toml` overrides).
- `claude_agent_sdk` and related imports use `ignore_missing_imports = true`.

---

## 4. Import Conventions

### Standard import order (enforced by ruff I rule):
1. Standard library
2. Third-party packages
3. Local/project imports

### `from __future__ import annotations`
Used consistently in files that need forward references or `X | None` union syntax at runtime:

```python
from __future__ import annotations
```

### TYPE_CHECKING guard
Used in factory modules to avoid circular imports:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csuite.agents.base import BaseAgent
    from csuite.tools.cost_tracker import CostTracker
```

### Lazy imports
Heavy dependencies are imported inside functions to avoid import-time cost or to handle optional deps:

```python
def _self_evaluate(self, artifact_text: str) -> None:
    try:
        from csuite.learning.feedback_loop import FeedbackStore, SelfEvaluator
        # ...
    except Exception:
        logger.debug("Self-evaluation skipped", exc_info=True)
```

---

## 5. Naming Conventions

### Files and modules
- Protocols: `p{NN}_{descriptor}/` (e.g., `p06_triz`, `p16_ach`, `p29_pmi_enumeration`)
- Agent files: `{role}.py` (e.g., `ceo.py`, `cfo.py`)
- Prompt files: `{role}_prompt.py` (e.g., `ceo_prompt.py`)

### Classes
- Agent classes: `{Role}Agent` (e.g., `CEOAgent`, `CFOAgent`)
- Orchestrator classes: `{Name}Orchestrator` (e.g., `TRIZOrchestrator`, `SynthesisOrchestrator`)
- Result dataclasses: `{Protocol}Result` (e.g., `TRIZResult`, `DebateResult`)
- Pydantic models: PascalCase nouns (e.g., `Session`, `Message`, `Settings`, `JudgeResult`)

### Variables and functions
- Agent keys: kebab-case strings (e.g., `"ceo-board-prep"`, `"gtm-vp-sales"`)
- Model constants: SCREAMING_SNAKE_CASE (e.g., `THINKING_MODEL`, `ORCHESTRATION_MODEL`, `HAIKU_MODEL`)
- Prompt constants: SCREAMING_SNAKE_CASE (e.g., `CEO_SYSTEM_PROMPT`, `DEDUPLICATION_PROMPT`)
- Factory functions: `create_*` or `get_*` (e.g., `create_agent()`, `get_settings()`)
- Private helpers: `_leading_underscore` (e.g., `_make_mock_client`, `_load_business_context`)

### Config singletons
Settings objects use `@lru_cache` or module-level `_settings` variable for singleton pattern:

```python
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

---

## 6. Async Patterns

### Core principle
All LLM calls and agent interactions are async. The codebase uses `anthropic.AsyncAnthropic` (orchestration) and `anthropic.Anthropic` with async wrappers (agent builder).

### Parallel agent execution
Agents run in parallel via `asyncio.gather()`:

```python
results = await asyncio.gather(
    *[agent_complete(agent, model, messages) for agent in self.agents]
)
```

### CLI entry points
CLIs wrap async orchestrators with `asyncio.run()`:

```python
if __name__ == "__main__":
    asyncio.run(main())
```

### Concurrency safety
BaseAgent uses `asyncio.Lock` to prevent concurrent session mutation:

```python
self._chat_lock = asyncio.Lock()

async def chat(self, user_message: str) -> str:
    async with self._chat_lock:
        # ...
```

### pytest-asyncio
Tests use `asyncio_mode = "auto"` (configured in `pyproject.toml`), so test functions marked `@pytest.mark.asyncio` run automatically in an event loop.

---

## 7. Pydantic Usage

### Version
**Pydantic v2** across all projects (`pydantic>=2.0.0`).

### Settings pattern
All projects use `pydantic-settings` for environment configuration:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = Field(..., description="Anthropic API key")
    default_model: str = Field(default="claude-opus-4-6")
```

`extra="ignore"` is standard -- unknown env vars are silently ignored.

### Data models
Session and message types use Pydantic `BaseModel` with `Field(default_factory=...)`:

```python
class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    messages: list[Message] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### Eval models
CE-Evals uses Pydantic models for structured data passing:

```python
class JudgeResult(BaseModel):
    scores: dict[str, dict[str, float]] = Field(default_factory=dict)
    ranking: list[str] = Field(default_factory=list)
    judge_reasoning: str = ""
```

### Orchestration results
Orchestration protocols use **dataclasses** (not Pydantic) for result types:

```python
@dataclass
class TRIZResult:
    question: str
    failure_modes: list[FailureMode] = field(default_factory=list)
    solutions: list[Solution] = field(default_factory=list)
    synthesis: str = ""
```

**Convention**: Agent Builder and Evals use Pydantic; Orchestration uses dataclasses.

---

## 8. Error Handling

### Graceful degradation pattern
External API calls use a layered resilience stack (`CE - Agent Builder/src/csuite/tools/resilience.py`):

1. **Cache check** (TTL-based in-memory cache)
2. **Circuit breaker** (fail-fast after repeated failures)
3. **Retry with exponential backoff + jitter**
4. **Graceful fallback** (return `DegradedResult` instead of raising)

```python
@resilient(api_name="sec_edgar", cache_ttl=300)
async def get_company_info(ticker):
    ...
```

### API error handling in agents
`BaseAgent.chat()` catches Anthropic-specific errors and returns user-friendly strings:

```python
except anthropic.APIError as e:
    logger.error("Anthropic API error for %s: %s", self.ROLE, e.message)
    return f"API error: {e.message}. Please check your API key and try again."
except Exception:
    logger.exception("Unexpected error in %s.chat()", self.ROLE)
    return "I encountered an error processing your request. Please try again."
```

### Silent degradation for optional subsystems
Memory, learning, tracing, and persistence systems use try/except with logging:

```python
try:
    from csuite.memory.extractor import extract_memories
    memories = extract_memories(assistant_message, self.ROLE)
    # ...
except Exception:
    logger.warning("Post-response memory storage failed", exc_info=True)
```

### Retry configuration
Retryable exceptions are explicitly listed (not broad catches):

```python
retryable_exceptions=(
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.APIConnectionError,
    ConnectionError,
    TimeoutError,
)
```

---

## 9. Prompt Patterns

### Prompt storage
Prompts live in dedicated files, exported as module-level string constants:
- Agent Builder: `src/csuite/prompts/{role}_prompt.py` exports `{ROLE}_SYSTEM_PROMPT`
- Orchestration: `protocols/p{NN}_{name}/prompts.py` exports stage-specific prompts

### Prompt composition
`BaseAgent._build_system_prompt()` assembles the full prompt from sections:

```python
sections = [base_prompt]
if self.business_context:
    sections.append(f"## Business Context\n\n{self.business_context}")
if memories:
    sections.append("## Institutional Memory\n\n...")
if lessons:
    sections.append(f"## Lessons Learned\n\n{lessons}")
return "\n\n".join(sections)
```

### E501 exemption
Prompt files are exempt from line-length limits (`per-file-ignores` in ruff config).

---

## 10. Model Policy

- **Executive agents**: `claude-opus-4-6` (mandatory for strategic thinking)
- **Orchestration/mechanical steps**: `claude-haiku-4-5-20251001` (dedup, ranking, extraction)
- **Temperature varies by role**: CFO=0.5 (precise), CEO/CTO/COO/CPO=0.6 (balanced), CMO=0.8 (creative)

Model selection is centralized in `CE - Agent Builder/src/csuite/config.py` via the `AGENT_CONFIGS` dict.

---

## 11. Database Patterns

### ce-db (shared layer)
Uses async SQLAlchemy 2.0 with `asyncpg`:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

_engine: AsyncEngine | None = None

def get_engine() -> AsyncEngine | None:
    global _engine
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5)
    return _engine
```

ORM models use `Mapped` type annotations (SQLAlchemy 2.0 style):

```python
class Run(Base):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    protocol_key: Mapped[str] = mapped_column(String(100))
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

### DuckDB (Agent Builder local storage)
Used for lightweight local state (sessions, experience logs, preferences):

```python
from csuite.storage.duckdb_store import DuckDBStore
```

---

## 12. Logging

Standard library `logging` throughout. Named loggers per module:

```python
logger = logging.getLogger(__name__)
```

Structured JSON logging for API resilience layer:

```python
record = {
    "timestamp": datetime.now().isoformat(),
    "api": api_name,
    "endpoint": endpoint,
    "status": status,
    "duration_ms": round(duration_ms, 2),
}
log_line = json.dumps(record)
```

---

## 13. Agent Architecture Pattern

### Agent Builder -- Subclass pattern
Each agent is a thin subclass of `BaseAgent` with a `ROLE` class variable and `get_system_prompt()`:

```python
class CEOAgent(BaseAgent):
    ROLE = "ceo"

    def get_system_prompt(self) -> str:
        return CEO_SYSTEM_PROMPT
```

### Factory routing
`create_agent(role)` routes to legacy `BaseAgent` subclass or `SdkAgent` based on `AGENT_BACKEND` setting:

```python
def create_agent(role: str, cost_tracker=None, **kwargs):
    backend = get_settings().agent_backend
    if backend == "sdk" or role not in _LEGACY_CLASSES:
        return SdkAgent(role=role, cost_tracker=cost_tracker)
    return _LEGACY_CLASSES[role](cost_tracker=cost_tracker, **kwargs)
```

### Orchestration -- Agent-agnostic dicts
Protocols accept agents as `list[dict]` with `{"name": str, "system_prompt": str}`:

```python
class TRIZOrchestrator:
    def __init__(self, agents: list[dict], ...):
        if not agents:
            raise ValueError("At least one agent is required")
```

---

## 14. Tool Use Pattern

Tool schemas use Anthropic's `input_schema` format in `tools/schemas.py`. The registry (`tools/registry.py`) maps agent roles to allowed tools and dispatches calls. All tool handlers:
- Are async functions
- Return JSON strings
- Return `{"error": "..."}` on failure (never raise)
- Accept `_agent_role` injected by the base agent

---

## 15. Cost Tracking

Per-query cost tracking is implemented via `CostTracker` with `UsageRecord` dataclass. Pricing is model-aware with support for:
- Cache token discounts (0.1x rate)
- Batch API discounts (0.5x rate)
- Configurable alert thresholds

Cost limits enforce tool loop termination:

```python
if iteration_cost >= self.settings.tool_cost_limit:
    logger.warning("Tool cost limit reached...")
    break
```
