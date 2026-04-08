"""CE AGENTS 2.0 — Coordination Learning System.

A new capability layer on top of the existing protocol library.
All features are gated behind COORDINATION_LAYER_ENABLED.

The existing 53 protocols and 56 agents remain fully operational.
This layer adds: coordination primitives, open agent conversation,
adaptive routing, interaction patterns, and composition evolution.
"""

from __future__ import annotations

import os


def is_enabled() -> bool:
    """Check if the coordination layer is active."""
    return os.getenv("COORDINATION_LAYER_ENABLED", "false").lower() in ("true", "1", "yes")
