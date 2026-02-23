"""
Elite system prompts for C-Suite agents.

Each prompt provides deep domain expertise, industry-specific frameworks,
and actionable output patterns for consulting/agency businesses.
"""

from csuite.prompts.ceo_prompt import CEO_SYSTEM_PROMPT
from csuite.prompts.cfo_prompt import CFO_SYSTEM_PROMPT
from csuite.prompts.cmo_prompt import CMO_SYSTEM_PROMPT
from csuite.prompts.coo_prompt import COO_SYSTEM_PROMPT
from csuite.prompts.cpo_prompt import CPO_SYSTEM_PROMPT
from csuite.prompts.cro_prompt import CRO_SYSTEM_PROMPT
from csuite.prompts.cto_prompt import CTO_SYSTEM_PROMPT
from csuite.prompts.debate_prompt import (
    DEBATE_FINAL_INSTRUCTIONS,
    DEBATE_OPENING_INSTRUCTIONS,
    DEBATE_REBUTTAL_INSTRUCTIONS,
    DEBATE_SYNTHESIS_PROMPT,
    format_prior_arguments,
)

__all__ = [
    "CEO_SYSTEM_PROMPT",
    "CFO_SYSTEM_PROMPT",
    "CTO_SYSTEM_PROMPT",
    "CMO_SYSTEM_PROMPT",
    "COO_SYSTEM_PROMPT",
    "CPO_SYSTEM_PROMPT",
    "CRO_SYSTEM_PROMPT",
    "DEBATE_OPENING_INSTRUCTIONS",
    "DEBATE_REBUTTAL_INSTRUCTIONS",
    "DEBATE_FINAL_INSTRUCTIONS",
    "DEBATE_SYNTHESIS_PROMPT",
    "format_prior_arguments",
]
