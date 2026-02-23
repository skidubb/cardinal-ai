"""P12: 25/10 Crowd Sourcing Protocol — Agent-agnostic orchestrator.

"Rapid idea generation followed by blind scoring to surface top ideas."

The protocol mirrors the Liberating Structure: each agent writes one bold idea
on a "card", then ideas are anonymized and cross-scored over multiple rounds.
Top 25% of ideas are highlighted.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
from dataclasses import dataclass, field

import anthropic

from .prompts import IDEA_GENERATION_PROMPT, SCORING_PROMPT, SYNTHESIS_PROMPT


@dataclass
class IdeaCard:
    id: int
    author: str  # only revealed in final output
    title: str
    idea: str
    bold_because: str
    scores: list[dict] = field(default_factory=list)  # each: {scorer, boldness, feasibility, impact, overall, reaction}
    avg_overall: float = 0.0
    avg_boldness: float = 0.0
    avg_feasibility: float = 0.0
    avg_impact: float = 0.0
    total_score: float = 0.0
    is_top_quartile: bool = False


@dataclass
class TwentyFiveTenResult:
    challenge: str
    ideas: list[IdeaCard] = field(default_factory=list)
    synthesis: str = ""
    scoring_rounds: int = 0
    total_scores_cast: int = 0


class TwentyFiveTenOrchestrator:
    """Runs the 25/10 Crowd Sourcing protocol with any set of agents."""

    def __init__(
        self,
        agents: list[dict],
        thinking_model: str = "claude-opus-4-6",
        orchestration_model: str = "claude-haiku-4-5-20251001",
        scoring_rounds: int = 5,
    ):
        if not agents or len(agents) < 2:
            raise ValueError("At least 2 agents required for cross-scoring")
        self.agents = agents
        self.thinking_model = thinking_model
        self.orchestration_model = orchestration_model
        self.scoring_rounds = scoring_rounds
        self.client = anthropic.AsyncAnthropic()

    async def run(self, challenge: str) -> TwentyFiveTenResult:
        """Execute the full 25/10 protocol."""
        result = TwentyFiveTenResult(
            challenge=challenge,
            scoring_rounds=self.scoring_rounds,
        )

        # Phase 1: Each agent generates one bold idea
        print("Phase 1: Generating idea cards...")
        ideas = await self._generate_ideas(challenge)
        result.ideas = ideas

        # Phase 2: Blind cross-scoring over N rounds
        # Each round, each agent scores one random idea they haven't scored yet
        # and didn't author
        print(f"Phase 2: Blind scoring ({self.scoring_rounds} rounds)...")
        await self._score_ideas(challenge, ideas)
        result.total_scores_cast = sum(len(idea.scores) for idea in ideas)

        # Compute averages and rank
        self._compute_rankings(ideas)

        # Mark top 25%
        top_count = max(1, len(ideas) // 4)
        for i, idea in enumerate(ideas):
            idea.is_top_quartile = i < top_count

        # Phase 3: Synthesize
        print("Phase 3: Synthesizing results...")
        result.synthesis = await self._synthesize(challenge, ideas)

        return result

    async def _generate_ideas(self, challenge: str) -> list[IdeaCard]:
        """Phase 1: Each agent writes one idea card."""
        prompt = IDEA_GENERATION_PROMPT.format(question=challenge)

        async def gen_idea(idx: int, agent: dict) -> IdeaCard:
            response = await self.client.messages.create(
                model=self.thinking_model,
                max_tokens=1024,
                system=agent["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
            )
            text = _extract_text(response)
            return _parse_idea_card(idx, agent["name"], text)

        cards = await asyncio.gather(
            *(gen_idea(i, agent) for i, agent in enumerate(self.agents))
        )
        return list(cards)

    async def _score_ideas(
        self, challenge: str, ideas: list[IdeaCard]
    ) -> None:
        """Phase 2: Multiple rounds of blind cross-scoring.

        Each round, each agent scores one idea they haven't scored yet and
        didn't write. Ideas are assigned randomly to maximize diversity.
        """
        agent_names = [a["name"] for a in self.agents]
        # Track what each agent has scored
        scored_by: dict[str, set[int]] = {name: set() for name in agent_names}

        for round_num in range(self.scoring_rounds):
            print(f"  Round {round_num + 1}/{self.scoring_rounds}...")
            round_tasks = []

            for agent in self.agents:
                name = agent["name"]
                # Find ideas this agent can score (not authored, not yet scored)
                eligible = [
                    idea for idea in ideas
                    if idea.author != name and idea.id not in scored_by[name]
                ]
                if not eligible:
                    continue
                # Pick a random eligible idea
                idea = random.choice(eligible)
                scored_by[name].add(idea.id)
                round_tasks.append(
                    self._score_single(challenge, agent, idea)
                )

            if round_tasks:
                await asyncio.gather(*round_tasks)

    async def _score_single(
        self, challenge: str, agent: dict, idea: IdeaCard
    ) -> None:
        """Score a single idea card (anonymized)."""
        # Anonymize the card
        card_text = f"TITLE: {idea.title}\nIDEA: {idea.idea}\nBOLD BECAUSE: {idea.bold_because}"
        response = await self.client.messages.create(
            model=self.orchestration_model,
            max_tokens=256,
            system=agent["system_prompt"],
            messages=[{
                "role": "user",
                "content": SCORING_PROMPT.format(
                    question=challenge, idea_card=card_text
                ),
            }],
        )
        text = _extract_text(response)
        try:
            score_data = _parse_json_object(text)
            idea.scores.append({
                "scorer": agent["name"],
                "boldness": score_data.get("boldness", 3),
                "feasibility": score_data.get("feasibility", 3),
                "impact": score_data.get("impact", 3),
                "overall": score_data.get("overall", 3),
                "reaction": score_data.get("one_line_reaction", ""),
            })
        except (json.JSONDecodeError, ValueError):
            # Fallback: assign neutral score
            idea.scores.append({
                "scorer": agent["name"],
                "boldness": 3, "feasibility": 3, "impact": 3, "overall": 3,
                "reaction": "(scoring parse error)",
            })

    def _compute_rankings(self, ideas: list[IdeaCard]) -> None:
        """Compute averages and sort by total score."""
        for idea in ideas:
            if idea.scores:
                n = len(idea.scores)
                idea.avg_overall = sum(s["overall"] for s in idea.scores) / n
                idea.avg_boldness = sum(s["boldness"] for s in idea.scores) / n
                idea.avg_feasibility = sum(s["feasibility"] for s in idea.scores) / n
                idea.avg_impact = sum(s["impact"] for s in idea.scores) / n
                idea.total_score = sum(s["overall"] for s in idea.scores)
        ideas.sort(key=lambda i: i.total_score, reverse=True)

    async def _synthesize(self, challenge: str, ideas: list[IdeaCard]) -> str:
        """Phase 3: Produce strategic briefing."""
        ranked = json.dumps(
            [
                {
                    "rank": i + 1,
                    "title": idea.title,
                    "idea": idea.idea,
                    "bold_because": idea.bold_because,
                    "author": idea.author,
                    "total_score": idea.total_score,
                    "avg_overall": round(idea.avg_overall, 2),
                    "avg_boldness": round(idea.avg_boldness, 2),
                    "avg_feasibility": round(idea.avg_feasibility, 2),
                    "avg_impact": round(idea.avg_impact, 2),
                    "num_scores": len(idea.scores),
                    "is_top_quartile": idea.is_top_quartile,
                    "scorer_reactions": [
                        {"scorer": s["scorer"], "overall": s["overall"], "reaction": s["reaction"]}
                        for s in idea.scores
                    ],
                }
                for i, idea in enumerate(ideas)
            ],
            indent=2,
        )
        response = await self.client.messages.create(
            model=self.thinking_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.format(
                    question=challenge, ranked_results=ranked
                ),
            }],
        )
        return _extract_text(response)


def _extract_text(response) -> str:
    """Get text from an Anthropic response."""
    for block in response.content:
        if hasattr(block, "text") and block.text:
            return block.text
    block_info = [type(b).__name__ for b in response.content]
    raise RuntimeError(
        f"No text in response. Stop: {response.stop_reason}, "
        f"usage: in={response.usage.input_tokens} out={response.usage.output_tokens}, "
        f"blocks: {block_info}"
    )


def _parse_idea_card(idx: int, author: str, text: str) -> IdeaCard:
    """Parse agent's idea card response into structured form."""
    title = ""
    idea = ""
    bold = ""
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.upper().startswith("TITLE:"):
            title = line.split(":", 1)[1].strip()
        elif line.upper().startswith("IDEA:"):
            idea = line.split(":", 1)[1].strip()
        elif line.upper().startswith("BOLD BECAUSE:"):
            bold = line.split(":", 1)[1].strip()
    # Fallback if parsing is loose
    if not title:
        title = text[:60].strip()
    if not idea:
        idea = text.strip()
    return IdeaCard(id=idx, author=author, title=title, idea=idea, bold_because=bold)


def _parse_json_object(text: str) -> dict:
    """Extract a JSON object from LLM output."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n(.*?)(?:```|$)", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
    return json.loads(text)
