"""Tests for image generation tools (OpenAI GPT Image 1 + Gemini 3 Pro Image Preview)."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from csuite.tools.image_gen import (
    generate_image_gemini,
    generate_image_openai,
)


@pytest.fixture(autouse=True)
def _tmp_images_dir(tmp_path, monkeypatch):
    """Redirect image output to a temp directory."""
    monkeypatch.setattr("csuite.tools.image_gen.IMAGES_DIR", tmp_path / "images")


# =============================================================================
# OpenAI Tests
# =============================================================================


class TestOpenAIGenerateImage:
    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        result = await generate_image_openai("a logo", api_key=None)
        assert "error" in result
        assert "OPENAI_API_KEY" in result["error"]

    @pytest.mark.asyncio
    async def test_success_b64(self, tmp_path):
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        fake_b64 = base64.b64encode(fake_png).decode()

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"b64_json": fake_b64}]
        }

        with patch("csuite.tools.image_gen.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await generate_image_openai("a logo", api_key="sk-test")

        assert "path" in result
        assert result["prompt"] == "a logo"
        assert "images" in result["path"]

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.text = "Rate limited"

        with patch("csuite.tools.image_gen.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await generate_image_openai("a logo", api_key="sk-test")

        assert "error" in result
        assert "429" in result["error"]

    @pytest.mark.asyncio
    async def test_timeout(self):
        with patch("csuite.tools.image_gen.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await generate_image_openai("a logo", api_key="sk-test")

        assert "error" in result
        assert "timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_size_falls_back(self):
        """Invalid size should fall back to 'auto'."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        fake_png = b"\x89PNG" + b"\x00" * 10
        mock_response.json.return_value = {
            "data": [{"b64_json": base64.b64encode(fake_png).decode()}]
        }

        with patch("csuite.tools.image_gen.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await generate_image_openai("a logo", size="9999x9999", api_key="sk-test")

        assert "path" in result


# =============================================================================
# Gemini Tests
# =============================================================================


class TestGeminiGenerateImage:
    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        result = await generate_image_gemini("a logo", api_key=None)
        assert "error" in result
        assert "GEMINI_API_KEY" in result["error"]

    @pytest.mark.asyncio
    async def test_success(self, tmp_path):
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        fake_b64 = base64.b64encode(fake_png).decode()

        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "predictions": [{"bytesBase64Encoded": fake_b64}]
        }

        with patch("csuite.tools.image_gen.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await generate_image_gemini("a logo", api_key="gemini-test")

        assert "path" in result
        assert result["prompt"] == "a logo"

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.text = "Bad request"

        with patch("csuite.tools.image_gen.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await generate_image_gemini("a logo", api_key="gemini-test")

        assert "error" in result
        assert "400" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_predictions(self):
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"predictions": []}

        with patch("csuite.tools.image_gen.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await generate_image_gemini("a logo", api_key="gemini-test")

        assert "error" in result
        assert "No predictions" in result["error"]
