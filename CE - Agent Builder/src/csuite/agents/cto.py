"""
CTO Agent - Chief Technology Officer

Elite technology advisor for professional services and consulting businesses.
Specializes in architecture, security, build vs. buy, and technology strategy.
"""

from csuite.agents.base import BaseAgent
from csuite.prompts import CTO_SYSTEM_PROMPT


class CTOAgent(BaseAgent):
    """Chief Technology Officer Agent.

    Expertise areas:
    - Architecture review and technical assessments
    - Build vs. buy analysis with TCO modeling
    - Security audits and compliance (SOC 2, GDPR)
    - Technology selection and evaluation
    - Technical debt quantification
    - Code review and quality standards

    Uses Opus model for technical depth.
    """

    ROLE = "cto"

    def get_system_prompt(self) -> str:
        """Get the elite CTO system prompt."""
        return CTO_SYSTEM_PROMPT
