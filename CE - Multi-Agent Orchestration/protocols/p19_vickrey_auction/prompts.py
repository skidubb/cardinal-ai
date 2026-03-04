"""Prompts for the P19 Vickrey Auction protocol."""

SEALED_BID_PROMPT = """\
You are participating in a sealed-bid evaluation exercise. You must independently evaluate all options and select the one you believe is strongest.

Question under evaluation:
{question}

Your role: {agent_name}
{system_prompt}

Options to evaluate:
{options_block}

Evaluate each option through the lens of your role. Then select your TOP choice and assign a confidence score from 0-100 indicating how strongly you believe this is the best option. Be honest and calibrated — do not inflate your confidence.

IMPORTANT: This is a sealed bid. You cannot see other evaluators' choices. Bid your true preference.

Respond in JSON:
{{
  "selected_option": "the exact option text you are selecting",
  "confidence": 85,
  "reasoning": "2-3 sentences explaining why this option is strongest from your perspective"
}}
"""

CALIBRATED_JUSTIFICATION_PROMPT = """\
You are the winning bidder in a Vickrey (second-price sealed-bid) auction for option selection.

Question under evaluation:
{question}

Your role: {agent_name}
{system_prompt}

You selected: {winning_option}
Your original confidence: {original_confidence}/100

However, per Vickrey auction rules, your bid is calibrated to the SECOND-HIGHEST confidence level: {second_price_confidence}/100.

All bids have been revealed:
{bids_block}

Now provide a calibrated justification for your winning option. Your justification should reflect the second-price confidence level ({second_price_confidence}/100), not your original confidence ({original_confidence}/100). This means you should:
- Acknowledge limitations and uncertainties proportional to the gap between your confidence and the second price
- Be more measured in your claims if the second price is significantly lower
- Integrate insights from other agents' reasoning where relevant

Respond in JSON:
{{
  "calibrated_justification": "A thorough but appropriately hedged justification at confidence level {second_price_confidence}/100",
  "key_tradeoffs": ["tradeoff 1", "tradeoff 2"],
  "risks_acknowledged": ["risk 1", "risk 2"]
}}
"""

FINAL_ASSESSMENT_PROMPT = """\
You are synthesizing the results of a Vickrey auction option-selection exercise.

Question: {question}

Options evaluated: {options_list}

All sealed bids:
{bids_block}

Winning agent: {winner}
Winning option: {winning_option}
Original confidence: {original_confidence}/100
Second-price (calibrated) confidence: {second_price_confidence}/100

Calibrated justification from winner:
{calibrated_justification}

Bid distribution by option:
{distribution_block}

Produce a final synthesis that includes:
1. The winning recommendation and calibrated confidence
2. Consensus analysis: did agents converge on the same option or diverge across many?
3. Distribution insights: which options attracted bids and at what confidence levels
4. A consensus score from 0.0 to 1.0 (1.0 = all agents chose the same option, 0.0 = every agent chose a different option)

Respond in JSON:
{{
  "summary": "2-3 sentence executive summary of the recommendation",
  "winning_option": "the selected option",
  "calibrated_confidence": {second_price_confidence},
  "consensus_analysis": "paragraph analyzing agreement/disagreement patterns",
  "consensus_score": 0.75,
  "distribution_insights": "paragraph on how bids were distributed",
  "dissenting_perspectives": ["notable dissent 1", "notable dissent 2"]
}}
"""
