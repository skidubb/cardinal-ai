"""
COO Agent - Chief Operating Officer

Elite operations advisor for professional services businesses.
Specializes in resource planning, delivery excellence, and process optimization.
"""

from csuite.agents.base import BaseAgent
from csuite.prompts import COO_SYSTEM_PROMPT


class COOAgent(BaseAgent):
    """Chief Operating Officer Agent.

    Expertise areas:
    - Resource allocation and capacity planning
    - Project delivery excellence
    - Process optimization
    - Knowledge management
    - Quality assurance
    - Operational efficiency

    Uses Opus model for operational complexity.
    """

    ROLE = "coo"

    def get_system_prompt(self) -> str:
        """Get the elite COO system prompt."""
        return COO_SYSTEM_PROMPT
