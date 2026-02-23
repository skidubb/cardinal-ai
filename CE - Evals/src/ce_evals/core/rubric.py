"""Rubric system — loads evaluation dimensions from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class Dimension(BaseModel):
    """A single scoring dimension."""

    name: str
    description: str
    scale_min: int = 1
    scale_max: int = 5


class Rubric(BaseModel):
    """Evaluation rubric with dimensions and judge prompt template."""

    name: str
    dimensions: list[Dimension]
    judge_system_prompt: str
    context_line: str = ""
    """Optional one-liner describing who the judge is evaluating for."""

    @classmethod
    def from_yaml(cls, path: str | Path) -> Rubric:
        with open(path) as f:
            data = yaml.safe_load(f)
        dims = [Dimension(**d) for d in data["dimensions"]]
        return cls(
            name=data["name"],
            dimensions=dims,
            judge_system_prompt=data.get("judge_system_prompt", ""),
            context_line=data.get("context_line", ""),
        )

    def render_dimensions_block(self) -> str:
        """Render dimensions as numbered list for inclusion in judge prompt."""
        lines = []
        for i, d in enumerate(self.dimensions, 1):
            lines.append(
                f"{i}. **{d.name.replace('_', ' ').title()}** "
                f"({d.scale_min}-{d.scale_max}): {d.description}"
            )
        return "\n".join(lines)

    def build_judge_prompt(self) -> str:
        """Build full judge system prompt with dimensions injected."""
        if self.judge_system_prompt:
            return self.judge_system_prompt.replace(
                "{{dimensions}}", self.render_dimensions_block()
            )
        # Fallback: generic prompt
        return (
            f"You are an expert evaluator. {self.context_line}\n\n"
            f"Score each response on these dimensions:\n\n"
            f"{self.render_dimensions_block()}\n\n"
            f"After scoring, provide a forced ranking of all responses from best to worst.\n\n"
            f"Respond ONLY with valid JSON in this format:\n"
            f'{{"scores": {{"Response A": {{"dim": N, ...}}, ...}}, '
            f'"ranking": ["Response X", ...], '
            f'"reasoning": "Brief explanation."}}'
        )

    @property
    def dimension_names(self) -> list[str]:
        return [d.name for d in self.dimensions]
