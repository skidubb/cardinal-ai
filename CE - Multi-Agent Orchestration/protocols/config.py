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

# ── Cognitive Depth Tiers (Think Fast and Slow) ──────────────────────────────
# Four-level cognitive hierarchy inspired by CogRouter (arXiv:2602.12662).
# Assign per protocol stage to cut costs 40-60% without quality loss.
#
#   L1 — Pattern Match:  Dedup, classification, extraction, format conversion
#   L2 — Rule-Based:     Scoring, ranking, filtering against explicit criteria
#   L3 — Analytical:     Evidence assessment, structured comparison, gap analysis
#   L4 — Creative/Strategic: Synthesis, ideation, adversarial reasoning, reframing
#
# Usage in orchestrators:
#   from protocols.config import COGNITIVE_TIERS
#   model = COGNITIVE_TIERS["L2"]  # Use for a scoring stage
#
COGNITIVE_TIERS = {
    "L1": ORCHESTRATION_MODEL,  # Haiku — fast pattern matching
    "L2": ORCHESTRATION_MODEL,  # Haiku — rule application
    "L3": BALANCED_MODEL,       # Sonnet — analytical reasoning
    "L4": THINKING_MODEL,       # Opus — creative/strategic synthesis
}

# Maps stage types to cognitive levels for protocol self-documentation.
# Orchestrators can use this to auto-select model tier per stage.
STAGE_COGNITIVE_MAP = {
    # L1 stages
    "dedup": "L1",
    "classify": "L1",
    "extract": "L1",
    "format": "L1",
    "parse": "L1",
    # L2 stages
    "score": "L2",
    "rank": "L2",
    "filter": "L2",
    "vote": "L2",
    "matrix": "L2",
    # L3 stages
    "assess": "L3",
    "compare": "L3",
    "analyze": "L3",
    "evaluate": "L3",
    # L4 stages
    "synthesize": "L4",
    "ideate": "L4",
    "debate": "L4",
    "reframe": "L4",
    "generate": "L4",
    "reason": "L4",
}


def model_for_stage(stage_type: str) -> str:
    """Return the appropriate model for a given stage type.

    Args:
        stage_type: One of the keys in STAGE_COGNITIVE_MAP, or a cognitive
                    level string like "L1", "L2", "L3", "L4".

    Returns:
        Model string suitable for client.messages.create().
    """
    if stage_type in COGNITIVE_TIERS:
        return COGNITIVE_TIERS[stage_type]
    level = STAGE_COGNITIVE_MAP.get(stage_type, "L4")  # Default to highest tier
    return COGNITIVE_TIERS[level]


# ── Frontier model catalog ────────────────────────────────────────────────
# LMSys Chatbot Arena leaderboard (Mar 2026).  Scores shown for reference.
# Agents can use raw LiteLLM strings directly; these are convenience aliases.
#
#  Rank  Model                          Score
#  ────  ─────                          ─────
#   1    claude-opus-4-6                 1504
#   2    claude-opus-4-6-thinking        1501
#   3    gemini-3.1-pro-preview          1500
#   4    grok-4.20-beta1                 1494
#   5    gemini-3-pro                    1486
#   6    gpt-5.2-chat-latest             1479
#   7    gemini-3-flash                  1473
#   8    grok-4.1-thinking               1473
#   9    claude-opus-4-5                 1470
#
FRONTIER_MODELS = {
    # ── Tier 1: Frontier (Arena 1490+) ─────────────────────────────────────
    "claude-opus": "claude-opus-4-6",
    "gemini-pro": "gemini/gemini-3.1-pro-preview",
    "grok": "xai/grok-4.20-beta1",

    # ── Tier 2: Near-Frontier (Arena 1470-1489) ───────────────────────────
    "gemini-3-pro": "gemini/gemini-3-pro",
    "gpt-5": "openai/gpt-5.2-chat-latest",
    "gemini-flash": "gemini/gemini-3-flash",
    "grok-thinking": "xai/grok-4.1-thinking",

    # ── Tier 3: Strong (Arena <1470 or utility) ───────────────────────────
    "claude-sonnet": "claude-sonnet-4-6",
    "claude-haiku": "claude-haiku-4-5-20251001",
    "deepseek-r1": "deepseek/deepseek-r1",
}
