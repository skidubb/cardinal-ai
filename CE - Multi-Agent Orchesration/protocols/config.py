"""Centralized model configuration for all coordination protocols.

Single source of truth for model strings. Change one line here instead of
find-and-replace across 48 protocols.

Precedence: env var > CLI arg > per-agent "model" field > these defaults.
"""

from __future__ import annotations

import os

# ── Anthropic defaults (used by all protocols) ──────────────────────────────
THINKING_MODEL = os.getenv("THINKING_MODEL", "claude-opus-4-6")
ORCHESTRATION_MODEL = os.getenv("ORCHESTRATION_MODEL", "claude-haiku-4-5-20251001")
BALANCED_MODEL = os.getenv("BALANCED_MODEL", "claude-sonnet-4-6")

# ── Frontier model catalog (for per-agent assignment in agents.py) ──────────
# Convenience constants — agents can also use raw LiteLLM strings directly.
FRONTIER_MODELS = {
    # Anthropic
    "claude-opus": "claude-opus-4-6",
    "claude-sonnet": "claude-sonnet-4-6",
    "claude-haiku": "claude-haiku-4-5-20251001",
    # OpenAI
    "gpt-5-pro": "gpt-5.2-pro",
    "gpt-5": "gpt-5.2",
    # Google
    "gemini-pro": "gemini/gemini-3-pro-preview",
    "gemini-flash": "gemini/gemini-2.5-flash-preview-09-2025",
    # xAI
    "grok": "xai/grok-4",
    "grok-fast": "xai/grok-4-1-fast-reasoning",
    # DeepSeek
    "deepseek-r1": "deepseek/deepseek-r1",
}
