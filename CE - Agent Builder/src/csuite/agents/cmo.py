"""
CMO Agent - Chief Marketing Officer

Elite marketing and brand strategy advisor for professional services businesses.
Specializes in positioning, thought leadership, and B2B demand generation.
"""

from csuite.agents.base import BaseAgent
from csuite.prompts import CMO_SYSTEM_PROMPT


class CMOAgent(BaseAgent):
    """Chief Marketing Officer Agent.

    Expertise areas:
    - Brand positioning for professional services
    - Thought leadership strategy
    - B2B demand generation
    - Content strategy and marketing
    - Competitive analysis
    - Marketing measurement and ROI

    Uses Opus model for strategic creativity.
    """

    ROLE = "cmo"

    def get_system_prompt(self) -> str:
        """Get the elite CMO system prompt."""
        return CMO_SYSTEM_PROMPT
