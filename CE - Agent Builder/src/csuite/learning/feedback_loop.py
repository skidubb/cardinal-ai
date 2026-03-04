"""
Closed-Loop Learning for C-Suite.

Artifact quality measurably improves over time through self-evaluation
and approval/rejection signals. Stores scores in Pinecone for retrieval
at generation time.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

import anthropic
from pydantic import BaseModel, Field

from csuite.config import HAIKU_MODEL, get_settings
from csuite.memory.provider import get_pinecone_index

logger = logging.getLogger(__name__)


class ArtifactScore(BaseModel):
    """Quality score for an artifact across multiple dimensions."""

    artifact_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_type: str = ""
    agent_role: str = ""
    dimensions: dict[str, float] = Field(default_factory=dict)
    overall: float = 0.0
    timestamp: float = Field(default_factory=time.time)
    approved: bool | None = None  # None = no user signal yet


SELF_EVAL_PROMPT = """\
You are a quality evaluator for AI-generated executive advisory output.

Score the following artifact on these dimensions (1-5 scale each):

1. **clarity**: How clear and well-structured is the output?
2. **actionability**: How specific and actionable are the recommendations?
3. **grounding**: How well-grounded in evidence/data are the claims?
4. **coherence**: How internally consistent is the reasoning?

Artifact type: {event_type}
Agent role: {agent_role}

Artifact:
{artifact_text}

Return ONLY a JSON object with scores:
{{"clarity": N, "actionability": N, "grounding": N, "coherence": N, "overall": N}}

The "overall" score should be a weighted average (actionability and grounding weighted 1.5x).
"""


class SelfEvaluator:
    """Scores artifacts using a Haiku call on 4 quality dimensions."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def evaluate(
        self, artifact_text: str, event_type: str = "", agent_role: str = ""
    ) -> ArtifactScore:
        """Score an artifact. Returns ArtifactScore with dimension scores."""
        try:
            result = self.client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=256,
                temperature=0.0,
                messages=[{
                    "role": "user",
                    "content": SELF_EVAL_PROMPT.format(
                        event_type=event_type or "general",
                        agent_role=agent_role or "unknown",
                        artifact_text=artifact_text[:4000],
                    ),
                }],
            )
            text = result.content[0].text.strip()
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                scores = json.loads(match.group())
                return ArtifactScore(
                    event_type=event_type,
                    agent_role=agent_role,
                    dimensions={
                        k: float(scores.get(k, 3.0))
                        for k in ("clarity", "actionability", "grounding", "coherence")
                    },
                    overall=float(scores.get("overall", 3.0)),
                )
        except Exception:
            logger.warning("Self-evaluation failed", exc_info=True)

        return ArtifactScore(
            event_type=event_type,
            agent_role=agent_role,
            dimensions={"clarity": 3.0, "actionability": 3.0, "grounding": 3.0, "coherence": 3.0},
            overall=3.0,
        )


class FeedbackStore:
    """Stores and retrieves artifact scores via Pinecone namespace 'artifact-feedback'."""

    NAMESPACE = "artifact-feedback"

    def __init__(self) -> None:
        settings = get_settings()
        self.enabled = bool(
            settings.memory_enabled
            and settings.pinecone_api_key
            and settings.pinecone_learning_index_host
        )
        pass

    def store_score(self, score: ArtifactScore, artifact_text: str) -> bool:
        """Store an artifact score with the artifact text as searchable content."""
        if not self.enabled:
            return False
        try:
            index = get_pinecone_index()
            record = {
                "_id": score.artifact_id,
                "text": artifact_text[:2000],
                "event_type": score.event_type,
                "agent_role": score.agent_role,
                "overall_score": score.overall,
                "clarity": score.dimensions.get("clarity", 0),
                "actionability": score.dimensions.get("actionability", 0),
                "grounding": score.dimensions.get("grounding", 0),
                "coherence": score.dimensions.get("coherence", 0),
                "approved": "" if score.approved is None else str(score.approved),
                "timestamp": int(score.timestamp),
            }
            index.upsert_records(namespace=self.NAMESPACE, records=[record])
            return True
        except Exception:
            logger.warning("Failed to store artifact score", exc_info=True)
            return False

    def record_approval(self, artifact_id: str, approved: bool) -> bool:
        """Record user approval/rejection signal for an artifact."""
        if not self.enabled:
            return False
        try:
            index = get_pinecone_index()
            # Update the record's approved field
            index.upsert_records(
                namespace=self.NAMESPACE,
                records=[{"_id": artifact_id, "approved": str(approved)}],
            )
            return True
        except Exception:
            logger.warning("Failed to record approval for %s", artifact_id, exc_info=True)
            return False

    def retrieve_exemplars(
        self, event_type: str, top_k: int = 3
    ) -> list[dict[str, Any]]:
        """Retrieve top-scored prior artifacts of the same type as exemplars."""
        if not self.enabled:
            return []
        try:
            index = get_pinecone_index()
            response = index.search(
                namespace=self.NAMESPACE,
                query={
                    "top_k": top_k,
                    "inputs": {"text": f"high quality {event_type} executive advisory output"},
                },
            )
            results = []
            for hit in response.get("result", {}).get("hits", []):
                fields = hit.get("fields", {})
                results.append({
                    "text": fields.get("text", ""),
                    "overall_score": fields.get("overall_score", 0),
                    "event_type": fields.get("event_type", ""),
                    "approved": fields.get("approved", ""),
                })
            # Sort by score descending
            results.sort(key=lambda r: float(r.get("overall_score", 0)), reverse=True)
            return results[:top_k]
        except Exception:
            logger.warning("Failed to retrieve exemplars", exc_info=True)
            return []


class ApprovalGate:
    """Manages user approval/rejection signals linked to artifact IDs."""

    def __init__(self, feedback_store: FeedbackStore | None = None) -> None:
        self.store = feedback_store or FeedbackStore()

    def approve(self, artifact_id: str) -> bool:
        return self.store.record_approval(artifact_id, approved=True)

    def reject(self, artifact_id: str) -> bool:
        return self.store.record_approval(artifact_id, approved=False)
