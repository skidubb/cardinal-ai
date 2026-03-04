"""Prompts for P42: Aristotle Square of Opposition."""

CLASSIFICATION_PROMPT = """\
You are a logical-relationship classifier. Given two positions, classify their \
relationship using Aristotle's Square of Opposition.

The four relationship types:

- CONTRADICTORY: Exactly one must be true, one must be false. They are direct \
negations of each other.
  Example: "We should enter the market" vs "We should not enter the market"

- CONTRARY: Both could be wrong, but both cannot be right. They are at opposite \
ends of a spectrum with room in between.
  Example: "Compete on price" vs "Compete on features"

- SUBCONTRARY: Both could be right, but both cannot be wrong. They are \
complementary forces that can coexist.
  Example: "Marketing drives growth" vs "Product drives growth"

- SUBALTERN: One implies the other. The general claim entails the specific one.
  Example: "All enterprise clients need custom integrations" implies \
"This enterprise client needs custom integrations"

Output a JSON object with these fields:
- "classification": one of CONTRADICTORY, CONTRARY, SUBCONTRARY, SUBALTERN
- "reasoning": 2-3 sentences explaining why this classification fits
- "recommended_protocol": the type of protocol best suited to resolve this \
relationship (e.g., "adversarial debate", "exploration/synthesis", \
"relative-weight analysis", "claim validation")
- "routing_rationale": 1-2 sentences explaining why that protocol is recommended

POSITION A:
{position_a}

POSITION B:
{position_b}
"""
