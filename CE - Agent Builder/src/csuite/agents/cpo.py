"""
CPO Agent - Chief Product Officer

Product strategist for user needs, roadmap priorities, and product-market fit.
Specializes in service design, prioritization, and competitive differentiation.
"""

from csuite.agents.base import BaseAgent
from csuite.prompts import CPO_SYSTEM_PROMPT


class CPOAgent(BaseAgent):
    """Chief Product Officer Agent.

    Expertise areas:
    - Service as product thinking
    - User/client problem discovery
    - Prioritization and roadmap
    - Product-market fit assessment
    - Service design and packaging
    - Deliverable design and quality

    Uses Opus model for complex product strategy reasoning.
    """

    ROLE = "cpo"

    def get_system_prompt(self) -> str:
        """Get the elite CPO system prompt."""
        return CPO_SYSTEM_PROMPT
