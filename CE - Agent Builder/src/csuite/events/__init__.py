"""
Event architecture for C-Suite discrete callable events.

Each event is independently invoked, produces structured output, and can
optionally write to Notion. Events compose existing engines (orchestrator,
debate, audit) — they never modify them.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from csuite.tools.cost_tracker import CostTracker


class EventResult(BaseModel):
    """Structured output from any event."""

    event_id: str
    event_type: str
    topic: str
    markdown_output: str = ""
    agent_outputs: dict[str, str] = Field(default_factory=dict)
    synthesis: str | None = None
    process_narrative: str = ""
    total_cost: float = 0.0
    notion_url: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    duration_minutes: float = 0.0


class EventBase(ABC):
    """Base class for all discrete callable events."""

    event_type: str = "base"

    def __init__(
        self,
        topic: str,
        agents: list[str] | None = None,
        cost_tracker: CostTracker | None = None,
    ):
        self.event_id = f"{self.event_type}-{uuid.uuid4().hex[:8]}"
        self.topic = topic
        self.agents = agents or ["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"]
        self.cost_tracker = cost_tracker or CostTracker()
        self.created_at = datetime.now()

    @abstractmethod
    async def run(self) -> EventResult:
        """Execute the event and return structured output."""
        ...

    def _build_result(self, **kwargs: Any) -> EventResult:
        """Helper to build an EventResult with common fields pre-filled."""
        return EventResult(
            event_id=self.event_id,
            event_type=self.event_type,
            topic=self.topic,
            created_at=self.created_at,
            **kwargs,
        )
