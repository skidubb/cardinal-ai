"""
Base agent class for C-Suite agents.

Provides shared functionality for all agents including:
- Conversation management
- Session persistence
- System prompt handling
- Response streaming
- Cost tracking (Directive D10)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from csuite.config import AgentConfig, get_agent_config, get_settings
from csuite.learning.experience_log import ExperienceLog
from csuite.learning.preferences import PreferenceTracker
from csuite.memory.store import MemoryStore
from csuite.session import Session, SessionManager
from csuite.tools.cost_tracker import CostTracker, TaskType
from csuite.tools.registry import execute_tool, get_tools_for_role

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all C-Suite agents."""

    # Subclasses must define their role
    ROLE: str = ""

    # Default task type for cost tracking (subclasses can override)
    DEFAULT_TASK_TYPE: TaskType = TaskType.EXECUTIVE_SYNTHESIS

    def __init__(
        self,
        session: Session | None = None,
        config: AgentConfig | None = None,
        cost_tracker: CostTracker | None = None,
    ):
        """Initialize the agent.

        Args:
            session: Existing session to resume, or None for new session
            config: Agent configuration override
            cost_tracker: Cost tracker instance (shared across agents if provided)
        """
        if not self.ROLE:
            raise ValueError("Agent subclass must define ROLE")

        self.settings = get_settings()
        self.config = config or get_agent_config(self.ROLE)
        self.session_manager = SessionManager()
        self.console = Console()

        # Initialize cost tracker (Directive D10)
        self.cost_tracker = cost_tracker or CostTracker()

        # Initialize or resume session
        if session:
            self.session = session
        else:
            self.session = self.session_manager.create_session(self.ROLE)

        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

        # Load business context from CLAUDE.md if available
        self.business_context = self._load_business_context()

        # Memory + Learning subsystems (graceful no-op if disabled)
        self.memory_store = MemoryStore()
        self.experience_log = ExperienceLog()
        self.preference_tracker = PreferenceTracker()

    def _load_business_context(self) -> str:
        """Load business context from CLAUDE.md file."""
        claude_md_path = self.settings.project_root / ".claude" / "CLAUDE.md"
        if claude_md_path.exists():
            return claude_md_path.read_text()
        return ""

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent.

        Subclasses must implement this to provide their specialized prompt.
        """
        pass

    def _build_system_prompt(self, query: str = "") -> str:
        """Build the full system prompt including business context, memory, and learning."""
        base_prompt = self.get_system_prompt()

        sections = [base_prompt]

        if self.business_context:
            sections.append(
                f"## Business Context\n\n"
                f"The following is specific context about the business you are advising:\n\n"
                f"{self.business_context}"
            )

        # Retrieve relevant memories from DuckDB
        if query and self.memory_store.enabled:
            memories = self.memory_store.retrieve(self.ROLE, query, top_k=5)
            if memories:
                mem_lines = []
                for m in memories:
                    mem_lines.append(f"- [{m['memory_type']}] {m['summary']}")
                sections.append(
                    "## Institutional Memory\n\n"
                    "Relevant past analyses and decisions:\n\n"
                    + "\n".join(mem_lines)
                )

        # Experience log lessons
        lessons = self.experience_log.get_lessons(self.ROLE, limit=20)
        if lessons:
            sections.append(f"## Lessons Learned\n\n{lessons}")

        # User preferences
        pref_ctx = self.preference_tracker.get_preference_context(self.ROLE)
        if pref_ctx:
            sections.append(f"## User Preferences\n\n{pref_ctx}")

        return "\n\n".join(sections)

    def _get_messages(self) -> list[dict[str, str]]:
        """Get conversation history for API call."""
        return self.session.get_conversation_history()

    def _extract_cached_tokens(self, usage: Any) -> int:
        """Extract cached token count from API response usage.

        Args:
            usage: The usage object from Anthropic API response

        Returns:
            Number of tokens read from cache (0 if not available)
        """
        # Anthropic returns cache_read_input_tokens when prompt caching is used
        return getattr(usage, "cache_read_input_tokens", 0)

    def _log_usage(
        self,
        response: Any,
        task_type: TaskType | None = None,
        audit_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log API usage to cost tracker.

        Args:
            response: The Anthropic API response object
            task_type: Type of task (defaults to agent's DEFAULT_TASK_TYPE)
            audit_id: Optional audit/project identifier for cost attribution
            metadata: Additional metadata to attach to the record
        """
        self.cost_tracker.log_usage(
            agent=self.ROLE.upper(),
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cached_tokens=self._extract_cached_tokens(response.usage),
            task_type=task_type or self.DEFAULT_TASK_TYPE,
            session_id=self.session.id,
            audit_id=audit_id,
            metadata=metadata or {},
        )

    # Maximum tool-loop iterations to prevent runaway loops
    MAX_TOOL_ITERATIONS = 15

    def _should_use_tools(self) -> bool:
        """Check if tools should be enabled for this agent."""
        if not self.settings.tools_enabled:
            return False
        if not self.config.tools_enabled:
            return False
        # Check session cost limit
        summary = self.get_session_cost_summary()
        if summary["total_cost"] >= self.settings.session_cost_limit:
            logger.info(
                "Tools disabled for session %s: cost $%.4f >= limit $%.2f",
                self.session.id, summary["total_cost"], self.settings.session_cost_limit,
            )
            return False
        return True

    async def chat(
        self,
        user_message: str,
        task_type: TaskType | None = None,
        audit_id: str | None = None,
    ) -> str:
        """Send a message and get a response.

        Supports an agentic tool-use loop: if Claude returns tool_use blocks,
        the tools are executed and results fed back until Claude produces a
        final text response or the iteration cap is hit.

        Args:
            user_message: The user's message
            task_type: Optional task type for cost tracking (defaults to DEFAULT_TASK_TYPE)
            audit_id: Optional audit/project ID for cost attribution

        Returns:
            The assistant's response text
        """
        # Add user message to session
        self.session.add_message("user", user_message)

        # Build messages for API
        messages = self._get_messages()

        # Load tools if enabled
        tools = get_tools_for_role(self.ROLE) if self._should_use_tools() else []

        # Track cost across iterations for per-query cost ceiling
        iteration_cost = 0.0

        # Agentic loop — keeps calling until Claude stops using tools
        iteration = 0
        assistant_message = ""

        while iteration < self.MAX_TOOL_ITERATIONS:
            iteration += 1

            api_kwargs: dict[str, Any] = dict(
                model=self.config.model or self.settings.default_model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=self._build_system_prompt(query=user_message),
                messages=messages,
            )
            if tools:
                api_kwargs["tools"] = tools

            response = self.client.messages.create(**api_kwargs)

            # Log usage for this iteration
            self._log_usage(response, task_type=task_type, audit_id=audit_id)

            # Track iteration cost for per-query ceiling
            query_cost = self._estimate_response_cost(response)
            iteration_cost += query_cost

            if response.stop_reason == "tool_use":
                # Append assistant message (with tool_use blocks) to messages
                messages.append({"role": "assistant", "content": response.content})

                # Execute each tool call, build tool_result blocks
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        block.input["_agent_role"] = self.ROLE
                        result = await execute_tool(
                            block.name, block.input, self.settings,
                            cost_tracker=self.cost_tracker,
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                messages.append({"role": "user", "content": tool_results})  # type: ignore[dict-item]

                # Check per-query cost ceiling
                if iteration_cost >= self.settings.tool_cost_limit:
                    logger.warning(
                        "Tool cost limit reached ($%.4f >= $%.2f) after %d iterations",
                        iteration_cost, self.settings.tool_cost_limit, iteration,
                    )
                    # Extract any text from last response
                    for block in response.content:
                        if hasattr(block, "text"):
                            assistant_message += block.text
                    if not assistant_message:
                        assistant_message = (
                            "[Tool cost limit reached. Returning partial results. "
                            f"Spent ${iteration_cost:.4f} across {iteration} iterations.]"
                        )
                    break

                continue  # Loop back for Claude's next response

            # stop_reason == "end_turn" — extract final text
            for block in response.content:
                if hasattr(block, "text"):
                    assistant_message += block.text
            break
        else:
            # Hit MAX_TOOL_ITERATIONS
            logger.warning("Hit max tool iterations (%d)", self.MAX_TOOL_ITERATIONS)
            if not assistant_message:
                assistant_message = (
                    f"[Reached maximum tool iterations ({self.MAX_TOOL_ITERATIONS}). "
                    "Returning partial results.]"
                )

        # Add assistant response to session
        self.session.add_message(
            "assistant",
            assistant_message,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

        # Persist session
        self.session_manager.save(self.session)

        # Post-response: store memories and detect corrections
        self._post_response_learning(user_message, assistant_message)

        return assistant_message

    def _estimate_response_cost(self, response: Any) -> float:
        """Estimate cost of a single API response for budget tracking.

        Accounts for cached tokens at 0.1x rate to match actual billing.
        """
        model = response.model.lower()
        if "opus" in model:
            input_rate, output_rate = 5.0, 25.0
        elif "sonnet" in model:
            input_rate, output_rate = 3.0, 15.0
        elif "haiku" in model:
            input_rate, output_rate = 1.0, 5.0
        else:
            input_rate, output_rate = 5.0, 25.0  # Conservative default

        per_token_input = input_rate / 1_000_000
        cached_tokens = self._extract_cached_tokens(response.usage)
        non_cached = max(0, response.usage.input_tokens - cached_tokens)

        input_cost = (non_cached * per_token_input) + (cached_tokens * per_token_input * 0.1)
        output_cost = response.usage.output_tokens * output_rate / 1_000_000
        return input_cost + output_cost

    async def chat_stream(
        self,
        user_message: str,
        task_type: TaskType | None = None,
        audit_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Send a message and stream the response.

        When tools are enabled, falls back to non-streaming chat() since
        streaming with tool use requires more complex handling. The full
        response is yielded as a single chunk.

        Args:
            user_message: The user's message
            task_type: Optional task type for cost tracking
            audit_id: Optional audit/project ID for cost attribution

        Yields:
            Response text chunks as they arrive
        """
        # Fall back to non-streaming when tools are active
        if self._should_use_tools() and get_tools_for_role(self.ROLE):
            result = await self.chat(user_message, task_type=task_type, audit_id=audit_id)
            yield result
            return

        # Add user message to session
        self.session.add_message("user", user_message)

        # Build messages for API
        messages = self._get_messages()

        # Call Claude API with streaming
        full_response = ""
        input_tokens = 0
        output_tokens = 0
        model_used = self.config.model or self.settings.default_model

        with self.client.messages.stream(
            model=self.config.model or self.settings.default_model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=self._build_system_prompt(query=user_message),
            messages=messages,  # type: ignore[arg-type]
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                yield text

            # Get final message for usage stats
            final_message = stream.get_final_message()
            if final_message:
                input_tokens = final_message.usage.input_tokens
                output_tokens = final_message.usage.output_tokens
                model_used = final_message.model

        # Add complete response to session
        self.session.add_message(
            "assistant",
            full_response,
            model=model_used,
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        )

        # Log usage to cost tracker (Directive D10)
        self.cost_tracker.log_usage(
            agent=self.ROLE.upper(),
            model=model_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            task_type=task_type or self.DEFAULT_TASK_TYPE,
            session_id=self.session.id,
            audit_id=audit_id,
        )

        # Persist session
        self.session_manager.save(self.session)

        # Post-response: store memories and detect corrections
        self._post_response_learning(user_message, full_response)

    def _post_response_learning(self, user_message: str, assistant_message: str) -> None:
        """Store memories, detect corrections, and self-evaluate after a response."""
        # Auto-detect corrections in user message
        if ExperienceLog.detect_correction(user_message):
            self.experience_log.add_lesson(
                self.ROLE, f"User correction: {user_message[:300]}"
            )

        # Extract and store memories from response (async-safe, fire-and-forget)
        if self.memory_store.enabled:
            try:
                from csuite.memory.extractor import extract_memories
                memories = extract_memories(assistant_message, self.ROLE)
                for mem in memories:
                    self.memory_store.store(
                        role=self.ROLE,
                        content=mem.get("content", ""),
                        memory_type=mem.get("memory_type", "analysis"),
                        session_id=self.session.id,
                        summary=mem.get("summary", ""),
                    )
            except Exception:
                logger.warning("Post-response memory storage failed", exc_info=True)

        # Self-evaluate artifact quality (closed-loop learning)
        self._self_evaluate(assistant_message)

    def _self_evaluate(self, artifact_text: str) -> None:
        """Run self-evaluation on artifact and store score in feedback loop."""
        try:
            from csuite.learning.feedback_loop import FeedbackStore, SelfEvaluator
            evaluator = SelfEvaluator()
            score = evaluator.evaluate(
                artifact_text=artifact_text,
                event_type="agent_response",
                agent_role=self.ROLE,
            )
            store = FeedbackStore()
            store.store_score(score, artifact_text)
        except Exception:
            logger.debug("Self-evaluation skipped", exc_info=True)

    def record_feedback(
        self, message_index: int, feedback_type: str, detail: str = ""
    ) -> None:
        """Record user feedback on a specific message."""
        # Update message metadata if index is valid
        if 0 <= message_index < len(self.session.messages):
            msg = self.session.messages[message_index]
            msg.metadata["feedback"] = feedback_type
            if detail:
                msg.metadata["feedback_detail"] = detail
            self.session_manager.save(self.session)

        # Route to preference tracker
        self.preference_tracker.record_feedback(
            role=self.ROLE,
            feedback_type=feedback_type,
            detail=detail,
            session_id=self.session.id,
            message_index=message_index,
        )

        # If correction, add to experience log
        if feedback_type == "correction" and detail:
            self.experience_log.add_lesson(self.ROLE, detail)

    def display_response(self, response: str) -> None:
        """Display a response with rich formatting."""
        self.console.print()
        self.console.print(
            Panel(
                Markdown(response),
                title=f"[bold blue]{self.config.name}[/bold blue]",
                border_style="blue",
            )
        )
        self.console.print()

    def get_session_id(self) -> str:
        """Get the current session ID."""
        return self.session.id

    def resume_session(self, session_id: str) -> bool:
        """Resume a previous session.

        Args:
            session_id: The session ID to resume

        Returns:
            True if session was found and resumed, False otherwise
        """
        session = self.session_manager.load(session_id, self.ROLE)
        if session:
            self.session = session
            return True
        return False

    def fork_session(self, title: str) -> Session | None:
        """Fork the current session.

        Args:
            title: Title for the forked session

        Returns:
            The new forked session, or None if fork failed
        """
        forked = self.session_manager.fork(self.session.id, title, self.ROLE)
        if forked:
            self.session = forked
        return forked

    def list_sessions(self, limit: int = 20) -> list[Session]:
        """List previous sessions for this agent."""
        return self.session_manager.list_sessions(self.ROLE, limit)

    def clear_session(self) -> None:
        """Start a fresh session."""
        self.session = self.session_manager.create_session(self.ROLE)

    # =========================================================================
    # Cost Tracking Methods (Directive D10)
    # =========================================================================

    def get_session_cost_summary(self) -> dict[str, Any]:
        """Get cost summary for the current session.

        Returns:
            Dictionary with cost metrics for this session including:
            - total_cost: Total $ spent in this session
            - query_count: Number of API calls
            - avg_cost_per_query: Average cost per call
            - total_input_tokens: Total input tokens
            - total_output_tokens: Total output tokens
            - by_task_type: Cost breakdown by task type
        """
        # Calculate from session messages with usage metadata
        total_cost = 0.0
        total_input = 0
        total_output = 0
        query_count = 0
        by_task_type: dict[str, float] = {}

        # Get cost records for this session from tracker
        records = self.cost_tracker._load_records()
        session_records = [r for r in records if r.session_id == self.session.id]

        for record in session_records:
            total_cost += record.total_cost
            total_input += record.input_tokens
            total_output += record.output_tokens
            query_count += 1

            task = record.task_type.value
            by_task_type[task] = by_task_type.get(task, 0) + record.total_cost

        return {
            "session_id": self.session.id,
            "agent": self.ROLE.upper(),
            "total_cost": round(total_cost, 4),
            "query_count": query_count,
            "avg_cost_per_query": round(total_cost / query_count, 4) if query_count > 0 else 0,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "by_task_type": {k: round(v, 4) for k, v in by_task_type.items()},
        }

    def get_agent_cost_summary(self, days: int = 7) -> dict[str, Any]:
        """Get cost summary for this agent over a time period.

        Args:
            days: Number of days to look back (default 7)

        Returns:
            Dictionary with cost metrics for this agent
        """
        from datetime import datetime, timedelta

        start_date = datetime.now() - timedelta(days=days)
        metrics = self.cost_tracker.get_metrics(start_date=start_date)

        agent_key = self.ROLE.upper()

        return {
            "agent": agent_key,
            "period_days": days,
            "total_cost": round(metrics.cost_by_agent.get(agent_key, 0), 4),
            "query_count": metrics.queries_by_agent.get(agent_key, 0),
            "pct_of_total": round(
                metrics.cost_by_agent.get(agent_key, 0) / metrics.total_cost * 100, 1
            ) if metrics.total_cost > 0 else 0,
            "comparison": {
                "total_all_agents": round(metrics.total_cost, 4),
                "avg_per_agent": round(
                    metrics.total_cost / len(metrics.cost_by_agent), 4
                ) if metrics.cost_by_agent else 0,
            },
        }

    def display_cost_summary(self) -> None:
        """Display session cost summary with rich formatting."""
        summary = self.get_session_cost_summary()

        self.console.print()
        self.console.print(
            Panel(
                f"""[bold]Session Cost Summary[/bold]

Session ID: {summary['session_id']}
Agent: {summary['agent']}

[yellow]Total Cost:[/yellow] ${summary['total_cost']:.4f}
[yellow]Queries:[/yellow] {summary['query_count']}
[yellow]Avg/Query:[/yellow] ${summary['avg_cost_per_query']:.4f}

[dim]Input Tokens:[/dim] {summary['total_input_tokens']:,}
[dim]Output Tokens:[/dim] {summary['total_output_tokens']:,}
""",
                title="[bold cyan]Cost Tracking (D10)[/bold cyan]",
                border_style="cyan",
            )
        )
        self.console.print()
