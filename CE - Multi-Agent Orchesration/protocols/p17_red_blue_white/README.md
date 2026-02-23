# P17: Red/Blue/White Team

Adversarial stress-testing: Red attacks a plan, Blue defends it, White adjudicates.

| Attribute | Value |
|-----------|-------|
| **Category** | Intelligence Analysis |
| **Problem Type** | Adversarial Stress-Testing |
| **Tool Level** | T0 (no tools) |
| **Agents** | N red (attackers) + M blue (defenders) + 1 white (arbiter) |

## How It Works

1. **Phase 1 — Red Team Attack**: Each Red agent independently identifies vulnerabilities, failure modes, blind spots, and risks in the plan (parallel, Opus with extended thinking). Produces structured attack reports with severity ratings.
2. **Phase 2 — Blue Team Defense**: Each Blue agent receives ALL attacks and independently produces defenses: mitigations, counterarguments, evidence, and plan modifications (parallel, Opus with extended thinking).
3. **Phase 3 — White Team Adjudication**: White agent receives all attacks and all defenses. For each vulnerability, evaluates whether the defense is adequate. Categorizes as Resolved, Partially Resolved, or Open. Produces a risk register (Opus with extended thinking).
4. **Phase 4 — Final Assessment**: White agent synthesizes into final report: resolved risks, open risks, plan strength score (1-10), and actionable recommendations (Opus).

## Usage

```bash
python -m protocols.p17_red_blue_white.run \
  --question "Should we enter the enterprise market?" \
  --plan "Launch an enterprise tier with dedicated support, SOC2 compliance, and custom integrations over the next 6 months" \
  --red cmo cfo \
  --blue cto coo \
  --white ceo

# JSON output
python -m protocols.p17_red_blue_white.run \
  -q "Should we pivot to AI-first?" \
  -p "Rebuild the core product around LLM capabilities, sunset legacy features" \
  -r cfo cro \
  -b cto cpo \
  -w ceo \
  --json
```

## Output

- Red Team attack reports with categorized vulnerabilities and severity ratings
- Blue Team defense reports with mitigations, evidence, and residual risk
- White Team adjudication: Resolved / Partially Resolved / Open for each vulnerability
- Plan strength score (1-10) with reasoning
- Prioritized recommendations for plan improvement

## Model Usage

| Phase | Model | Calls |
|-------|-------|-------|
| Red Team Attack | Opus (thinking) | N red agents |
| Blue Team Defense | Opus (thinking) | M blue agents |
| White Adjudication | Opus (thinking) | 1 |
| Final Assessment | Opus | 1 |
