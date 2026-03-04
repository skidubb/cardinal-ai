"""Tool execution dispatcher for agent tool calls.

Routes tool_use blocks from Claude responses to actual tool handlers.
Handlers are imported lazily from the CE Agent Builder's tool registry.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Add CE Agent Builder to sys.path for tool handler imports
_AGENT_BUILDER_SRC = Path(__file__).resolve().parent.parent.parent / "CE - Agent Builder" / "src"
if str(_AGENT_BUILDER_SRC) not in sys.path:
    sys.path.insert(0, str(_AGENT_BUILDER_SRC))

# Maximum tool result length
MAX_RESULT_LENGTH = 50_000

# Maximum iterations for the agentic tool loop
MAX_TOOL_ITERATIONS = 15


class _SettingsProxy:
    """Minimal settings proxy that reads from environment variables.

    Provides the interface expected by CE Agent Builder tool handlers
    without requiring their full pydantic Settings class.
    """
    def __init__(self):
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        self.notion_api_key = os.getenv("NOTION_API_KEY")
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index_host = os.getenv("PINECONE_INDEX_HOST")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.reports_dir = Path(os.getenv("REPORTS_DIR", "./reports"))
        self.reports_dir.mkdir(parents=True, exist_ok=True)


_settings: _SettingsProxy | None = None


def _get_settings() -> _SettingsProxy:
    global _settings
    if _settings is None:
        _settings = _SettingsProxy()
    return _settings


async def execute_tool(tool_name: str, tool_input: dict) -> tuple[str, float]:
    """Execute a tool and return (result_json, elapsed_ms).

    Never raises — errors are returned as {"error": "..."} strings.
    """
    start = time.monotonic()
    try:
        # Try to import from CE Agent Builder's tool registry
        from csuite.tools.registry import TOOL_HANDLERS, sanitize_tool_output

        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            elapsed_ms = (time.monotonic() - start) * 1000
            return json.dumps({"error": f"Unknown tool: {tool_name}"}), elapsed_ms

        settings = _get_settings()
        result = await handler(tool_input, settings)
        result = sanitize_tool_output(result)
        elapsed_ms = (time.monotonic() - start) * 1000
        return result, elapsed_ms

    except ImportError:
        logger.warning("CE Agent Builder tools not available (import failed)")
        elapsed_ms = (time.monotonic() - start) * 1000
        return json.dumps({
            "error": f"Tool '{tool_name}' unavailable — CE Agent Builder not installed"
        }), elapsed_ms
    except Exception as e:
        logger.warning("Tool %s failed: %s", tool_name, e, exc_info=True)
        elapsed_ms = (time.monotonic() - start) * 1000
        return json.dumps({"error": f"Tool '{tool_name}' failed: {str(e)[:200]}"}), elapsed_ms
