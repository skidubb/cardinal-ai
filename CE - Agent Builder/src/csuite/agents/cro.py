"""
CRO Agent - Chief Revenue Officer

Revenue strategist for GTM alignment, pipeline management, and cross-functional
revenue operations. Owns the full revenue motion from first touch to renewal.
"""

from csuite.agents.base import BaseAgent
from csuite.prompts import CRO_SYSTEM_PROMPT


class CROAgent(BaseAgent):
    """Chief Revenue Officer Agent.

    Expertise areas:
    - Revenue strategy and GTM architecture
    - Pipeline management and forecasting
    - Sales methodology (MEDDPICC) and deal strategy
    - Customer success and net revenue retention
    - Revenue operations and analytics
    - Cross-functional sales/marketing/success alignment

    Uses Opus model for strategic revenue reasoning.
    """

    ROLE = "cro"

    def get_system_prompt(self) -> str:
        """Get the elite CRO system prompt."""
        return CRO_SYSTEM_PROMPT
