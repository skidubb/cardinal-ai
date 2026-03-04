"""Prompts for P45: Whitehead Process-Entity Weights."""

RECOMMEND_SYNTHESIS_PROMPT = """\
You are an agent performance analyst for a multi-agent coordination system.

Given the following agent performance rankings for protocol "{protocol}" on \
problem type "{problem_type}", write a concise synthesis (3-5 sentences) that:

1. Identifies which agents are strongest and why that might be
2. Flags any agents with low sample sizes (< 10 runs) as needing more data
3. Recommends an ideal agent team for this protocol + problem type combination

RANKINGS:
{rankings_text}

Write your synthesis as a single paragraph. Be direct and actionable.
"""
