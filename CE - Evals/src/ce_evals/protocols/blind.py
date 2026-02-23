"""Blind protocol — anonymization and metadata stripping."""

from __future__ import annotations

import random
import re


def anonymize(
    responses: dict[str, str],
) -> tuple[list[tuple[str, str]], dict[str, str]]:
    """Shuffle responses and assign anonymous labels.

    Returns:
        (labeled_parts, label_to_candidate) where labeled_parts is
        [(label, text), ...] in randomized order.
    """
    names = list(responses.keys())
    random.shuffle(names)
    labels = [f"Response {chr(65 + i)}" for i in range(len(names))]
    label_to_candidate = dict(zip(labels, names))
    labeled_parts = [(label, responses[name]) for label, name in zip(labels, names)]
    return labeled_parts, label_to_candidate


def strip_metadata(text: str, patterns: list[str] | None = None) -> str:
    """Remove identifying metadata from output text."""
    # Default patterns that might reveal which protocol produced the output
    default_patterns = [
        # Protocol names that could reveal identity
        r"(?i)(debate|negotiation|synthesis|single agent|multi-agent|delphi|"
        r"ach|triz|vickrey|round-robin|causal loop|system archetype|"
        r"borda\s*count|cynefin|crazy eights|affinity\s*mapping|"
        r"troika|ecocycle|min\s*specs|1-2-4-all|what[\s-]*so[\s-]*what|"
        r"hsr|dad|red\s*team|blue\s*team|white\s*team|"
        r"wicked\s*question|auction|interests?\s*negotiation|"
        r"structured\s*debate|round[\s-]*robin)"
        r"\s*(mode|approach|protocol|analysis|framework|method|process)?",
        r"(?i)protocol:\s*\S+",
        r"Debate ID:\s*\S+",
        r"Constraint[s]?:\s*\d+",
        r"Round \d+ of \d+",
        # Phase/step markers from specific protocols
        r"(?i)(ACH|Analysis of Competing Hypotheses)\s*:?",
        r"(?i)Red[\s-]*Blue[\s-]*White\s*(team|cell|exercise)?",
        r"(?i)Vickrey\s*(auction|mechanism)?",
        r"(?i)Borda\s*(count|ranking|vote)?",
        r"(?i)TRIZ\s*(contradiction|principle)?",
    ]
    all_patterns = default_patterns + (patterns or [])
    for pat in all_patterns:
        text = re.sub(pat, "", text)
    return text.strip()
