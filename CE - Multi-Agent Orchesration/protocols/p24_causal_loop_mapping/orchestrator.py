"""P24: Causal Loop Mapping — Orchestrator.

Extract system variables, identify causal links, trace feedback loops,
and find leverage points for intervention.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import anthropic

from .prompts import (
    VARIABLE_EXTRACTION_PROMPT,
    DEDUPLICATION_PROMPT,
    CAUSAL_LINK_PROMPT,
    LEVERAGE_POINT_PROMPT,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Variable:
    id: str
    name: str
    description: str


@dataclass
class CausalLink:
    from_var: str
    to_var: str
    polarity: str  # "+" or "-"
    reasoning: str = ""


@dataclass
class FeedbackLoop:
    id: str
    loop_type: str  # "reinforcing" or "balancing"
    path: list[str]  # ordered variable IDs forming the cycle
    polarities: list[str]  # polarity of each link in the path


@dataclass
class CausalLoopResult:
    question: str
    variables: list[Variable]
    causal_links: list[CausalLink]
    reinforcing_loops: list[FeedbackLoop]
    balancing_loops: list[FeedbackLoop]
    leverage_points: dict[str, Any]
    timings: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class CausalLoopOrchestrator:
    """Runs the five-phase Causal Loop Mapping protocol."""

    thinking_model: str = "claude-opus-4-6"
    orchestration_model: str = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        agents: list[dict[str, str]],
        *,
        thinking_model: str | None = None,
        orchestration_model: str | None = None,
        thinking_budget: int = 10_000,
    ) -> None:
        self.agents = agents  # [{"name": ..., "system_prompt": ...}, ...]
        if thinking_model:
            self.thinking_model = thinking_model
        if orchestration_model:
            self.orchestration_model = orchestration_model
        self.thinking_budget = thinking_budget
        self.client = anthropic.AsyncAnthropic()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self, question: str) -> CausalLoopResult:
        timings: dict[str, float] = {}

        # Phase 1 — Extract Variables (parallel, Opus)
        t0 = time.time()
        raw_variables = await self._extract_variables(question)
        timings["phase1_extract_variables"] = time.time() - t0

        # Phase 2 — Deduplicate Variables (Haiku)
        t0 = time.time()
        variables = await self._deduplicate_variables(question, raw_variables)
        timings["phase2_deduplicate"] = time.time() - t0

        # Phase 3 — Identify Causal Links (parallel, Opus)
        t0 = time.time()
        raw_links = await self._identify_links(question, variables)
        timings["phase3_identify_links"] = time.time() - t0

        # Phase 4 — Merge Links & Trace Loops (computation, no LLM)
        t0 = time.time()
        causal_links = self._merge_links(raw_links, variables)
        reinforcing_loops, balancing_loops = self._trace_loops(causal_links, variables)
        timings["phase4_merge_trace"] = time.time() - t0

        # Phase 5 — Leverage Point Analysis (Opus)
        t0 = time.time()
        leverage_points = await self._leverage_analysis(
            question, variables, causal_links, reinforcing_loops, balancing_loops,
        )
        timings["phase5_leverage_analysis"] = time.time() - t0

        return CausalLoopResult(
            question=question,
            variables=variables,
            causal_links=causal_links,
            reinforcing_loops=reinforcing_loops,
            balancing_loops=balancing_loops,
            leverage_points=leverage_points,
            timings=timings,
        )

    # ------------------------------------------------------------------
    # Phase 1: Extract Variables
    # ------------------------------------------------------------------

    async def _extract_variables(self, question: str) -> list[dict]:
        """Each agent identifies system variables in parallel (Opus)."""

        async def _one(agent: dict) -> list[dict]:
            prompt = VARIABLE_EXTRACTION_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            return parsed.get("variables", [])

        results = await asyncio.gather(*[_one(a) for a in self.agents])
        return [v for batch in results for v in batch]

    # ------------------------------------------------------------------
    # Phase 2: Deduplicate Variables
    # ------------------------------------------------------------------

    async def _deduplicate_variables(
        self, question: str, raw_variables: list[dict],
    ) -> list[Variable]:
        """Merge and deduplicate variables via Haiku."""
        raw_block = "\n".join(
            f"- {v.get('name', '???')}: {v.get('description', '')}"
            for v in raw_variables
        )
        prompt = DEDUPLICATION_PROMPT.format(
            question=question,
            raw_variables_block=raw_block,
        )
        resp = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = self._parse_json_object(self._extract_text(resp))
        variables = []
        for v in parsed.get("variables", []):
            variables.append(Variable(
                id=v.get("id", ""),
                name=v.get("name", ""),
                description=v.get("description", ""),
            ))
        return variables

    # ------------------------------------------------------------------
    # Phase 3: Identify Causal Links
    # ------------------------------------------------------------------

    async def _identify_links(
        self, question: str, variables: list[Variable],
    ) -> list[dict]:
        """Each agent identifies causal links in parallel (Opus)."""
        var_block = self._format_variables_block(variables)

        async def _one(agent: dict) -> list[dict]:
            prompt = CAUSAL_LINK_PROMPT.format(
                question=question,
                agent_name=agent["name"],
                system_prompt=agent["system_prompt"],
                variables_block=var_block,
            )
            resp = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=self.thinking_budget + 4096,
                thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = self._parse_json_object(self._extract_text(resp))
            return parsed.get("links", [])

        results = await asyncio.gather(*[_one(a) for a in self.agents])
        return [link for batch in results for link in batch]

    # ------------------------------------------------------------------
    # Phase 4: Merge Links & Trace Loops (pure computation)
    # ------------------------------------------------------------------

    def _merge_links(
        self, raw_links: list[dict], variables: list[Variable],
    ) -> list[CausalLink]:
        """Merge links with majority vote on polarity for conflicting pairs."""
        valid_ids = {v.id for v in variables}

        # Group by (from, to) pair
        buckets: dict[tuple[str, str], list[str]] = {}
        reasoning_map: dict[tuple[str, str], list[str]] = {}
        for link in raw_links:
            from_var = link.get("from", "").strip()
            to_var = link.get("to", "").strip()
            polarity = link.get("polarity", "+").strip()
            if from_var not in valid_ids or to_var not in valid_ids:
                continue
            if from_var == to_var:
                continue
            if polarity not in ("+", "-"):
                polarity = "+"
            key = (from_var, to_var)
            buckets.setdefault(key, []).append(polarity)
            reasoning_map.setdefault(key, []).append(link.get("reasoning", ""))

        # Majority vote on polarity
        merged: list[CausalLink] = []
        for (from_var, to_var), polarities in buckets.items():
            winner = Counter(polarities).most_common(1)[0][0]
            best_reasoning = reasoning_map[(from_var, to_var)][0]
            merged.append(CausalLink(
                from_var=from_var,
                to_var=to_var,
                polarity=winner,
                reasoning=best_reasoning,
            ))
        return merged

    def _trace_loops(
        self,
        links: list[CausalLink],
        variables: list[Variable],
    ) -> tuple[list[FeedbackLoop], list[FeedbackLoop]]:
        """Find closed cycles in the causal graph via DFS.

        A loop is Reinforcing if the product of polarities is positive
        (all '+' or even number of '-'). A loop is Balancing if the
        product is negative (odd number of '-').
        """
        # Build adjacency list: node -> [(neighbor, polarity)]
        adj: dict[str, list[tuple[str, str]]] = {}
        for link in links:
            adj.setdefault(link.from_var, []).append((link.to_var, link.polarity))

        all_nodes = {v.id for v in variables}
        found_cycles: list[tuple[list[str], list[str]]] = []  # (path, polarities)
        seen_cycle_keys: set[frozenset[tuple[str, str]]] = set()

        def _dfs(
            start: str,
            current: str,
            path: list[str],
            polarities: list[str],
            visited: set[str],
        ) -> None:
            for neighbor, polarity in adj.get(current, []):
                if neighbor == start and len(path) >= 2:
                    # Found a cycle — canonicalize to avoid duplicates
                    edge_set = frozenset(
                        (path[i], path[i + 1] if i + 1 < len(path) else start)
                        for i in range(len(path))
                    )
                    if edge_set not in seen_cycle_keys:
                        seen_cycle_keys.add(edge_set)
                        found_cycles.append(
                            (path + [current], polarities + [polarity]),
                        )
                elif neighbor not in visited and len(path) < 8:
                    visited.add(neighbor)
                    _dfs(start, neighbor, path + [current], polarities + [polarity], visited)
                    visited.discard(neighbor)

        for node in all_nodes:
            _dfs(node, node, [], [], {node})

        reinforcing: list[FeedbackLoop] = []
        balancing: list[FeedbackLoop] = []
        r_idx = 1
        b_idx = 1

        for path, polarities in found_cycles:
            neg_count = polarities.count("-")
            if neg_count % 2 == 0:
                reinforcing.append(FeedbackLoop(
                    id=f"R{r_idx}",
                    loop_type="reinforcing",
                    path=path,
                    polarities=polarities,
                ))
                r_idx += 1
            else:
                balancing.append(FeedbackLoop(
                    id=f"B{b_idx}",
                    loop_type="balancing",
                    path=path,
                    polarities=polarities,
                ))
                b_idx += 1

        return reinforcing, balancing

    # ------------------------------------------------------------------
    # Phase 5: Leverage Point Analysis
    # ------------------------------------------------------------------

    async def _leverage_analysis(
        self,
        question: str,
        variables: list[Variable],
        links: list[CausalLink],
        reinforcing: list[FeedbackLoop],
        balancing: list[FeedbackLoop],
    ) -> dict[str, Any]:
        var_block = self._format_variables_block(variables)
        links_block = "\n".join(
            f"- {l.from_var} --({l.polarity})--> {l.to_var}: {l.reasoning}"
            for l in links
        )
        reinforcing_block = self._format_loops_block(reinforcing) or "None detected"
        balancing_block = self._format_loops_block(balancing) or "None detected"

        prompt = LEVERAGE_POINT_PROMPT.format(
            question=question,
            variables_block=var_block,
            links_block=links_block,
            reinforcing_block=reinforcing_block,
            balancing_block=balancing_block,
        )

        resp = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=self.thinking_budget + 4096,
            thinking={"type": "enabled", "budget_tokens": self.thinking_budget},
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

    @staticmethod
    def _format_variables_block(variables: list[Variable]) -> str:
        return "\n".join(
            f"- {v.id}: {v.name} — {v.description}" for v in variables
        )

    @staticmethod
    def _format_loops_block(loops: list[FeedbackLoop]) -> str:
        lines = []
        for loop in loops:
            path_str = " -> ".join(loop.path) + " -> " + loop.path[0]
            pol_str = " -> ".join(loop.polarities)
            lines.append(f"- {loop.id} ({loop.loop_type}): {path_str} [polarities: {pol_str}]")
        return "\n".join(lines)
