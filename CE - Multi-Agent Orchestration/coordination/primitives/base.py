"""Base primitive interface — the atomic building blocks of coordination.

Each primitive is a callable unit with typed input/output, cost estimate,
and trace metadata. Primitives are the vocabulary agents use during open
conversation and autonomous coordination.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PrimitiveType(str, Enum):
    """The 9 canonical coordination primitives."""
    DECOMPOSE = "decompose"
    PROPOSE = "propose"
    CHALLENGE = "challenge"
    RETRIEVE = "retrieve"
    SIMULATE = "simulate"
    SCORE = "score"
    RECONCILE = "reconcile"
    ESCALATE = "escalate"
    COMPRESS = "compress"


class PrimitiveInput(BaseModel):
    """Typed input for a primitive execution."""
    content: str
    context: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)


class PrimitiveOutput(BaseModel):
    """Typed output from a primitive execution."""
    content: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PrimitiveTrace(BaseModel):
    """Trace metadata for a single primitive execution."""
    primitive_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    primitive_type: PrimitiveType
    agent_id: str | None = None
    input_summary: str = ""
    output_summary: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    started_at: float = Field(default_factory=time.time)
    completed_at: float | None = None


class Primitive(ABC):
    """Base class for all coordination primitives.

    Each primitive is a callable unit that:
    - Takes typed PrimitiveInput
    - Returns typed PrimitiveOutput
    - Produces a PrimitiveTrace for observability
    - Has a cost estimate for budget planning
    """

    primitive_type: PrimitiveType

    @abstractmethod
    async def execute(
        self,
        input: PrimitiveInput,
        agent_id: str | None = None,
    ) -> tuple[PrimitiveOutput, PrimitiveTrace]:
        """Execute this primitive and return output + trace."""
        ...

    def estimate_cost(self, input: PrimitiveInput) -> float:
        """Estimate the cost of executing this primitive. Override for accuracy."""
        return 0.01  # Conservative default: $0.01 per primitive call


class Composition(BaseModel):
    """A sequence of primitives that forms a coordination pattern.

    Compositions are data, not code. They can be stored as JSON,
    mutated, and evolved by the learning system.
    """
    composition_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: list[CompositionStep] = Field(default_factory=list)
    parent_id: str | None = None  # Lineage tracking for mutations
    source: str = "authored"  # "authored", "extracted", "mutated"


class CompositionStep(BaseModel):
    """A single step in a composition."""
    primitive_type: PrimitiveType
    config: dict[str, Any] = Field(default_factory=dict)
    parallel_with: list[int] = Field(default_factory=list)  # Indices of steps to run in parallel
    condition: str | None = None  # Optional: "if score < 0.5" style condition for branching


# Fix forward reference
Composition.model_rebuild()
