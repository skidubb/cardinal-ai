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

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

# Ensure CE Agent Builder is importable
# parents[2] = the monorepo root ("CE - AGENTS"); Agent Builder is a sibling of this project
_AGENT_BUILDER_SRC = Path(__file__).resolve().parents[2] / "CE - Agent Builder" / "src"
_env_path = os.environ.get("CE_AGENT_BUILDER_PATH")
if _env_path:
    _AGENT_BUILDER_SRC = Path(_env_path).resolve()
if str(_AGENT_BUILDER_SRC) not in sys.path:
    sys.path.insert(0, str(_AGENT_BUILDER_SRC))

# ── Lazy imports from Agent Builder (may not be installed) ───────────────────

# A failed import means agents run WITHOUT tools/prompts — never degrade silently.
# Failures are recorded here and surfaced via /api/health (agent_builder_status()).
AGENT_BUILDER_IMPORT_ERRORS: dict[str, str] = {}

_role_prompts: dict[str, str] | None = None
_role_tool_map: dict[str, list[str]] | None = None
_all_tool_schemas: dict[str, dict] | None = None


def agent_builder_status() -> dict:
    """Report whether Agent Builder imports work. Attempts all three imports."""
    _get_role_prompts()
    _get_role_tool_map()
    _get_all_tool_schemas()
    return {
        "ok": not AGENT_BUILDER_IMPORT_ERRORS,
        "path": str(_AGENT_BUILDER_SRC),
        "errors": dict(AGENT_BUILDER_IMPORT_ERRORS),
    }


def _get_role_prompts() -> dict[str, str]:
    global _role_prompts
    if _role_prompts is None:
        try:
            from csuite.agents.sdk_agent import _ROLE_PROMPTS

            _role_prompts = _ROLE_PROMPTS
        except ImportError as exc:
            logger.error(
                "DEGRADED: cannot import _ROLE_PROMPTS from Agent Builder at %s — "
                "agents will run with generic prompts: %s",
                _AGENT_BUILDER_SRC,
                exc,
            )
            AGENT_BUILDER_IMPORT_ERRORS["_ROLE_PROMPTS"] = str(exc)
            _role_prompts = {}
    return _role_prompts


def _get_role_tool_map() -> dict[str, list[str]]:
    global _role_tool_map
    if _role_tool_map is None:
        try:
            from csuite.tools.registry import ROLE_TOOL_MAP

            _role_tool_map = ROLE_TOOL_MAP
        except ImportError as exc:
            logger.error(
                "DEGRADED: cannot import ROLE_TOOL_MAP from Agent Builder at %s — "
                "agents will run with NO tools: %s",
                _AGENT_BUILDER_SRC,
                exc,
            )
            AGENT_BUILDER_IMPORT_ERRORS["ROLE_TOOL_MAP"] = str(exc)
            _role_tool_map = {}
    return _role_tool_map


def _get_all_tool_schemas() -> dict[str, dict]:
    global _all_tool_schemas
    if _all_tool_schemas is None:
        try:
            from csuite.tools.schemas import ALL_TOOL_SCHEMAS

            _all_tool_schemas = ALL_TOOL_SCHEMAS
        except ImportError as exc:
            logger.error(
                "DEGRADED: cannot import ALL_TOOL_SCHEMAS from Agent Builder at %s — "
                "agents will run with NO tools: %s",
                _AGENT_BUILDER_SRC,
                exc,
            )
            AGENT_BUILDER_IMPORT_ERRORS["ALL_TOOL_SCHEMAS"] = str(exc)
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
            return (
                "## Institutional Memory\n\nRelevant past analyses and decisions:\n\n"
                + "\n".join(lines)
            )
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

        return json.dumps(
            {"error": f"Tool executor unavailable for '{tool_name}'"}
        ), 0.0


# ── ServerAgent ──────────────────────────────────────────────────────────────

MAX_TOOL_ITERATIONS = 15


def _model_accepts_temperature(model: str) -> bool:
    """Claude 4.x deprecated the temperature parameter (API returns 400).

    Other Anthropic models and non-Anthropic models via LiteLLM still accept it.
    """
    if not model:
        return True
    low = model.lower()
    return not (
        "claude-opus-4" in low or "claude-sonnet-4" in low or "claude-haiku-4" in low
    )


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

    def __init__(
        self,
        role: str,
        model: str = "claude-opus-4-7",
        temperature: float | None = None,
        *,
        system_prompt: str | None = None,
        tool_names: list[str] | None = None,
        kb_namespaces: list[str] | None = None,
        max_tokens: int | None = None,
        display_name: str | None = None,
    ):
        self.role = role
        self.model = model
        self.temperature = temperature
        self.name = display_name if display_name else _get_agent_name(role)
        self.cost = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_tokens = 0
        self.tool_calls: list[dict] = []
        self._client: anthropic.AsyncAnthropic | None = None
        self.institutional_memory: str | None = None
        self._system_prompt_override = system_prompt
        self._tool_names_override = tool_names
        self.kb_namespaces = kb_namespaces
        self._max_tokens_override = max_tokens

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic()
        return self._client

    @property
    def tools_available(self) -> bool:
        """Whether this agent's model supports the native Anthropic tool loop."""
        from protocols.model_catalog import supports_tools

        return supports_tools(self.model)

    def _build_system_prompt(self, query: str = "") -> str:
        """Assemble full system prompt: role prompt + business context + memory + lessons."""
        if self._system_prompt_override is not None:
            base = self._system_prompt_override
        else:
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
        if not self.tools_available:
            return []

        schemas = _get_all_tool_schemas()

        if self._tool_names_override is not None:
            resolved = [
                schemas[name] for name in self._tool_names_override if name in schemas
            ]
            dropped = [
                name for name in self._tool_names_override if name not in schemas
            ]
            if dropped:
                logger.warning(
                    "[%s] dropped unknown tool override(s): %s", self.role, dropped
                )
            return resolved

        tool_map = _get_role_tool_map()
        tool_names = tool_map.get(self.role, [])
        return [schemas[name] for name in tool_names if name in schemas]

    async def chat(self, message: str) -> str:
        """Send a message and get a response.

        Anthropic-catalog models use the direct API with the native
        agentic tool-use loop (below). Gateway models (routed through
        LiteLLM/Vercel AI Gateway) don't support that tool loop, so they're
        dispatched to ``_litellm_chat`` instead.

        Implements full agentic tool-use loop: if Claude returns tool_use
        blocks, execute them and feed results back until Claude produces
        a final text response or MAX_TOOL_ITERATIONS is reached.
        """
        from protocols.model_catalog import ModelRoute, resolve_route

        if resolve_route(self.model) == ModelRoute.GATEWAY:
            return await self._litellm_chat(message)

        system_prompt = self._build_system_prompt(query=message)
        tools = self._resolve_tools()
        self.tool_calls = []

        messages: list[dict[str, Any]] = [{"role": "user", "content": message}]

        # Convert system prompt to list-of-blocks with cache_control on the last
        # block. This enables Anthropic prompt caching: the tools + system prefix
        # is cached for 5 min and charged at 0.1× on re-use (writes cost 1.25×).
        # The tool loop re-sends create_kwargs on every iteration, so the cache
        # pays off from the second tool iteration onward and across protocol stages
        # that call the same agent within the 5-min TTL.
        system_blocks: list[dict] = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self._max_tokens_override or 16_384,
            "system": system_blocks,
            "messages": messages,
        }
        # Claude 4.x deprecated the temperature parameter entirely and rejects
        # it with HTTP 400. Extended thinking also requires temperature=1.0 on
        # models that still accept it. Apply a custom temperature only on
        # models that support it AND disable thinking in that branch.
        custom_temp = (
            self.temperature is not None
            and float(self.temperature) != 1.0
            and _model_accepts_temperature(self.model)
        )
        if custom_temp:
            create_kwargs["thinking"] = {"type": "disabled"}
            create_kwargs["temperature"] = float(self.temperature)
        else:
            create_kwargs["thinking"] = {"type": "adaptive"}
            if self.temperature is not None and float(self.temperature) != 1.0:
                logger.warning(
                    "temperature=%s ignored: model %s does not accept temperature",
                    self.temperature,
                    self.model,
                )
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
        from protocols.llm import get_event_queue

        eq = get_event_queue()

        for iteration in range(MAX_TOOL_ITERATIONS):
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        input_summary = (
                            json.dumps(block.input)[:500] if block.input else "{}"
                        )
                    except (TypeError, ValueError):
                        input_summary = str(block.input)[:500]

                    logger.info(
                        "[%s] tool_call #%d: %s",
                        self.role,
                        iteration,
                        block.name,
                    )

                    if eq is not None:
                        await eq.put(
                            {
                                "event": "tool_call",
                                "agent_name": self.name,
                                "tool_name": block.name,
                                "tool_input": input_summary,
                                "iteration": iteration,
                            }
                        )

                    result, elapsed_ms = await _execute_tool(block.name, block.input)

                    logger.info(
                        "[%s] tool_result: %s (%.0fms)",
                        self.role,
                        block.name,
                        elapsed_ms,
                    )

                    result_text = str(result)
                    self.tool_calls.append(
                        {
                            "tool": block.name,
                            "input_summary": input_summary,
                            "result_summary": result_text[:1000],
                            "elapsed_ms": round(elapsed_ms, 1),
                            "iteration": iteration,
                            "id": block.id,
                        }
                    )

                    if eq is not None:
                        await eq.put(
                            {
                                "event": "tool_result",
                                "agent_name": self.name,
                                "tool_name": block.name,
                                "tool_result_summary": result_text[:500],
                                "elapsed_ms": round(elapsed_ms, 1),
                                "iteration": iteration,
                            }
                        )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

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

    async def _litellm_chat(self, message: str) -> str:
        """Send a message via LiteLLM (Vercel AI Gateway) for non-Anthropic models.

        No tool loop — gateway models in the catalog are marked
        ``supports_anthropic_tool_loop=False``, so this is a plain single-turn
        completion. System prompt is a plain string (no cache_control blocks;
        prompt caching is an Anthropic-specific feature).
        """
        import litellm

        from protocols.llm import _retry_api_call
        from protocols.model_catalog import litellm_id_for

        system_prompt = self._build_system_prompt(query=message)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ]

        create_kwargs: dict[str, Any] = {
            "model": litellm_id_for(self.model),
            "messages": messages,
            "max_tokens": self._max_tokens_override or 16_384,
        }
        if self.temperature is not None and float(self.temperature) != 1.0:
            create_kwargs["temperature"] = float(self.temperature)

        self.cost = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_tokens = 0
        self.tool_calls = []

        response = await _retry_api_call(litellm.acompletion, **create_kwargs)
        self._accumulate_litellm_usage(response)

        return response.choices[0].message.content or ""

    def _accumulate_litellm_usage(self, response: Any) -> None:
        """Accumulate token usage and cost from a LiteLLM (OpenAI-shape) response."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        inp = getattr(usage, "prompt_tokens", 0) or 0
        out = getattr(usage, "completion_tokens", 0) or 0
        self.input_tokens += inp
        self.output_tokens += out
        from ce_shared.pricing import cost_for_model

        self.cost += cost_for_model(self.model, input_tokens=inp, output_tokens=out)

    def _accumulate_usage(self, response: Any) -> None:
        """Accumulate token usage and cost from an API response.

        Reads both ``cache_read_input_tokens`` (0.1× cost) and
        ``cache_creation_input_tokens`` (1.25× cost) from the usage object so
        that prompt-cache economics are accurately reflected.
        """
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        inp = getattr(usage, "input_tokens", 0) or 0
        out = getattr(usage, "output_tokens", 0) or 0
        cached = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.input_tokens += inp
        self.output_tokens += out
        self.cached_tokens += cached
        from ce_shared.pricing import cost_for_model

        self.cost += cost_for_model(
            self.model,
            input_tokens=inp,
            output_tokens=out,
            cache_read_tokens=cached,
            cache_write_tokens=cache_write,
        )

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
