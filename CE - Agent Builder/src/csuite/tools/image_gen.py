"""
Image Generation Tools for C-Suite Agents (CMO + CPO).

Provides async wrappers for OpenAI GPT Image 1 and Google Gemini Imagen 3.
Images are saved to reports/images/ and the file path is returned.

Handlers never raise — errors are returned as {"error": "..."} dicts.
"""

from __future__ import annotations

import base64
import logging
import re
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Output directory for generated images
IMAGES_DIR = Path("reports/images")

# Timeouts for image generation APIs (seconds)
IMAGE_GEN_TIMEOUT = 120.0


def _ensure_images_dir() -> Path:
    """Create the images output directory if it doesn't exist."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    return IMAGES_DIR


def _slugify(text: str, max_len: int = 40) -> str:
    """Create a filesystem-safe slug from text."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len]


def _make_filename(prompt: str, ext: str = "png") -> str:
    """Generate a timestamped filename from a prompt."""
    ts = int(time.time())
    slug = _slugify(prompt)
    return f"{ts}-{slug}.{ext}"


# =============================================================================
# OpenAI GPT Image 1
# =============================================================================

OPENAI_VALID_SIZES = {"1024x1024", "1536x1024", "1024x1536", "auto"}
OPENAI_VALID_QUALITIES = {"low", "medium", "high", "auto"}
OPENAI_VALID_STYLES = {"vivid", "natural"}


async def generate_image_openai(
    prompt: str,
    size: str = "auto",
    quality: str = "medium",
    style: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Generate an image using OpenAI GPT Image 1.

    Returns {"path": "...", "prompt": "..."} on success,
    or {"error": "..."} on failure.
    """
    if not api_key:
        return {"error": "OpenAI API key not configured (set OPENAI_API_KEY in .env)"}

    if size not in OPENAI_VALID_SIZES:
        size = "auto"
    if quality not in OPENAI_VALID_QUALITIES:
        quality = "medium"

    body: dict = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": quality,
    }
    if style and style in OPENAI_VALID_STYLES:
        body["style"] = style

    try:
        async with httpx.AsyncClient(timeout=IMAGE_GEN_TIMEOUT) as client:
            resp = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )

            if resp.status_code != 200:
                error_detail = resp.text[:300]
                return {"error": f"OpenAI API error ({resp.status_code}): {error_detail}"}

            data = resp.json()
            image_data = data.get("data", [{}])[0]

            # GPT Image 1 returns base64 by default
            b64 = image_data.get("b64_json")
            url = image_data.get("url")

            if b64:
                image_bytes = base64.b64decode(b64)
            elif url:
                img_resp = await client.get(url, timeout=60.0)
                if img_resp.status_code != 200:
                    return {"error": f"Failed to download image from URL ({img_resp.status_code})"}
                image_bytes = img_resp.content
            else:
                return {"error": "No image data in OpenAI response"}

        out_dir = _ensure_images_dir()
        filename = _make_filename(prompt)
        filepath = out_dir / filename
        filepath.write_bytes(image_bytes)

        logger.info("OpenAI image saved: %s (%d bytes)", filepath, len(image_bytes))
        return {"path": str(filepath), "prompt": prompt}

    except httpx.TimeoutException:
        return {"error": "OpenAI image generation timed out"}
    except Exception as e:
        logger.warning("OpenAI image generation failed: %s", e, exc_info=True)
        return {"error": f"OpenAI image generation failed: {str(e)[:200]}"}


# =============================================================================
# Google Gemini 3 Pro (Image Preview)
# =============================================================================

GEMINI_VALID_SIZES = {"1024x1024", "1536x1024", "1024x1536"}


async def generate_image_gemini(
    prompt: str,
    size: str = "1024x1024",
    api_key: str | None = None,
) -> dict:
    """Generate an image using Gemini 3 Pro (image preview).

    Returns {"path": "...", "prompt": "..."} on success,
    or {"error": "..."} on failure.
    """
    if not api_key:
        return {"error": "Gemini API key not configured (set GEMINI_API_KEY in .env)"}

    if size not in GEMINI_VALID_SIZES:
        size = "1024x1024"

    # Parse size into aspect ratio config
    width, height = (int(x) for x in size.split("x"))

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-3-pro-image-preview:predict"
        f"?key={api_key}"
    )

    body = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": f"{width}:{height}",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=IMAGE_GEN_TIMEOUT) as client:
            resp = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json=body,
            )

            if resp.status_code != 200:
                error_detail = resp.text[:300]
                return {"error": f"Gemini API error ({resp.status_code}): {error_detail}"}

            data = resp.json()
            predictions = data.get("predictions", [])
            if not predictions:
                return {"error": "No predictions in Gemini response"}

            b64 = predictions[0].get("bytesBase64Encoded")
            if not b64:
                return {"error": "No image data in Gemini response"}

            image_bytes = base64.b64decode(b64)

        out_dir = _ensure_images_dir()
        filename = _make_filename(prompt)
        filepath = out_dir / filename
        filepath.write_bytes(image_bytes)

        logger.info("Gemini image saved: %s (%d bytes)", filepath, len(image_bytes))
        return {"path": str(filepath), "prompt": prompt}

    except httpx.TimeoutException:
        return {"error": "Gemini image generation timed out"}
    except Exception as e:
        logger.warning("Gemini image generation failed: %s", e, exc_info=True)
        return {"error": f"Gemini image generation failed: {str(e)[:200]}"}
