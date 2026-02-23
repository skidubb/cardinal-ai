"""Token cost estimation using multi-provider pricing."""

from __future__ import annotations

# Feb 2026 pricing per million tokens: (input, output)
PRICING: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-opus-4-6": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (0.80, 4.0),
    # OpenAI
    "gpt-5.2": (2.50, 10.0),
    "gpt-4o": (2.50, 10.0),
    "o3-mini": (1.10, 4.40),
    # Google
    "gemini-3.1-pro-preview": (1.25, 5.0),
    "gemini-2.5-pro": (1.25, 5.0),
}


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "claude-opus-4-6",
) -> float:
    """Estimate cost in USD."""
    if model not in PRICING:
        # Try prefix match
        for key in PRICING:
            if model.startswith(key.rsplit("-", 1)[0]):
                inp, out = PRICING[key]
                break
        else:
            inp, out = (0.0, 0.0)  # Unknown model — don't guess
    else:
        inp, out = PRICING[model]
    return (input_tokens * inp + output_tokens * out) / 1_000_000
