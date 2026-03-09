# Testing Conventions

Purpose: Document the test framework, structure, markers, mocking patterns, coverage approach, and CI setup across the CE-AGENTS monorepo.

---

## 1. Test Framework

**pytest >= 8.0** is the test runner across all projects. Key dependencies:

| Package | Purpose |
|---------|---------|
| `pytest` | Test runner and assertion framework |
| `pytest-asyncio` | Async test support with `@pytest.mark.asyncio` |
| `unittest.mock` | Mocking (stdlib -- no third-party mock library) |

---

## 2. Test Structure

Tests live in `tests/` directories within each sub-project:

```
CE - Agent Builder/tests/
    conftest.py              # Shared fixtures (DuckDB, mock Anthropic client, mock settings)
    __init__.py
    test_base_agent.py       # Core agent logic (20+ tests, grouped in classes)
    test_cost_tracker.py     # Cost calculation and tracking
    test_session_models.py   # Session/message Pydantic models
    test_github_api.py       # Integration tests (real API calls)
    test_sec_edgar.py        # Integration tests
    test_census_api.py       # Integration tests
    test_bls_api.py          # Integration tests
    test_web_search.py       # Integration tests
    test_notion_api.py       # Integration tests
    test_pinecone_kb.py      # Integration tests
    test_image_gen.py        # Integration tests
    test_duckdb_store.py     # Storage layer tests
    test_memory_store.py     # Pinecone memory tests
    test_memory_extractor.py # Memory extraction logic
    test_experience_log.py   # Learning subsystem
    test_feedback_loop.py    # Self-evaluation loop
    test_preferences.py      # User preference tracking
    test_file_export.py      # Report generation
    test_qa_tool.py          # QA protocol tooling

CE - Multi-Agent Orchestration/tests/
    __init__.py
    test_orchestrator_smoke.py   # Parametric smoke tests for ALL protocols
    test_output_correctness.py   # Content-level correctness assertions
    test_runs_api.py             # FastAPI route tests
    test_protocols_api.py        # Protocol listing API
    test_manifest.py             # Protocol manifest validation
    test_llm_no_tools.py         # LLM dispatch without tools
    test_blackboard_smoke.py     # Blackboard pattern tests
    test_run_envelope.py         # Run envelope structure
    test_walk_*.py               # Walk protocol family tests (5 files)
    test_integration_live.py     # Live integration tests

CE - Evals/tests/
    __init__.py
    test_rubric.py           # Rubric loading and prompt building
    test_models.py           # Pydantic model validation
    test_cost.py             # Cost calculation
    test_blind.py            # Blind evaluation protocol
    test_judge_pipeline.py   # Judge-parse-aggregate pipeline
    test_report.py           # Report generation
```

---

## 3. Test Organization Patterns

### Class-based grouping
Related tests are grouped into classes (no `setUp`/`tearDown` -- pytest fixtures instead):

```python
class TestEstimateResponseCost:
    def test_opus_pricing(self):
        ...

    def test_haiku_pricing(self):
        ...

    def test_cached_tokens_discounted(self):
        ...
```

### Function-level tests
Simpler test files use standalone functions:

```python
def test_from_yaml_loads_dimensions():
    rubric = Rubric.from_yaml(f.name)
    assert rubric.name == "Test Rubric"
```

### Naming convention
Test names follow `test_{what_is_tested}` or `test_{behavior_under_test}`:

```python
def test_valid_org_returns_info(self, client): ...
def test_invalid_org_returns_none(self, client): ...
def test_rate_limit_status(self, client): ...
def test_high_cost_query_alert(self, temp_tracker): ...
```

---

## 4. Markers

### `integration` marker
Tests that hit real external APIs are marked with `@pytest.mark.integration` to exclude them from CI unit test runs.

Registered in `CE - Agent Builder/pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = ["integration: real API calls"]
```

Usage -- module-level marker for entire test files:

```python
# test_github_api.py
pytestmark = pytest.mark.integration
```

Or per-test:

```python
@pytest.mark.integration
async def test_live_api_call():
    ...
```

### `asyncio` marker
Used for async test functions:

```python
@pytest.mark.asyncio
async def test_happy_path(self):
    result = await agent.chat("What is the strategy?")
    assert result == "Mock response"
```

The `asyncio_mode = "auto"` setting in `pyproject.toml` makes this automatic for the Agent Builder project.

---

## 5. Pytest Configuration

### Agent Builder (`CE - Agent Builder/pyproject.toml`)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --tb=short --strict-markers"
markers = ["integration: real API calls"]
```

- `asyncio_mode = "auto"`: All async tests run without needing explicit `@pytest.mark.asyncio` in most cases.
- `--tb=short`: Abbreviated tracebacks for cleaner output.
- `--strict-markers`: Fail on unknown markers (prevents typos).

### Other projects
CE - Evals and CE - Multi-Agent Orchestration rely on default pytest settings with no `pyproject.toml` pytest config.

---

## 6. Fixtures

### Shared fixtures (`CE - Agent Builder/tests/conftest.py`)

**DuckDB test isolation:**

```python
@pytest.fixture
def temp_duckdb_path(tmp_path: Path) -> Path:
    return tmp_path / "test.duckdb"

@pytest.fixture
def duckdb_store(temp_duckdb_path: Path) -> DuckDBStore:
    store = DuckDBStore(db_path=temp_duckdb_path)
    import csuite.storage.provider as _provider_mod
    old_store = _provider_mod._store
    _provider_mod._store = store
    yield store
    _provider_mod._store = old_store
    store.close()
```

Key pattern: Patches the module-level singleton so all code under test uses the temp store.

**Mock API response factory:**

```python
def make_api_response(
    text: str = "Mock response",
    stop_reason: str = "end_turn",
    model: str = "claude-opus-4-6",
    input_tokens: int = 100,
    output_tokens: int = 50,
    content: list | None = None,
) -> MagicMock:
    resp = MagicMock()
    resp.model = model
    resp.stop_reason = stop_reason
    resp.usage = _make_usage(input_tokens, output_tokens)
    resp.content = content or [make_text_block(text)]
    return resp
```

**Mock tool-use blocks:**

```python
def make_tool_use_block(
    tool_name: str = "test_tool",
    tool_input: dict | None = None,
    tool_id: str = "tu_123",
) -> MagicMock:
    block = MagicMock(spec=[])  # spec=[] prevents auto-creating attributes
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input or {}
    block.id = tool_id
    return block
```

Note: `spec=[]` is used to prevent `MagicMock` from auto-creating a `.text` attribute, since `hasattr(block, "text")` must return `False` for tool-use blocks.

**Mock settings:**

```python
@pytest.fixture
def mock_settings(tmp_path: Path):
    settings = MagicMock()
    settings.anthropic_api_key = "test-key-123"
    settings.default_model = "claude-opus-4-6"
    settings.memory_enabled = True
    settings.tools_enabled = True
    # ...
    return settings
```

---

## 7. Mocking Patterns

### Multi-patch context manager
`test_base_agent.py` defines a custom `_AgentPatchContext` that bundles all patches needed to construct a `BaseAgent` without any real dependencies:

```python
class _AgentPatchContext:
    def __enter__(self):
        pairs = [
            ("csuite.agents.base.get_settings", "settings"),
            ("csuite.agents.base.get_agent_config", "agent_config"),
            ("csuite.agents.base.anthropic.Anthropic", "anthropic"),
            ("csuite.agents.base.SessionManager", "session_mgr"),
            ("csuite.agents.base.MemoryStore", "memory_store"),
            ("csuite.agents.base.ExperienceLog", "experience_log"),
            ("csuite.agents.base.PreferenceTracker", "pref_tracker"),
            ("csuite.agents.base.CostTracker", "cost_tracker"),
        ]
        # ... start all patches, configure return values

    def __exit__(self, *args):
        for p in self.patches:
            p.stop()
```

Usage:

```python
def test_reads_claude_md(self, tmp_path):
    with _agent_patches() as ctx:
        ctx.mocks["settings"].return_value.project_root = tmp_path
        agent = _TestAgent()
        assert "Business Context" in agent.business_context
```

### AsyncMock for async methods
Async tool execution and API calls use `unittest.mock.AsyncMock`:

```python
with patch("csuite.agents.base.execute_tool",
           new_callable=AsyncMock, return_value='{"result": "ok"}'):
    result = await agent.chat("Use a tool")
```

### Mock sequencing via `side_effect`
For multi-step LLM interactions (tool loops, multi-phase protocols):

```python
ctx.mock_client.messages.create.side_effect = [tool_resp, final_resp]
```

### Orchestration smoke test mocking
Protocol tests mock at two levels:
1. `protocols.llm.agent_complete` -- returns canned JSON string
2. `anthropic.AsyncAnthropic` -- returns `MockMessage` objects with `.content[0].text`

```python
with (
    patch("protocols.llm.agent_complete", new=AsyncMock(return_value=CANNED_JSON_OBJECT)),
    patch("anthropic.AsyncAnthropic", return_value=mock_client),
    patch("protocols.tracing.make_client", return_value=mock_client),
):
    result = asyncio.run(_run())
```

### Evals test mocking
Judge pipeline tests mock the backend and settings:

```python
@patch("ce_evals.core.judge.get_backend")
@patch("ce_evals.core.judge.get_settings")
def test_full_pipeline(self, mock_settings, mock_get_backend):
    mock_backend = MagicMock()
    mock_backend.call.return_value = (json_string, 100, 200)
    mock_get_backend.return_value = mock_backend
```

---

## 8. Parametric Testing

### Protocol smoke tests
The orchestration project uses `@pytest.mark.parametrize` to auto-discover and test every protocol:

```python
_PROTOCOL_DIRS = _discover_protocol_dirs()
_PROTOCOL_IDS = [d.name for d in _PROTOCOL_DIRS]

@pytest.mark.parametrize("protocol_dir_name", _PROTOCOL_IDS)
def test_orchestrator_smoke(protocol_dir_name: str) -> None:
    """Smoke-test each protocol orchestrator with fully mocked LLM calls."""
    ...
```

This generates one test per protocol in CI output. Protocols that fail are marked `xfail` rather than failing the suite:

```python
pytest.xfail(f"{protocol_dir_name} raised {type(exc).__name__}: {exc}")
```

### Override tables for non-standard protocols
Protocols with non-standard `run()` signatures are handled via lookup dicts:

```python
_PROTOCOL_RUN_KWARGS = {
    "p07_wicked_questions": {"topic": _TEST_QUESTION},
    "p13_ecocycle_planning": {"question": ..., "initiatives": [...]},
    "p17_red_blue_white": {"question": ..., "plan": ...},
    ...
}
```

---

## 9. Test Categories

### Unit tests (CI default)
- No external dependencies (API calls, databases)
- Use mocks for all I/O
- Run with: `pytest tests/ -m "not integration"`

### Integration tests
- Hit real APIs (GitHub, SEC EDGAR, Census, BLS, Pinecone)
- Marked with `pytestmark = pytest.mark.integration` or per-test `@pytest.mark.integration`
- Excluded from CI unit test job
- Designed for low API consumption (conservative limits, small orgs)

### Correctness tests
- Go beyond smoke tests to assert on output content
- Verify field presence, agent perspective propagation, winner selection logic
- `CE - Multi-Agent Orchestration/tests/test_output_correctness.py`

### Smoke tests
- Verify each protocol can be imported, instantiated, and `run()` completes
- Do not assert on output quality -- only that result is not `None`
- `CE - Multi-Agent Orchestration/tests/test_orchestrator_smoke.py`

---

## 10. Concrete Test Agent Pattern

Tests that need a `BaseAgent` instance create a minimal concrete subclass:

```python
class _TestAgent(BaseAgent):
    ROLE = "ceo"

    def get_system_prompt(self) -> str:
        return "You are a test CEO agent."
```

This avoids coupling tests to any specific agent implementation.

---

## 11. CI Pipeline

Defined in `.github/workflows/ci.yml`. Triggers on push to `main` and PRs targeting `main`.

### Jobs

| Job | Project | What it does |
|-----|---------|--------------|
| `agent-builder-lint` | CE - Agent Builder | `ruff check src/csuite` + `mypy src/csuite --ignore-missing-imports` |
| `agent-builder-test` | CE - Agent Builder | `pytest tests/ -v --tb=short -m "not integration"` |
| `orchestration-lint` | CE - Multi-Agent Orchestration | `ruff check protocols/ api/ --ignore E402` |
| `orchestration-test` | CE - Multi-Agent Orchestration | `pytest tests/ -v --tb=short` |
| `orchestration-ui` | CE - Multi-Agent Orchestration/ui | `npm ci` + `npx vite build` |
| `evals-test` | CE - Evals | `pytest tests/ -v` |

### Environment
- **Python 3.13** (all Python jobs)
- **Node 20** (UI build job)
- `ANTHROPIC_API_KEY: sk-test-placeholder` for tests that import settings but don't make real calls

### Key CI patterns:
- Integration tests are **excluded** from CI via `-m "not integration"` (Agent Builder only)
- Orchestration tests install additional packages inline: `pip install pytest fastapi httpx sqlmodel sse-starlette litellm`
- No test coverage tool is configured (no `--cov` flags, no coverage reports)
- Jobs run independently (no `needs:` dependencies between them)

---

## 12. Assertions

### Standard pytest assertions
The codebase uses plain `assert` statements (no `self.assert*` methods):

```python
assert result == "Mock response"
assert "Business Context" in agent.business_context
assert agent._should_use_tools() is False
```

### pytest.approx for floating point
Cost calculations use `pytest.approx` with relative tolerance:

```python
assert record.total_cost == pytest.approx(0.15, rel=0.01)
```

### pytest.raises for exceptions
```python
with pytest.raises(ValueError, match="must define ROLE"):
    _NoRole()
```

### pytest.xfail for known-fragile tests
Orchestration smoke tests use `pytest.xfail` rather than hard failures:

```python
pytest.xfail(f"{protocol_dir_name} raised {type(exc).__name__}: {exc}")
```

---

## 13. Test Data

### Canned JSON objects
Orchestration tests define rich JSON objects that satisfy every protocol's `parse_json_object` calls:

```python
_RICH_OBJECT = {
    "hypotheses": [{"label": "Mock hypothesis", ...}],
    "evidence": [...],
    "scores": [...],
    "synthesis": "mock synthesis",
    # ... extensive field coverage for all 50 protocols
}
```

### Temporary directories
Tests use pytest's built-in `tmp_path` fixture for file-based storage:

```python
def test_log_usage(self, temp_tracker):
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = CostTracker(data_dir=Path(tmpdir))
        ...
```

### Placeholder API keys
CI uses `sk-test-placeholder` to satisfy settings validation without making real API calls.

---

## 14. What Is NOT Tested

- No test coverage measurement (no `pytest-cov` configured)
- No mutation testing
- No snapshot/golden-file testing
- No load/performance tests
- No end-to-end tests that run real LLM calls in CI
- `ce-db` project has no tests in the repo (only `dev = ["pytest>=8.0", "pytest-asyncio"]` declared)
- No UI component tests (React/Vite app only has a build check)
