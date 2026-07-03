"""Smoke tests for the shared prompt fragments module."""

from __future__ import annotations

from protocols import prompt_fragments as pf


def test_all_expected_constants_present() -> None:
    for name in (
        "JSON_ONLY_INSTRUCTION",
        "JSON_ARRAY_INSTRUCTION",
        "STRUCTURED_THEN_PROSE_INSTRUCTION",
        "CIN_SCALE_SCORING",
        "ONE_TO_FIVE_SCALE",
        "CONFIDENCE_SCALE",
        "PROHIBITED_HEADER",
        "REQUIRED_HEADER",
        "DEFAULT_PROHIBITIONS",
        "SYNTHESIS_PREAMBLE",
        "ADVERSARIAL_PREAMBLE",
    ):
        val = getattr(pf, name)
        assert isinstance(val, str) and val.strip(), f"{name} is empty"


def test_no_stray_format_placeholders() -> None:
    """These fragments are meant to be concatenated, not str.format'd.

    Any lone `{name}` would blow up on format() calls in a downstream prompt.
    """
    for name in dir(pf):
        val = getattr(pf, name)
        if not isinstance(val, str) or name.startswith("_"):
            continue
        # `{` and `}` should always be balanced and used only for literal braces.
        assert val.count("{") == val.count("}"), f"{name} has unbalanced braces"


def test_agent_framing_uses_both_args() -> None:
    out = pf.agent_framing("CFO", "the chief financial officer", context="Q4 close")
    assert "CFO" in out
    assert "chief financial officer" in out
    assert "Q4 close" in out


def test_agent_framing_omits_context_block_when_empty() -> None:
    out = pf.agent_framing("CTO", "the chief technology officer")
    assert "Context:" not in out


def test_role_scoped_prefixes_role() -> None:
    out = pf.role_scoped("Analyze the pipeline.", "CFO")
    assert out.startswith("[Role: CFO]")
    assert "Analyze the pipeline." in out
