"""
CEO Agent - Chief Executive Officer

Strategic visionary for market positioning, competitive strategy, and high-stakes decisions.
Specializes in vision, positioning, and asymmetric advantage for service businesses.
"""

from csuite.agents.base import BaseAgent
from csuite.prompts import CEO_SYSTEM_PROMPT


class CEOAgent(BaseAgent):
    """Chief Executive Officer Agent.

    Expertise areas:
    - Strategic vision and market positioning
    - Competitive moat analysis
    - Growth strategy (organic and inorganic)
    - Market dynamics and industry trends
    - High-stakes decision-making
    - Executive team and organizational design

    Uses Opus model for complex strategic reasoning.
    """

    ROLE = "ceo"

    def get_system_prompt(self) -> str:
        """Get the elite CEO system prompt."""
        return CEO_SYSTEM_PROMPT
