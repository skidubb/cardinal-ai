"""Stage prompts for P32: Tetlock Calibrated Forecast Protocol."""

FERMI_DECOMPOSITION_PROMPT = """\
You are a superforecaster trained in Fermi decomposition. Break the following \
forecasting question into 3-5 independently estimable sub-questions. Each \
sub-question must be MORE CONCRETE than the original — something where base \
rates or reference classes can be found.

For each sub-question, explain:
1. Why this component matters to the overall forecast
2. What data or reference class you would look for to estimate it
3. How it connects to the other sub-questions

THE FORECASTING QUESTION:
{question}
"""

BASE_RATE_PROMPT = """\
You are a superforecaster establishing outside-view base rates. For each \
sub-question below, find the most relevant reference class and historical \
frequency. You MUST cite specific reference classes (e.g., "of 47 tech IPOs \
in 2019-2023, 34% exceeded their offering price within 12 months").

For each sub-question provide:
1. The reference class you chose and why it's the best fit
2. The base rate (as a percentage or probability)
3. Sample size and time period of the reference class
4. Confidence in the reference class applicability (high/medium/low)

SUB-QUESTIONS FROM FERMI DECOMPOSITION:
{decomposition}

ORIGINAL QUESTION:
{question}
"""

INSIDE_VIEW_ADJUSTMENT_PROMPT = """\
You are a superforecaster performing inside-view adjustments. Starting from \
each base rate below, adjust incrementally based on case-specific factors.

For EACH adjustment you must specify:
- Factor name: what specific information drives this adjustment
- Direction: up or down from the base rate
- Magnitude: small (1-5 percentage points), medium (5-15pp), or large (15+pp)
- Justification: why this factor matters for THIS specific case

CRITICAL CONSTRAINT: The total cumulative adjustment from the base rate must \
NOT exceed 25 percentage points in either direction. If you have many factors \
pulling the same way, prioritize the strongest and cap the total.

After all adjustments, state the adjusted probability for each sub-question.

BASE RATES AND REFERENCE CLASSES:
{base_rates}

ORIGINAL QUESTION:
{question}
"""

EXTREMIZING_AGGREGATION_PROMPT = """\
You are a superforecaster performing the final aggregation step. You have \
adjusted probabilities for each sub-question. Now combine them into a single \
forecast using extremizing aggregation.

The extremizing formula: p_final = p^X / (p^X + (1-p)^X) where X typically \
ranges from 1.5 to 2.5. Use higher X when:
- Multiple independent lines of evidence point the same direction
- The evidence is strong and the base rates are well-established
Use lower X when:
- Evidence is mixed or contradictory
- Reference classes are uncertain or poorly fitting

Your output MUST include:
1. The combined probability from the sub-questions (explain your aggregation logic)
2. The extremizing factor X you chose and why
3. The final extremized probability
4. A 80% confidence interval (e.g., "25%-45%")
5. Key assumptions that could shift the forecast significantly

ADJUSTED PROBABILITIES AND REASONING:
{adjustments}

ORIGINAL QUESTION:
{question}
"""

SYNTHESIS_PROMPT = """\
You are a superforecaster writing the final forecast summary. Synthesize the \
entire Tetlock Calibrated Forecast process into a clear, actionable briefing.

Structure your output as:

1. **Forecast**: State the final probability and confidence interval in one sentence
2. **Decomposition Summary**: The 3-5 sub-questions and why they matter
3. **Key Base Rates**: The most important reference classes and what they tell us
4. **Critical Adjustments**: The factors that moved the needle most from the base rates
5. **Confidence Assessment**: What would make you MORE or LESS confident
6. **Decision Implications**: What should a decision-maker do with this forecast

Be direct and quantitative. Every claim should trace back to evidence from the analysis.

ORIGINAL QUESTION:
{question}

FERMI DECOMPOSITION:
{decomposition}

BASE RATES:
{base_rates}

INSIDE-VIEW ADJUSTMENTS:
{adjustments}

FINAL PROBABILITY:
{final_probability}
"""
