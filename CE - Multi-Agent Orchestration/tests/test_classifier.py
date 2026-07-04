"""Tests for question classifier — unit tests only (no API calls)."""

import pytest

from protocols.learning.classifier import (
    QUESTION_CATEGORIES,
    _parse_categories,
)


class TestParseCategories:
    def test_valid_json_single(self):
        assert _parse_categories('["innovation"]') == ["innovation"]

    def test_valid_json_multiple(self):
        assert _parse_categories('["pricing", "financial"]') == ["pricing", "financial"]

    def test_markdown_fenced(self):
        assert _parse_categories('```json\n["risk"]\n```') == ["risk"]

    def test_invalid_category_filtered(self):
        assert _parse_categories('["innovation", "bogus"]') == ["innovation"]

    def test_all_invalid_returns_unclassified(self):
        assert _parse_categories('["bogus", "fake"]') == ["unclassified"]

    def test_malformed_json_returns_unclassified(self):
        assert _parse_categories("not json at all") == ["unclassified"]

    def test_empty_string_returns_unclassified(self):
        assert _parse_categories("") == ["unclassified"]

    def test_empty_array_returns_unclassified(self):
        assert _parse_categories("[]") == ["unclassified"]


def test_question_categories_is_nonempty_list():
    assert len(QUESTION_CATEGORIES) >= 5
    assert all(isinstance(c, str) for c in QUESTION_CATEGORIES)
