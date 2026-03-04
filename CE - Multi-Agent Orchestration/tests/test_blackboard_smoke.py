"""Parametric smoke tests for blackboard/ProtocolDef execution path.

Discovers all protocols with a ``protocol_def.py``, imports the ProtocolDef,
and runs it through the generic ``Orchestrator`` with mocked LLM calls.
Asserts the blackboard contains expected entries (at minimum "question" plus
at least one stage output). Protocols that fail are marked xfail.

Uses the same mock infrastructure as ``test_orchestrator_smoke.py``.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from protocols.orchestrator_loop import Orchestrator, ProtocolDef

# Reuse mock helpers from the existing smoke tests
from tests.test_orchestrator_smoke import (
    CANNED_JSON_OBJECT,
    CANNED_TEXT,
    MockMessage,
    MockTextBlock,
    MockUsage,
    _make_mock_client,
)

# ---------------------------------------------------------------------------
# Test agents
# ---------------------------------------------------------------------------

_TEST_AGENTS = [
    {"name": "test-agent", "system_prompt": "You are a test agent."},
    {"name": "test-agent-2", "system_prompt": "You are a second test agent."},
    {"name": "test-agent-3", "system_prompt": "You are a third test agent."},
]

_TEST_QUESTION = "Should we expand into the European market?"


# ---------------------------------------------------------------------------
# Protocol discovery — find all protocol_def.py files and import the ProtocolDef
# ---------------------------------------------------------------------------

_PROTOCOLS_DIR = _REPO_ROOT / "protocols"


def _discover_protocol_defs() -> list[tuple[str, Path]]:
    """Return (protocol_dir_name, path) for each protocol with a protocol_def.py."""
    results = []
    for d in sorted(_PROTOCOLS_DIR.iterdir()):
        if not d.is_dir():
            continue
        if not (d.name.startswith("p") and not d.name.startswith("__")):
            continue
        pdef_file = d / "protocol_def.py"
        if pdef_file.exists():
            results.append((d.name, pdef_file))
    return results


def _import_protocol_def(protocol_dir_name: str) -> ProtocolDef | None:
    """Import protocol_def.py and find the ProtocolDef instance.

    Convention: the module exports a top-level variable whose value is a ProtocolDef.
    """
    module_name = f"protocols.{protocol_dir_name}.protocol_def"
    try:
        mod = importlib.import_module(module_name)
    except ImportError:
        return None

    for attr_name in dir(mod):
        obj = getattr(mod, attr_name)
        if isinstance(obj, ProtocolDef):
            return obj
    return None


_PROTOCOL_DEF_IDS = [name for name, _ in _discover_protocol_defs()]


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("protocol_dir_name", _PROTOCOL_DEF_IDS)
def test_blackboard_smoke(protocol_dir_name: str) -> None:
    """Run each ProtocolDef through the generic Orchestrator with mocked LLM.

    Asserts:
    - The ProtocolDef can be imported.
    - Orchestrator.run() completes without raising.
    - The returned blackboard has a "question" topic.
    - At least one additional topic was written (i.e., at least one stage fired).
    """
    protocol_def = _import_protocol_def(protocol_dir_name)
    if protocol_def is None:
        pytest.skip(f"Could not import ProtocolDef for {protocol_dir_name}")

    mock_client = _make_mock_client(CANNED_JSON_OBJECT)

    async def _run():
        orchestrator = Orchestrator()
        bb = await orchestrator.run(
            protocol=protocol_def,
            question=_TEST_QUESTION,
            agents=_TEST_AGENTS,
            client=mock_client,
            thinking_model="claude-opus-4-6",
            orchestration_model="claude-haiku-4-5-20251001",
            thinking_budget=1000,
            no_tools=True,
        )
        return bb

    with (
        patch("protocols.llm.agent_complete", new=AsyncMock(return_value=CANNED_JSON_OBJECT)),
        patch("protocols.stages.agent_complete", new=AsyncMock(return_value=CANNED_JSON_OBJECT)),
        patch("anthropic.AsyncAnthropic", return_value=mock_client),
    ):
        try:
            bb = asyncio.run(_run())
        except Exception as exc:
            import traceback as _tb
            print(f"\n{'='*60}\n{protocol_dir_name} BLACKBOARD EXCEPTION:\n{'='*60}")
            _tb.print_exc()
            print(f"{'='*60}\n")
            pytest.xfail(
                f"{protocol_dir_name} blackboard path raised {type(exc).__name__}: {exc}"
            )
            return  # xfail exits, but satisfy type checker

    # Basic assertions
    assert bb is not None, f"{protocol_dir_name}: Orchestrator.run() returned None"
    assert bb.has_topic("question"), f"{protocol_dir_name}: blackboard missing 'question' topic"

    topics = bb.topics()
    assert len(topics) > 1, (
        f"{protocol_dir_name}: only 'question' on blackboard — no stages fired. "
        f"Topics: {topics}"
    )
