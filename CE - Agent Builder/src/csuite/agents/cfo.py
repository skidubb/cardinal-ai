"""
CFO Agent - Chief Financial Officer

Elite financial advisor for professional services and consulting businesses.
Specializes in project economics, cash flow, pricing strategy, and financial KPIs.
"""

from csuite.agents.base import BaseAgent
from csuite.prompts import CFO_SYSTEM_PROMPT


class CFOAgent(BaseAgent):
    """Chief Financial Officer Agent.

    Expertise areas:
    - Project profitability analysis
    - Cash flow forecasting
    - Pricing strategy (T&M, fixed-fee, retainers)
    - Financial KPIs for consulting/agencies
    - Working capital management
    - Revenue forecasting

    Uses Opus model for complex financial reasoning.
    """

    ROLE = "cfo"

    def get_system_prompt(self) -> str:
        """Get the elite CFO system prompt."""
        return CFO_SYSTEM_PROMPT
