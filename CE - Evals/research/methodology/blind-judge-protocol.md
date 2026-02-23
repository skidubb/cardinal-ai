# Blind Judge Protocol

## Overview

This evaluation framework uses an LLM-as-a-Judge approach with blind scoring to compare outputs from different multi-agent coordination protocols.

## Procedure

1. **Candidate Generation**: Each selected protocol runs on the same question independently
2. **Anonymization**: Outputs are stripped of protocol-identifying metadata and assigned random labels (Response A, B, C...)
3. **Randomization**: Presentation order is shuffled each evaluation to prevent position bias
4. **Blind Scoring**: A judge model scores each response on rubric dimensions (1-5 scale) without knowing which protocol produced it
5. **Forced Ranking**: The judge must rank all responses from best to worst
6. **De-anonymization**: Labels are mapped back to protocol names for reporting

## Bias Mitigations

- **Anonymization** prevents the judge from favoring known protocols
- **Metadata stripping** removes protocol names, round counts, and structural markers
- **Random ordering** prevents position bias (first/last preference)
- **Rubric-driven scoring** ensures consistent evaluation criteria across runs
- **Forced ranking** prevents ties and requires the judge to commit to relative quality

## Rubrics

Rubrics are defined in YAML and contain:
- Named dimensions with descriptions
- A judge system prompt template
- Configurable scale (default 1-5)

Multiple rubrics can be used on the same outputs to evaluate different quality aspects.

## Limitations

- Single-judge evaluations may have model-specific biases
- Short outputs may score differently than long outputs regardless of quality
- The judge model's own capabilities limit its ability to evaluate certain dimensions
- Cost/duration tracking captures eval-harness overhead, not just protocol API calls
