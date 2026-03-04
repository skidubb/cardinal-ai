"""Tests for protocols/llm.py — _no_tools ContextVar behavior."""

from protocols.llm import set_no_tools, get_no_tools, _no_tools


def test_no_tools_default_is_false():
    # Reset to default
    _no_tools.set(False)
    assert get_no_tools() is False


def test_set_no_tools_true():
    set_no_tools(True)
    assert get_no_tools() is True
    # Clean up
    set_no_tools(False)


def test_set_no_tools_false():
    set_no_tools(True)
    set_no_tools(False)
    assert get_no_tools() is False
