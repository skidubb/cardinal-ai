"""Tests for file export tools (write_deliverable, export_pdf)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from csuite.tools.registry import _handle_export_pdf, _handle_write_deliverable


@pytest.fixture
def mock_settings(tmp_path):
    settings = MagicMock()
    settings.reports_dir = tmp_path / "reports"
    settings.reports_dir.mkdir()
    return settings


@pytest.mark.asyncio
async def test_write_deliverable_success(mock_settings):
    result = json.loads(
        await _handle_write_deliverable(
            {"filename": "CMO-D6-LinkedIn-Post.md", "content": "# Hello\n\nContent here."},
            mock_settings,
        )
    )
    assert "path" in result
    assert result["bytes"] > 0
    assert Path(result["path"]).exists()
    assert "warning" not in result


@pytest.mark.asyncio
async def test_write_deliverable_naming_warning(mock_settings):
    result = json.loads(
        await _handle_write_deliverable(
            {"filename": "random-file.md", "content": "content"},
            mock_settings,
        )
    )
    assert "warning" in result
    assert "naming convention" in result["warning"]
    assert Path(result["path"]).exists()


@pytest.mark.asyncio
async def test_write_deliverable_custom_directory(mock_settings):
    result = json.loads(
        await _handle_write_deliverable(
            {"filename": "CEO-D1-Test.md", "content": "test", "directory": "sprint-2"},
            mock_settings,
        )
    )
    assert "sprint-2" in result["path"]
    assert Path(result["path"]).exists()


@pytest.mark.asyncio
async def test_write_deliverable_creates_directories(mock_settings):
    result = json.loads(
        await _handle_write_deliverable(
            {"filename": "CFO-D3-Pricing.md", "content": "pricing", "directory": "deep/nested/dir"},
            mock_settings,
        )
    )
    assert Path(result["path"]).exists()


@pytest.mark.asyncio
async def test_export_pdf_file_not_found(mock_settings):
    result = json.loads(
        await _handle_export_pdf({"markdown_path": "/nonexistent/file.md"}, mock_settings)
    )
    assert "error" in result
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_export_pdf_success(mock_settings, tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text("# Test\n\nContent")

    with patch("csuite.tools.report_generator.ProspectReportGenerator") as mock_gen_cls:
        mock_gen = MagicMock()
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")
        mock_gen.save_pdf.return_value = pdf_path
        mock_gen_cls.return_value = mock_gen

        result = json.loads(
            await _handle_export_pdf({"markdown_path": str(md_file)}, mock_settings)
        )

    assert "path" in result
    assert result["path"].endswith(".pdf")


@pytest.mark.asyncio
async def test_export_pdf_weasyprint_missing(mock_settings, tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text("# Test")

    with patch("csuite.tools.report_generator.ProspectReportGenerator") as mock_gen_cls:
        mock_gen = MagicMock()
        mock_gen.save_pdf.return_value = None
        mock_gen_cls.return_value = mock_gen

        result = json.loads(
            await _handle_export_pdf({"markdown_path": str(md_file)}, mock_settings)
        )

    assert "error" in result
    assert "weasyprint" in result["error"].lower()
