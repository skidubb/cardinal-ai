"""P27: Affinity Mapping — Orchestrator.

Generate items, LLM-based semantic clustering, theme labeling, hierarchy synthesis.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic

from .prompts import (
    GENERATE_ITEMS_PROMPT,
    CLUSTER_ITEMS_PROMPT,
    LABEL_VALIDATE_PROMPT,
    HIERARCHY_SYNTHESIS_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AffinityMappingResult:
    question: str
    raw_items: dict[str, list[str]]
    total_items: int
    clusters: list[dict[str, Any]]
    themed_clusters: list[dict[str, Any]]
    hierarchy: list[dict[str, Any]]
    strategic_insights: list[str]
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class AffinityMappingOrchestrator:
    """Runs the four-phase Affinity Mapping protocol."""

    thinking_model: str = "claude-opus-4-6"
    orchestration_model: str = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        agents: list[dict[str, str]],
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
    ) -> None:
        self.agents = agents
        if thinking_model:
            self.thinking_model = thinking_model
        if orchestration_model:
            self.orchestration_model = orchestration_model
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self, question: str) -> AffinityMappingResult:
        timings: dict[str, float] = {}

        # Phase 1 — Generate Items (parallel, Opus)
        t0 = time.time()
        raw_items = await self._generate_items(question)
        timings["phase1_generate_items"] = time.time() - t0

        all_items = [item for items in raw_items.values() for item in items]
        total_items = len(all_items)

        # Phase 2 — Pool & Cluster (Haiku)
        t0 = time.time()
        clusters = await self._cluster_items(question, all_items)
        timings["phase2_cluster"] = time.time() - t0

        # Phase 3 — Label & Validate (Haiku)
        t0 = time.time()
        themed_clusters = await self._label_validate(question, clusters)
        timings["phase3_label_validate"] = time.time() - t0

        # Phase 4 — Hierarchy & Synthesis (Opus)
        t0 = time.time()
        synthesis = await self._hierarchy_synthesis(
            question, themed_clusters, total_items, len(self.agents),
        )
        timings["phase4_hierarchy_synthesis"] = time.time() - t0

        return AffinityMappingResult(
            question=question,
            raw_items=raw_items,
            total_items=total_items,
            clusters=clusters,
            themed_clusters=themed_clusters,
            hierarchy=synthesis.get("hierarchy", []),
            strategic_insights=synthesis.get("strategic_insights", []),
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Phase 1: Generate Items
    # ------------------------------------------------------------------

    async def _generate_items(self, question: str) -> dict[str, list[str]]:
        """Each agent generates sticky-note items in parallel (Opus)."""

        async def _one(agent: dict) -> tuple[str, list[str]]:
            prompt = GENERATE_ITEMS_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            return agent["name"], parsed.get("items", [])

        results = await asyncio.gather(*[_one(a) for a in self.agents])
        return {name: items for name, items in results}

    # ------------------------------------------------------------------
    # Phase 2: Pool & Cluster
    # ------------------------------------------------------------------

    async def _cluster_items(
        self, question: str, all_items: list[str],
    ) -> list[dict[str, Any]]:
        """LLM-based semantic clustering via Haiku."""
        items_block = "\n".join(f"- {item}" for item in all_items)
        prompt = CLUSTER_ITEMS_PROMPT.format(
            question=question,
            items_block=items_block,
        )
        resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = self._parse_json_object(self._extract_text(resp))
        return parsed.get("clusters", [])

    # ------------------------------------------------------------------
    # Phase 3: Label & Validate
    # ------------------------------------------------------------------

    async def _label_validate(
        self, question: str, clusters: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Generate descriptive theme names and check for misplaced items (Haiku)."""
        clusters_block = ""
        for i, c in enumerate(clusters, 1):
            items = "\n".join(f"    - {item}" for item in c.get("items", []))
            clusters_block += f"  Cluster {i} — \"{c.get('theme', 'Unnamed')}\":\n{items}\n\n"

        prompt = LABEL_VALIDATE_PROMPT.format(
            question=question,
            clusters_block=clusters_block,
        )
        resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = self._parse_json_object(self._extract_text(resp))
        return parsed.get("themed_clusters", [])

    # ------------------------------------------------------------------
    # Phase 4: Hierarchy & Synthesis
    # ------------------------------------------------------------------

    async def _hierarchy_synthesis(
        self,
        question: str,
        themed_clusters: list[dict[str, Any]],
        total_items: int,
        agent_count: int,
    ) -> dict[str, Any]:
        """Build theme hierarchy and strategic insights (Opus)."""
        themed_block = ""
        for tc in themed_clusters:
            items = "\n".join(f"    - {item}" for item in tc.get("items", []))
            misplaced = tc.get("misplaced", [])
            misplaced_str = f"\n    Misplaced: {misplaced}" if misplaced else ""
            themed_block += (
                f"  **{tc.get('theme_name', 'Unnamed')}**: {tc.get('summary', '')}\n"
                f"{items}{misplaced_str}\n\n"
            )

        prompt = HIERARCHY_SYNTHESIS_PROMPT.format(
            question=question,
            total_items=total_items,
            agent_count=agent_count,
            themed_clusters_block=themed_block,
        )
        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_object(self._extract_text(resp))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(response: anthropic.types.Message) -> str:
        parts = []
        for block in response.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts)

    @staticmethod
    def _parse_json_object(text: str) -> dict:
        """Extract the first JSON object from text."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}
