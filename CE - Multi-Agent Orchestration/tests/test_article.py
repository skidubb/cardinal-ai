"""Tests for protocols/article.py — ArticleWriter validation and prompt assembly."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from protocols.article import (
    Article,
    ArticleWriter,
    _clip,
    _format_excerpts,
    _validate_article,
)


# ── _clip ─────────────────────────────────────────────────────────────────────


def test_clip_short_text_unchanged():
    text = "short text"
    assert _clip(text, 100) == text


def test_clip_long_text_keeps_head_and_tail_with_marker():
    text = "a" * 1000
    clipped = _clip(text, 100)
    assert "[…]" in clipped
    assert clipped.startswith("a" * 10)
    assert clipped.endswith("a" * 10)
    assert len(clipped) < len(text)


# ── _format_excerpts ──────────────────────────────────────────────────────────


def test_format_excerpts_attributes_by_name():
    outputs = [{"name": "CFO", "text": "The payback is 8 months."}]
    result = _format_excerpts(outputs)
    assert "=== CFO ===" in result
    assert "The payback is 8 months." in result


def test_format_excerpts_falls_back_to_agent_key():
    outputs = [{"agent_key": "cto", "text": "Some analysis."}]
    result = _format_excerpts(outputs)
    assert "=== cto ===" in result


def test_format_excerpts_empty_list_returns_placeholder():
    assert _format_excerpts([]) == "(no individual contributions recorded)"


def test_format_excerpts_skips_blank_text():
    outputs = [{"name": "CFO", "text": "   "}, {"name": "CTO", "text": "real content"}]
    result = _format_excerpts(outputs)
    assert "CFO" not in result
    assert "real content" in result


def test_format_excerpts_respects_per_agent_cap():
    from protocols.article import MAX_AGENT_EXCERPT_CHARS

    outputs = [{"name": "CFO", "text": "x" * (MAX_AGENT_EXCERPT_CHARS * 2)}]
    result = _format_excerpts(outputs)
    # clipped excerpt plus the "=== CFO ===\n" header
    assert len(result) < MAX_AGENT_EXCERPT_CHARS * 2


def test_format_excerpts_respects_total_cap():

    outputs = [{"name": f"Agent{i}", "text": "x" * 2_000} for i in range(50)]
    result = _format_excerpts(outputs)
    # budget runs out well before all 50 agents are included
    assert result.count("===") < 100  # 50 agents * 2 markers each = 100 if all included


# ── _validate_article ──────────────────────────────────────────────────────────


def _full_payload(**overrides):
    payload = {
        "headline": "Board Approves Expansion",
        "deck": "A closely contested vote settles months of debate.",
        "lede": "The room went quiet.\n\nThen the CFO spoke.",
        "sections": [
            {
                "heading": "The Case For",
                "body_markdown": "The CFO argued the numbers work.",
                "pull_quote": {"text": "The math is undeniable.", "attribution": "CFO"},
            }
        ],
        "tensions": [
            {
                "framing": "Timing of the rollout",
                "sides": ["CFO wants Q3", "COO wants Q4"],
            }
        ],
        "what_next": "The board reconvenes in October.",
    }
    payload.update(overrides)
    return payload


def test_validate_article_full_valid_payload():
    article = _validate_article(
        _full_payload(),
        protocol_key="p04_multi_round_debate",
        agent_names=["CFO", "COO"],
    )
    assert isinstance(article, Article)
    assert article.headline == "Board Approves Expansion"
    assert len(article.sections) == 1
    assert article.sections[0]["pull_quote"]["attribution"] == "CFO"
    assert len(article.tensions) == 1
    assert article.tensions[0]["framing"] == "Timing of the rollout"


def test_validate_article_sections_without_body_dropped():
    payload = _full_payload(
        sections=[
            {"heading": "Empty", "body_markdown": ""},
            {"heading": "Real", "body_markdown": "Has content."},
        ]
    )
    article = _validate_article(payload, protocol_key="p04", agent_names=[])
    assert len(article.sections) == 1
    assert article.sections[0]["heading"] == "Real"


def test_validate_article_pull_quote_without_text_becomes_none():
    payload = _full_payload(
        sections=[
            {
                "heading": "Real",
                "body_markdown": "Has content.",
                "pull_quote": {"attribution": "CFO"},
            }
        ]
    )
    article = _validate_article(payload, protocol_key="p04", agent_names=[])
    assert article.sections[0]["pull_quote"] is None


def test_validate_article_byline_carries_protocol_agents_generated_at():
    article = _validate_article(
        _full_payload(), protocol_key="p16_ach", agent_names=["CEO", "CFO"]
    )
    assert article.byline["protocol"] == "p16_ach"
    assert article.byline["agents"] == ["CEO", "CFO"]
    assert "generated_at" in article.byline


def test_article_is_empty_true_for_empty_payload():
    article = _validate_article({}, protocol_key="p04", agent_names=[])
    assert article.is_empty


def test_article_is_empty_false_for_valid_payload():
    article = _validate_article(
        _full_payload(), protocol_key="p04", agent_names=["CFO"]
    )
    assert not article.is_empty


def test_validate_article_tensions_without_framing_dropped():
    payload = _full_payload(tensions=[{"sides": ["A", "B"]}, {"framing": "Real one"}])
    article = _validate_article(payload, protocol_key="p04", agent_names=[])
    assert len(article.tensions) == 1
    assert article.tensions[0]["framing"] == "Real one"


# ── ArticleWriter.write ────────────────────────────────────────────────────────


VALID_ARTICLE_JSON = """{
  "headline": "Board Approves Expansion",
  "deck": "A closely contested vote settles months of debate.",
  "lede": "The room went quiet.",
  "sections": [
    {"heading": "The Case", "body_markdown": "The numbers work.", "pull_quote": null}
  ],
  "tensions": [],
  "what_next": "Reconvene in October."
}"""


@pytest.mark.asyncio
async def test_article_writer_write_populates_article():
    writer = ArticleWriter(client=object())
    with patch(
        "protocols.article.agent_complete",
        new=AsyncMock(return_value=VALID_ARTICLE_JSON),
    ):
        article = await writer.write(
            question="Should we expand?",
            synthesis="The team recommends expansion.",
            protocol_key="p04_multi_round_debate",
            agent_outputs=[{"name": "CFO", "text": "Numbers work."}],
        )
    assert article.headline == "Board Approves Expansion"
    assert article.byline["agents"] == ["CFO"]


@pytest.mark.asyncio
async def test_article_writer_write_no_judge_verdict_uses_placeholder_in_prompt():
    writer = ArticleWriter(client=object())
    mock_complete = AsyncMock(return_value=VALID_ARTICLE_JSON)
    with patch("protocols.article.agent_complete", new=mock_complete):
        await writer.write(
            question="Should we expand?",
            synthesis="The team recommends expansion.",
            protocol_key="p04_multi_round_debate",
            agent_outputs=[{"name": "CFO", "text": "Numbers work."}],
            judge_verdict=None,
        )
    _, kwargs = mock_complete.call_args
    prompt = kwargs["messages"][0]["content"]
    assert "(no independent review available)" in prompt


@pytest.mark.asyncio
async def test_article_writer_write_agent_names_flow_into_prompt_and_byline():
    writer = ArticleWriter(client=object())
    mock_complete = AsyncMock(return_value=VALID_ARTICLE_JSON)
    with patch("protocols.article.agent_complete", new=mock_complete):
        article = await writer.write(
            question="Should we expand?",
            synthesis="The team recommends expansion.",
            protocol_key="p04_multi_round_debate",
            agent_outputs=[{"name": "CFO", "text": "x"}, {"name": "COO", "text": "y"}],
        )
    _, kwargs = mock_complete.call_args
    prompt = kwargs["messages"][0]["content"]
    assert "CFO, COO" in prompt
    assert article.byline["agents"] == ["CFO", "COO"]
