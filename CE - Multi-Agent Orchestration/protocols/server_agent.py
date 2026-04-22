"""ServerAgent — production agent for server/Docker deployment.

Uses direct Anthropic API calls with native tool-use instead of spawning
Claude Code subprocesses (which fail as root in Docker). Drop-in replacement
for the old AgentBridge(SdkAgent(...)) path.

Reuses:
- System prompts from CE Agent Builder's _ROLE_PROMPTS (70+ roles)
- Tool schemas from CE Agent Builder's ALL_TOOL_SCHEMAS
- Tool execution from api/tool_executor.py
- Memory/learning from CE Agent Builder (graceful degradation if unavailable)
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

# Ensure CE Agent Builder is importable
_AGENT_BUILDER_SRC = Path(__file__).resolve().parents[1] / "CE - Agent Builder" / "src"
_env_path = os.environ.get("CE_AGENT_BUILDER_PATH")
if _env_path:
    _AGENT_BUILDER_SRC = Path(_env_path).resolve()
if str(_AGENT_BUILDER_SRC) not in sys.path:
    sys.path.insert(0, str(_AGENT_BUILDER_SRC))

# ── Lazy imports from Agent Builder (may not be installed) ───────────────────

_role_prompts: dict[str, str] | None = None
_role_tool_map: dict[str, list[str]] | None = None
_all_tool_schemas: dict[str, dict] | None = None


def _get_role_prompts() -> dict[str, str]:
    global _role_prompts
    if _role_prompts is None:
        try:
            from csuite.agents.sdk_agent import _ROLE_PROMPTS
            _role_prompts = _ROLE_PROMPTS
        except ImportError:
            logger.warning("Cannot import _ROLE_PROMPTS from Agent Builder")
            _role_prompts = {}
    return _role_prompts


def _get_role_tool_map() -> dict[str, list[str]]:
    global _role_tool_map
    if _role_tool_map is None:
        try:
            from csuite.tools.registry import ROLE_TOOL_MAP
            _role_tool_map = ROLE_TOOL_MAP
        except ImportError:
            logger.warning("Cannot import ROLE_TOOL_MAP from Agent Builder")
            _role_tool_map = {}
    return _role_tool_map


def _get_all_tool_schemas() -> dict[str, dict]:
    global _all_tool_schemas
    if _all_tool_schemas is None:
        try:
            from csuite.tools.schemas import ALL_TOOL_SCHEMAS
            _all_tool_schemas = ALL_TOOL_SCHEMAS
        except ImportError:
            logger.warning("Cannot import ALL_TOOL_SCHEMAS from Agent Builder")
            _all_tool_schemas = {}
    return _all_tool_schemas


# ── Agent name mapping (from protocols/agents.py BUILTIN_AGENTS) ─────────────

def _get_agent_name(role: str) -> str:
    """Get human-readable agent name for a role key."""
    try:
        from protocols.agents import BUILTIN_AGENTS
        agent = BUILTIN_AGENTS.get(role, {})
        return agent.get("name", role.replace("-", " ").title())
    except ImportError:
        return role.replace("-", " ").title()


# ── Business context loader ──────────────────────────────────────────────────

def _load_business_context() -> str:
    """Load business context from Agent Builder's CLAUDE.md."""
    candidates = [
        _AGENT_BUILDER_SRC.parent / ".claude" / "CLAUDE.md",
        Path(__file__).resolve().parents[1] / ".claude" / "CLAUDE.md",
    ]
    for path in candidates:
        if path.exists():
            try:
                return path.read_text()
            except Exception:
                pass
    return ""


# ── Memory/learning helpers (graceful degradation) ───────────────────────────

def _get_memory_context(role: str, query: str) -> str:
    """Retrieve semantic memories from Pinecone. Returns empty string on failure."""
    try:
        from csuite.memory.store import MemoryStore
        store = MemoryStore()
        if not store.enabled:
            return ""
        memories = store.retrieve(role, query, top_k=5)
        if memories:
            lines = [f"- [{m['memory_type']}] {m['summary']}" for m in memories]
            return "## Institutional Memory\n\nRelevant past analyses and decisions:\n\n" + "\n".join(lines)
    except Exception:
        logger.debug("Memory retrieval failed for %s", role, exc_info=True)
    return ""


def _get_lessons(role: str) -> str:
    """Retrieve experience log lessons from DuckDB. Returns empty string on failure."""
    try:
        from csuite.learning.experience_log import ExperienceLog
        log = ExperienceLog()
        lessons = log.get_lessons(role, limit=20)
        if lessons:
            return f"## Lessons Learned\n\n{lessons}"
    except Exception:
        logger.debug("Lesson retrieval failed for %s", role, exc_info=True)
    return ""


def _get_preferences(role: str) -> str:
    """Retrieve user preferences. Returns empty string on failure."""
    try:
        from csuite.learning.preferences import PreferenceTracker
        tracker = PreferenceTracker()
        ctx = tracker.get_preference_context(role)
        if ctx:
            return f"## User Preferences\n\n{ctx}"
    except Exception:
        logger.debug("Preference retrieval failed for %s", role, exc_info=True)
    return ""


# ── Tool executor ────────────────────────────────────────────────────────────

async def _execute_tool(tool_name: str, tool_input: dict) -> tuple[str, float]:
    """Execute a tool call. Delegates to api/tool_executor.py."""
    try:
        from api.tool_executor import execute_tool
        return await execute_tool(tool_name, tool_input)
    except ImportError:
        import json
        import time
        return json.dumps({"error": f"Tool executor unavailable for '{tool_name}'"}), 0.0


# ── ServerAgent ──────────────────────────────────────────────────────────────

MAX_TOOL_ITERATIONS = 15


class ServerAgent:
    """Production agent for server deployment — direct Anthropic API with tools.

    Replaces SdkAgent (which spawns Claude Code subprocesses) with pure
    API calls using anthropic.AsyncAnthropic().messages.create().

    Supports:
    - 70+ role-specific system prompts from Agent Builder
    - Per-role tool schemas (40+ roles) with full agentic tool loop
    - Pinecone memory, DuckDB experience logs, user preferences (graceful degradation)
    - Real token-level cost tracking from API responses
    - Dict-style access for protocol compatibility
    """

    def __init__(self, role: str, model: str = "claude-opus-4-7"):
        self.role = role
        self.model = model
        self.name = _get_agent_name(role)
        self.cost = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_tokens = 0
        self.tool_calls: list[dict] = []
        self._client: anthropic.AsyncAnthropic | None = None
        self.institutional_memory: str | None = None

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic()
        return self._client

    def _build_system_prompt(self, query: str = "") -> str:
        """Assemble full system prompt: role prompt + business context + memory + lessons."""
        role_prompts = _get_role_prompts()
        base = role_prompts.get(self.role, "")

        # Fall back to BUILTIN_AGENTS system prompt if no rich prompt
        if not base:
            try:
                from protocols.agents import BUILTIN_AGENTS
                agent = BUILTIN_AGENTS.get(self.role, {})
                base = agent.get("system_prompt", f"You are {self.role}.")
            except ImportError:
                base = f"You are {self.role}."

        sections = [base]

        ctx = _load_business_context()
        if ctx:
            sections.append(
                "## Business Context\n\n"
                "The following is specific context about the business "
                "you are advising:\n\n" + ctx
            )

        if query:
            mem = _get_memory_context(self.role, query)
            if mem:
                sections.append(mem)

        lessons = _get_lessons(self.role)
        if lessons:
            sections.append(lessons)

        prefs = _get_preferences(self.role)
        if prefs:
            sections.append(prefs)

        if self.institutional_memory:
            sections.append(
                "## Institutional Memory -- Past Protocol Insights\n\n"
                "The following is a high-quality synthesis from a previous run "
                "on a similar question. Use it as context, not as a template. "
                "Build on its strengths and address its gaps.\n\n"
                f"{self.institutional_memory}"
            )

        return "\n\n".join(sections)

    def _resolve_tools(self) -> list[dict]:
        """Get Anthropic-format tool schemas for this agent's role."""
        tool_map = _get_role_tool_map()
        schemas = _get_all_tool_schemas()
        tool_names = tool_map.get(self.role, [])
        return [schemas[name] for name in tool_names if name in schemas]

    async def chat(self, message: str) -> str:
        """Send a message and get a response via direct Anthropic API.

        Implements full agentic tool-use loop: if Claude returns tool_use
        blocks, execute them and feed results back until Claude produces
        a final text response or MAX_TOOL_ITERATIONS is reached.
        """
        system_prompt = self._build_system_prompt(query=message)
        tools = self._resolve_tools()
        self.tool_calls = []

        messages: list[dict[str, Any]] = [{"role": "user", "content": message}]

        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 16_384,
            "system": system_prompt,
            "messages": messages,
            "thinking": {"type": "adaptive", "budget_tokens": 10_000},
        }
        if tools:
            create_kwargs["tools"] = tools

        # Reset cost accumulators
        self.cost = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_tokens = 0

        response = await self.client.messages.create(**create_kwargs)
        self._accumulate_usage(response)

        # If no tools or no tool_use, return text directly
        if not tools or response.stop_reason != "tool_use":
            return self._extract_text(response)

        # Agentic tool loop
        for iteration in range(MAX_TOOL_ITERATIONS):
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    self.tool_calls.append({
                        "tool": block.name,
                        "input_summary": str(block.input)[:300],
                        "id": block.id,
                    })
                    logger.info(
                        "[%s] tool_call #%d: %s",
                        self.role, iteration, block.name,
                    )

                    result, elapsed_ms = await _execute_tool(block.name, block.input)

                    logger.info(
                        "[%s] tool_result: %s (%.0fms)",
                        self.role, block.name, elapsed_ms,
                    )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            if not tool_results:
                break

            messages.append({"role": "user", "content": tool_results})

            response = await self.client.messages.create(
                **{**create_kwargs, "messages": messages}
            )
            self._accumulate_usage(response)

            if response.stop_reason != "tool_use":
                break

        return self._extract_text(response)

    def _accumulate_usage(self, response: Any) -> None:
        """Accumulate token usage and cost from an API response."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        inp = getattr(usage, "input_tokens", 0) or 0
        out = getattr(usage, "output_tokens", 0) or 0
        cached = getattr(usage, "cache_read_input_tokens", 0) or 0
        self.input_tokens += inp
        self.output_tokens += out
        self.cached_tokens += cached
        from ce_shared.pricing import cost_for_model
        self.cost += cost_for_model(self.model, input_tokens=inp, output_tokens=out, cache_read_tokens=cached)

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Extract text content from an Anthropic API response."""
        parts = []
        for block in response.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n\n".join(parts) if parts else ""

    # ── Dict-style access for protocol compatibility ─────────────────────────

    def __getitem__(self, key: str) -> Any:
        if key == "name":
            return self.name
        if key == "system_prompt":
            return self._build_system_prompt()
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default
