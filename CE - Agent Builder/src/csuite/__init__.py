"""
C-Suite: Elite AI Advisory Team

A personal C-suite of elite AI advisors (CFO, CTO, CMO, COO) for consulting/agency businesses.
Built with Claude Agent SDK for deep domain expertise and actionable recommendations.
"""

__version__ = "0.1.0"
__author__ = "Scott Ewalt"

from csuite.agents.cfo import CFOAgent
from csuite.agents.cmo import CMOAgent
from csuite.agents.coo import COOAgent
from csuite.agents.cto import CTOAgent

__all__ = [
    "CFOAgent",
    "CTOAgent",
    "CMOAgent",
    "COOAgent",
]
