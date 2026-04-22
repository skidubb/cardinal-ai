"""Discover Questions — surface vexing, categorized questions from a document.

Kills the "blank box" problem on /run: upload a 10-K / research paper / CIM
and get back a list of questions pre-mapped to the best-fit protocol.
"""

from __future__ import annotations

import html as _html_lib
import json
import logging
import re
from io import BytesIO
from typing import Literal

import anthropic
import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from api.context_pipeline import (
    MAX_FILE_SIZE,
    MAX_TOTAL_SIZE,
    _detect_file_type,
    _extract_text_from_docx,
    _extract_text_from_pdf,
)
from api.manifest import get_protocol_manifest
from api.middleware.clerk_auth import resolve_tenant
from protocols.config import ORCHESTRATION_MODEL, THINKING_MODEL
from protocols.llm import extract_text, llm_complete, parse_json_object

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["discover"])

# Token thresholds: if the doc is huge, pre-summarize with Haiku before Opus.
MAX_INLINE_TOKENS = 50_000
POST_SUMMARY_TARGET_TOKENS = 40_000
ESTIMATED_CHARS_PER_TOKEN = 4

AcceptedFileType = Literal["text", "pdf", "docx"]
_ACCEPTED_TYPES: set[str] = {"text", "pdf", "docx"}

QuestionCategory = Literal[
    "strategic",
    "financial",
    "operational",
    "competitive",
    "legal",
    "technical",
    "market",
    "people",
]
QuestionSeverity = Literal["high", "medium", "low"]


class DiscoveredQuestion(BaseModel):
    text: str
    category: QuestionCategory
    severity: QuestionSeverity
    rationale: str
    suggested_protocol: str
    suggested_protocol_name: str | None = None


class DiscoverResult(BaseModel):
    document_summary: str
    questions: list[DiscoveredQuestion] = Field(default_factory=list)
    source_filename: str
    token_count: int
    was_truncated: bool = False


def _extract_text_from_upload(file_type: str, raw: bytes) -> str:
    if file_type == "text":
        return raw.decode("utf-8", errors="replace")
    if file_type == "pdf":
        return _extract_text_from_pdf(raw)
    if file_type == "docx":
        return _extract_text_from_docx(raw)
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported file type '{file_type}'. Upload PDF, DOCX, TXT, or MD.",
    )


# ── URL ingestion ────────────────────────────────────────────────────────────
URL_FETCH_TIMEOUT = 20.0
MAX_URL_BYTES = 10_000_000  # 10 MB per URL
MAX_URLS = 5

# Block elements whose content is typically chrome, not article text.
_HTML_STRIP_TAGS = ("script", "style", "nav", "footer", "aside", "header", "form", "svg", "noscript")
# Block-level elements we want to preserve as paragraph breaks in the output.
_HTML_BLOCK_TAGS = ("p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "section", "article")
_HTML_BLOCK_RE = re.compile(
    r"</?(?:" + "|".join(_HTML_BLOCK_TAGS) + r")[^>]*>", re.IGNORECASE
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_WS_RE = re.compile(r"[ \t]+")
_HTML_NEWLINES_RE = re.compile(r"\n\s*\n\s*")


def _extract_text_from_html(raw: str) -> str:
    """Strip HTML to readable text using stdlib only.

    Good enough for Claude to reason over — not trying to replicate
    trafilatura-quality extraction. Removes scripts, styles, and common
    chrome; preserves paragraph breaks so structure survives.
    """
    cleaned = raw
    for tag in _HTML_STRIP_TAGS:
        cleaned = re.sub(
            rf"<{tag}\b[^>]*>.*?</{tag}>",
            " ",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        )
    cleaned = _HTML_BLOCK_RE.sub("\n", cleaned)
    cleaned = _HTML_TAG_RE.sub(" ", cleaned)
    cleaned = _html_lib.unescape(cleaned)
    cleaned = _HTML_WS_RE.sub(" ", cleaned)
    cleaned = _HTML_NEWLINES_RE.sub("\n\n", cleaned)
    return cleaned.strip()


async def _fetch_url_text(url: str) -> str:
    """Fetch a URL and return extracted text. Raises HTTPException on failure."""
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(
            status_code=400,
            detail=f"URL must start with http:// or https://: {url}",
        )
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=URL_FETCH_TIMEOUT,
            headers={"User-Agent": "CE-Discover/1.0 (+Cardinal Element)"},
        ) as client:
            resp = await client.get(url)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch {url}: {type(exc).__name__}: {exc}",
        ) from exc

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"URL returned HTTP {resp.status_code}: {url}",
        )

    raw_bytes = resp.content[:MAX_URL_BYTES]
    content_type = (resp.headers.get("content-type") or "").lower()

    # PDF URLs
    if "application/pdf" in content_type or url.lower().split("?", 1)[0].endswith(".pdf"):
        text = _extract_text_from_pdf(raw_bytes)
    else:
        # Treat everything else as text-ish; best-effort decode.
        try:
            body = raw_bytes.decode(resp.encoding or "utf-8", errors="replace")
        except (LookupError, UnicodeDecodeError):
            body = raw_bytes.decode("utf-8", errors="replace")
        if "html" in content_type or body.lstrip().lower().startswith(("<!doctype", "<html")):
            text = _extract_text_from_html(body)
        else:
            text = body

    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail=f"No extractable text at URL: {url}",
        )
    return text


def _token_estimate(text: str) -> int:
    return len(text) // ESTIMATED_CHARS_PER_TOKEN


def _build_protocol_catalog() -> list[dict]:
    """Surface a compact catalog the LLM can pick from."""
    manifest = get_protocol_manifest()
    catalog = []
    for p in manifest:
        catalog.append({
            "key": p["key"],
            "name": p["name"],
            "category": p["category"],
            "when_to_use": p.get("when_to_use") or p.get("description") or "",
            "problem_types": p.get("problem_types") or [],
        })
    return catalog


def _catalog_to_prompt_block(catalog: list[dict]) -> str:
    lines = []
    for p in catalog:
        pt = ", ".join(p["problem_types"]) if p["problem_types"] else ""
        when = (p["when_to_use"] or "").strip().splitlines()[0][:160]
        lines.append(f"- {p['key']} ({p['name']}) — {when} [types: {pt}]")
    return "\n".join(lines)


DISCOVER_SYSTEM = (
    "You surface the most analytically vexing, decision-relevant questions "
    "hiding in a document. You return strict JSON and never pad."
)


DISCOVER_USER_TEMPLATE = """You are a senior analyst. Read the document below and surface the 5-12 most
ANALYTICALLY VEXING questions a decision-maker should ask — not obvious
questions, not table-of-contents questions, but the ones where a wrong answer
costs real money or optionality.

For each question, also pick the single best-fit coordination protocol from the
catalog. The protocol you pick MUST be a `key` present in the catalog.

CATEGORIES (pick exactly one per question):
strategic | financial | operational | competitive | legal | technical | market | people

SEVERITY (pick exactly one):
high   — core to the decision; wrong answer materially changes the outcome
medium — shapes execution; wrong answer causes meaningful rework
low    — worth tracking; not decision-critical alone

CATEGORY → PROTOCOL GUIDANCE (use as strong prior; override only when a
specific protocol's `when_to_use` clearly fits better):
- strategic    → p04_multi_round_debate (decisions with opposing valid views)
- financial    → p39_popper_falsification (testable/falsifiable claim) OR
                 p32_tetlock_forecast (probabilistic forecast / scenarios)
- operational  → p13_ecocycle_planning (portfolio-wide lifecycle) OR
                 p22_sequential_pipeline (stepwise execution work)
- competitive  → p17_red_blue_white (adversarial pressure-test) OR
                 p06_triz (inversion / contradiction resolution)
- legal        → p16_ach (evidence-vs-hypothesis grid)
- technical    → p34_current_reality_tree (root-cause logic) OR
                 p06_triz (contradiction / design trade-offs)
- market       → p32_tetlock_forecast (quantified forecasts) OR
                 p07_wicked_questions (paradox / tension framing)
- people       → p09_troika_consulting (advisory facilitation) OR
                 p10_heard_seen_respected (empathy / listening patterns)

Special cases:
- Questions with a specific testable claim ("X will hold under Y") → prefer
  p39_popper_falsification over p32_tetlock_forecast.
- Questions that are truly bull/bear framings → p04_multi_round_debate wins.

PROTOCOL CATALOG:
{catalog}

OUTPUT FORMAT — return exactly this JSON shape, no prose:
{{
  "document_summary": "2-3 sentences, what this doc is and why it matters",
  "questions": [
    {{
      "text": "question phrased so an analyst can run it directly",
      "category": "strategic",
      "severity": "high",
      "rationale": "one sentence — why this is load-bearing",
      "suggested_protocol": "p06_triz"
    }}
  ]
}}

Return 5-12 questions. Prefer fewer, sharper questions over padding.

DOCUMENT:
<<<DOC
{document}
DOC
"""


SUMMARIZE_TEMPLATE = """Summarize the following document into roughly {target} tokens.

Preserve: specific numbers, entities, risks, strategic shifts, open questions,
footnote disclosures that matter. Drop: boilerplate, repetitive disclaimers,
standard definitions.

Return ONLY the compressed document — no preface, no header.

<<<DOC
{document}
DOC
"""


async def _maybe_summarize(
    client: anthropic.AsyncAnthropic, text: str
) -> tuple[str, bool]:
    """If text exceeds the inline threshold, compress with Haiku first."""
    tokens = _token_estimate(text)
    if tokens <= MAX_INLINE_TOKENS:
        return text, False

    prompt = SUMMARIZE_TEMPLATE.format(
        target=POST_SUMMARY_TARGET_TOKENS,
        document=text,
    )
    resp = await llm_complete(
        client,
        model=ORCHESTRATION_MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
        agent_name="discover_summarize",
    )
    return extract_text(resp), True


async def _discover_questions(
    client: anthropic.AsyncAnthropic, document: str, catalog: list[dict]
) -> dict:
    prompt = DISCOVER_USER_TEMPLATE.format(
        catalog=_catalog_to_prompt_block(catalog),
        document=document,
    )
    resp = await llm_complete(
        client,
        model=THINKING_MODEL,
        max_tokens=4096,
        system=DISCOVER_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        agent_name="discover_questions",
    )
    raw = extract_text(resp)
    try:
        return parse_json_object(raw)
    except Exception as exc:
        _log.warning("discover_questions JSON parse failed: %s\nRAW=%s", exc, raw[:1000])
        raise HTTPException(
            status_code=502,
            detail="LLM returned unparseable JSON. Try a different document or retry.",
        ) from exc


def _validate_questions(raw: dict, catalog: list[dict]) -> list[DiscoveredQuestion]:
    valid_keys = {p["key"] for p in catalog}
    name_by_key = {p["key"]: p["name"] for p in catalog}

    out: list[DiscoveredQuestion] = []
    for q in raw.get("questions", []):
        if not isinstance(q, dict):
            continue
        key = (q.get("suggested_protocol") or "").strip()
        if key not in valid_keys:
            # Silently drop hallucinated protocol keys rather than hard-failing.
            continue
        try:
            out.append(DiscoveredQuestion(
                text=str(q.get("text", "")).strip(),
                category=q.get("category"),
                severity=q.get("severity"),
                rationale=str(q.get("rationale", "")).strip(),
                suggested_protocol=key,
                suggested_protocol_name=name_by_key.get(key),
            ))
        except Exception as exc:
            _log.info("dropped malformed question: %s (%s)", q, exc)
            continue
    return out


@router.post("/discover-questions", response_model=DiscoverResult)
async def discover_questions(
    files: list[UploadFile] = File(default=[]),
    urls: list[str] = Form(default=[]),
    tenant_slug: str = Depends(resolve_tenant),
) -> DiscoverResult:
    # Filter out empty URL strings coming from the form (e.g. trailing input).
    cleaned_urls = [u.strip() for u in urls if u and u.strip()]

    if not files and not cleaned_urls:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one file or URL.",
        )
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Upload at most 5 files per call.")
    if len(cleaned_urls) > MAX_URLS:
        raise HTTPException(
            status_code=400,
            detail=f"Provide at most {MAX_URLS} URLs per call.",
        )

    total_bytes = 0
    extracted_blocks: list[tuple[str, str]] = []  # (label, text)
    for f in files:
        raw = await f.read()
        total_bytes += len(raw)
        if len(raw) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"{f.filename}: file exceeds 50 MB.",
            )
        if total_bytes > MAX_TOTAL_SIZE:
            raise HTTPException(status_code=413, detail="Total upload exceeds 200 MB.")

        filename = f.filename or "unknown"
        file_type = _detect_file_type(filename, f.content_type)
        if file_type not in _ACCEPTED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{filename}: unsupported file type. "
                    "Only PDF, DOCX, TXT, and MD are accepted."
                ),
            )
        text = _extract_text_from_upload(file_type, raw)
        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail=f"{filename}: no extractable text found.",
            )
        extracted_blocks.append((filename, text))

    for url in cleaned_urls:
        url_text = await _fetch_url_text(url)
        extracted_blocks.append((url, url_text))

    combined = "\n\n---\n\n".join(
        f"### {name}\n\n{body}" for name, body in extracted_blocks
    )
    if len(extracted_blocks) == 1:
        source_filename = extracted_blocks[0][0]
    else:
        parts = []
        if files:
            parts.append(f"{len(files)} file{'s' if len(files) != 1 else ''}")
        if cleaned_urls:
            parts.append(f"{len(cleaned_urls)} URL{'s' if len(cleaned_urls) != 1 else ''}")
        source_filename = " + ".join(parts)

    client = anthropic.AsyncAnthropic()

    document, was_truncated = await _maybe_summarize(client, combined)
    catalog = _build_protocol_catalog()
    if not catalog:
        raise HTTPException(
            status_code=500,
            detail="Protocol catalog is empty — server is misconfigured.",
        )

    raw = await _discover_questions(client, document, catalog)
    questions = _validate_questions(raw, catalog)

    if not questions:
        raise HTTPException(
            status_code=502,
            detail="No valid questions returned. Try a different document or retry.",
        )

    _log.info(
        "discover: tenant=%s filename=%s tokens=%d truncated=%s questions=%d",
        tenant_slug,
        source_filename,
        _token_estimate(combined),
        was_truncated,
        len(questions),
    )

    return DiscoverResult(
        document_summary=str(raw.get("document_summary", "")),
        questions=questions,
        source_filename=source_filename,
        token_count=_token_estimate(combined),
        was_truncated=was_truncated,
    )
