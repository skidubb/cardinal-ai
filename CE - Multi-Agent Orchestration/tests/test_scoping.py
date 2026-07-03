"""Tests for the scoping helper — proves one-line adoption works."""

from __future__ import annotations

from protocols import scoping


def test_scoped_prompt_task_only() -> None:
    agent = {"name": "CFO", "system_prompt": "You are the CFO."}
    prompt = scoping.scoped_prompt(agent, "Score this option: X.")
    assert "You are the CFO." in prompt
    assert "Score this option: X." in prompt
    assert "shared context" not in prompt.lower()


def test_scoped_prompt_filters_by_scope() -> None:
    agent = {"name": "CFO", "context_scope": ["financial"]}
    ctx = [
        {"scope": "financial", "content": "Cash runway is 14 months."},
        {"scope": "technical", "content": "Kubernetes cluster is at 80% util."},
        {"scope": "all", "content": "Q4 board meeting is Nov 12."},
    ]
    prompt = scoping.scoped_prompt(agent, "Analyze.", shared_context=ctx)
    assert "Cash runway" in prompt
    assert "Kubernetes" not in prompt
    assert "Q4 board meeting" in prompt


def test_scoped_prompt_no_scope_sees_everything() -> None:
    agent = {"name": "CEO"}  # no context_scope
    ctx = [
        {"scope": "financial", "content": "F"},
        {"scope": "technical", "content": "T"},
    ]
    prompt = scoping.scoped_prompt(agent, "Task", shared_context=ctx)
    assert "F" in prompt
    assert "T" in prompt


def test_scoped_prompt_falls_back_to_name_when_no_system_prompt() -> None:
    agent = {"name": "CTO"}
    prompt = scoping.scoped_prompt(agent, "Do X.")
    assert "You are CTO." in prompt


def test_scoped_prompt_handles_empty_agent_gracefully() -> None:
    prompt = scoping.scoped_prompt({}, "Do X.")
    assert "Do X." in prompt


def test_scoped_prompt_all_scope_sees_all_blocks() -> None:
    agent = {"name": "COO", "context_scope": ["all"]}
    ctx = [
        {"scope": "financial", "content": "F"},
        {"scope": "technical", "content": "T"},
    ]
    prompt = scoping.scoped_prompt(agent, "Task", shared_context=ctx)
    assert "F" in prompt and "T" in prompt
