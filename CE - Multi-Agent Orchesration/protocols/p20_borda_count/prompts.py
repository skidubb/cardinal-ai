"""Prompts for the P20 Borda Count Voting protocol."""

RANKING_PROMPT = """\
You are participating in a Borda Count voting exercise to rank a set of options.

Question:
{question}

Your role: {agent_name}
{system_prompt}

Options to rank (in no particular order):
{options_block}

Rank ALL {num_options} options from best (rank 1) to worst (rank {num_options}) based on your expertise and perspective. Every option must appear exactly once. Provide reasoning for each ranking position.

Respond in JSON:
{{
  "rankings": [
    {{"rank": 1, "option": "the best option (exact text)", "reasoning": "why this is your top choice"}},
    {{"rank": 2, "option": "second best option", "reasoning": "why this is second"}},
    {{"rank": {num_options}, "option": "last option", "reasoning": "why this is last"}}
  ]
}}
"""

TIEBREAK_PROMPT = """\
You are resolving a tie in a Borda Count voting exercise.

Question:
{question}

The following options are tied with {tied_score} Borda points each:
{tied_options_block}

Here is how each agent ranked these tied options:
{head_to_head_block}

Using Condorcet head-to-head comparison, determine the final ordering among the tied options. For each pair of tied options, count how many agents ranked A above B versus B above A. The option that wins more head-to-head matchups should rank higher.

Respond in JSON:
{{
  "tiebreak_ranking": [
    {{"option": "winner of tiebreak", "condorcet_wins": 3, "reasoning": "won N of M head-to-head comparisons"}},
    {{"option": "second place", "condorcet_wins": 1, "reasoning": "explanation"}}
  ],
  "analysis": "brief explanation of the head-to-head results"
}}
"""

FINAL_REPORT_PROMPT = """\
You are the lead analyst producing the final report for a Borda Count voting exercise.

Question:
{question}

Options evaluated:
{options_block}

## Final Ranking (by Borda score):
{ranking_block}

## Individual Agent Ballots:
{ballots_block}

## Tiebreak Applied: {tiebreak_applied}
{tiebreak_details}

Produce a comprehensive final report that includes:
1. **Executive Summary**: The winning option and why the group converged on it
2. **Reasoning Clusters**: For each option, group the similar reasoning themes across agents (what common arguments appeared)
3. **Consensus Analysis**: How much agreement was there? Were agents aligned or split? Provide a consensus score from 0.0 (complete disagreement) to 1.0 (unanimous)
4. **Margin Analysis**: How decisive was the winner? Could small changes in voting shift the outcome?
5. **Dissenting Views**: Notable minority positions worth considering

Respond in JSON:
{{
  "executive_summary": "paragraph summarizing the result",
  "reasoning_clusters": {{
    "Option A": ["common reason 1", "common reason 2"],
    "Option B": ["common reason 1"]
  }},
  "consensus_score": 0.75,
  "consensus_analysis": "paragraph on agreement patterns",
  "margin_analysis": "paragraph on how decisive the result was",
  "dissenting_views": ["notable minority view 1", "notable minority view 2"],
  "report": "full narrative report suitable for a decision-maker"
}}
"""
