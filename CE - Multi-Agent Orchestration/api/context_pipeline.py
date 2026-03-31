"""Run context processing pipeline.

Handles file uploads for protocol runs: text extraction, threshold-based routing
(inline vs RAG), chunking, Pinecone upsert, retrieval, and cleanup.

Two Pinecone paths:
- Text-only RAG: uses the existing integrated-inference index (upsert_records / search).
- Media-present RAG: uses Gemini Embedding 2 for ALL content (text + media) and
  upserts raw 3072-dim vectors to a dedicated ``ce-run-context`` index.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from io import BytesIO

from fastapi import UploadFile

from api.text_utils import chunk_text

_log = logging.getLogger(__name__)

# Gemini Embedding 2 config
GEMINI_EMBEDDING_MODEL = "gemini-embedding-2-preview"
GEMINI_EMBEDDING_DIM = 3072
GEMINI_RUN_CONTEXT_INDEX = "ce-run-context"  # separate index for 3072-dim vectors

# ── Size limits ──────────────────────────────────────────────────────────────

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB per file
MAX_TOTAL_SIZE = 200 * 1024 * 1024  # 200 MB total

# Token threshold: below this, inject text directly into the prompt.
# Above this (or when media files are present), use RAG via Pinecone.
INLINE_TOKEN_THRESHOLD = 50_000

# ── File type detection ──────────────────────────────────────────────────────

_EXT_TO_TYPE: dict[str, str] = {
    ".txt": "text",
    ".md": "text",
    ".csv": "text",
    ".pdf": "pdf",
    ".docx": "docx",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".mp3": "audio",
    ".wav": "audio",
    ".mp4": "video",
    ".mov": "video",
}

MEDIA_TYPES = {"image", "audio", "video"}


def _detect_file_type(filename: str, content_type: str | None) -> str:
    """Detect file type from extension, falling back to MIME type."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in _EXT_TO_TYPE:
        return _EXT_TO_TYPE[ext]
    # Fallback to MIME
    if content_type:
        if content_type.startswith("image/"):
            return "image"
        if content_type.startswith("audio/"):
            return "audio"
        if content_type.startswith("video/"):
            return "video"
        if content_type in ("application/pdf",):
            return "pdf"
    return "text"  # default fallback


# ── Data structures ──────────────────────────────────────────────────────────


@dataclass
class ProcessedFile:
    filename: str
    content_type: str
    file_type: str  # "text" | "pdf" | "docx" | "image" | "audio" | "video"
    extracted_text: str | None  # None for media files
    raw_bytes: bytes
    token_estimate: int

    def metadata_dict(self) -> dict:
        """Serializable metadata (no raw bytes)."""
        return {
            "filename": self.filename,
            "content_type": self.content_type,
            "file_type": self.file_type,
            "size_bytes": len(self.raw_bytes),
        }


@dataclass
class RunContext:
    run_id: int
    files: list[ProcessedFile] = field(default_factory=list)
    mode: str = "inline"  # "inline" | "rag"
    inline_text: str | None = None
    pinecone_namespace: str | None = None  # "run-{run_id}" when mode="rag"
    has_media: bool = False

    def files_metadata_json(self) -> str:
        """JSON string of file metadata for DB storage."""
        return json.dumps([f.metadata_dict() for f in self.files])


# ── Text extraction ──────────────────────────────────────────────────────────


def _extract_text_from_pdf(raw_bytes: bytes) -> str:
    """Extract text from PDF using PyMuPDF."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=raw_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def _extract_text_from_docx(raw_bytes: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    from docx import Document

    doc = Document(BytesIO(raw_bytes))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_text(file_type: str, raw_bytes: bytes, filename: str) -> str | None:
    """Extract text from a file. Returns None for media files."""
    if file_type == "text":
        return raw_bytes.decode("utf-8", errors="replace")
    if file_type == "pdf":
        return _extract_text_from_pdf(raw_bytes)
    if file_type == "docx":
        return _extract_text_from_docx(raw_bytes)
    # Media files: no text extraction
    return None


# ── Processing pipeline ──────────────────────────────────────────────────────


async def process_uploaded_files(
    run_id: int,
    files: list[UploadFile],
) -> RunContext:
    """Process uploaded files and return a RunContext.

    Determines inline vs RAG mode based on total token count and media presence.
    For RAG mode, chunks text and upserts to Pinecone.
    """
    processed: list[ProcessedFile] = []

    for f in files:
        raw_bytes = await f.read()
        filename = f.filename or "unknown"
        content_type = f.content_type or "application/octet-stream"
        file_type = _detect_file_type(filename, content_type)

        extracted_text = _extract_text(file_type, raw_bytes, filename)
        token_estimate = len(extracted_text) // 4 if extracted_text else 0

        processed.append(ProcessedFile(
            filename=filename,
            content_type=content_type,
            file_type=file_type,
            extracted_text=extracted_text,
            raw_bytes=raw_bytes,
            token_estimate=token_estimate,
        ))

    has_media = any(f.file_type in MEDIA_TYPES for f in processed)
    total_tokens = sum(f.token_estimate for f in processed)

    ctx = RunContext(run_id=run_id, files=processed, has_media=has_media)

    if total_tokens < INLINE_TOKEN_THRESHOLD and not has_media:
        # Inline mode: concatenate all extracted text
        ctx.mode = "inline"
        text_blocks = []
        for f in processed:
            if f.extracted_text:
                text_blocks.append(f"### {f.filename}\n\n{f.extracted_text}")
        ctx.inline_text = "\n\n---\n\n".join(text_blocks)
        _log.info(
            "Run %d: inline mode (%d tokens across %d files)",
            run_id, total_tokens, len(processed),
        )
    else:
        # RAG mode: chunk + upsert to Pinecone
        ctx.mode = "rag"
        ctx.pinecone_namespace = f"run-{run_id}"
        await _upsert_to_pinecone(ctx)
        _log.info(
            "Run %d: RAG mode (namespace=%s, %d files, has_media=%s)",
            run_id, ctx.pinecone_namespace, len(processed), has_media,
        )

    return ctx


# ── Gemini Embedding 2 ───────────────────────────────────────────────────────


def _get_gemini_client():
    """Lazy-init Gemini client."""
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is required for media file embedding. "
            "Set it in .env or export it in your shell."
        )
    return genai.Client(api_key=api_key)


def _embed_bytes_with_gemini(raw_bytes: bytes, mime_type: str) -> list[float]:
    """Embed a single media file (image/audio/video) via Gemini Embedding 2."""
    from google.genai import types

    client = _get_gemini_client()
    result = client.models.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        contents=[types.Part.from_bytes(data=raw_bytes, mime_type=mime_type)],
    )
    return list(result.embeddings[0].values)


def _embed_text_with_gemini(text: str) -> list[float]:
    """Embed a text string via Gemini Embedding 2.

    Used when media files are present so all vectors live in the same space.
    """
    client = _get_gemini_client()
    result = client.models.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        contents=text,
    )
    return list(result.embeddings[0].values)


# ── Pinecone operations ──────────────────────────────────────────────────────


def _get_pinecone_client():
    """Get Pinecone client instance."""
    from pinecone import Pinecone

    return Pinecone(api_key=os.getenv("PINECONE_API_KEY"))


def _get_integrated_index():
    """Get the existing integrated-inference Pinecone index (text-only RAG)."""
    pc = _get_pinecone_client()
    index_name = os.getenv("PINECONE_INDEX", "ce-gtm-knowledge")
    return pc.Index(index_name)


def _get_gemini_index():
    """Get the dedicated 3072-dim Pinecone index for Gemini vectors.

    Uses PINECONE_RUN_CONTEXT_INDEX env var, defaulting to 'ce-run-context'.
    This index must be created with dimension=3072 and metric=cosine.
    """
    pc = _get_pinecone_client()
    index_name = os.getenv("PINECONE_RUN_CONTEXT_INDEX", GEMINI_RUN_CONTEXT_INDEX)
    return pc.Index(index_name)


def _ensure_gemini_index_exists() -> None:
    """Create the Gemini run-context index if it doesn't exist.

    Serverless index on aws/us-east-1 with 3072 dimensions, cosine metric.
    """
    from pinecone import Pinecone, ServerlessSpec

    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_name = os.getenv("PINECONE_RUN_CONTEXT_INDEX", GEMINI_RUN_CONTEXT_INDEX)

    existing = [idx.name for idx in pc.list_indexes()]
    if index_name in existing:
        return

    _log.info("Creating Pinecone index '%s' (3072-dim, cosine) for Gemini vectors...", index_name)
    pc.create_index(
        name=index_name,
        dimension=GEMINI_EMBEDDING_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
    _log.info("Pinecone index '%s' created.", index_name)


async def _upsert_to_pinecone(ctx: RunContext) -> None:
    """Chunk text files and upsert to Pinecone namespace.

    Text-only runs: uses Pinecone integrated inference (upsert_records) on the
    existing index.

    Media-present runs: uses Gemini Embedding 2 for ALL content (text chunks +
    media files) and upserts raw 3072-dim vectors to the dedicated
    ``ce-run-context`` index.
    """
    namespace = ctx.pinecone_namespace
    if not namespace:
        return

    if ctx.has_media:
        await _upsert_gemini_vectors(ctx, namespace)
    else:
        await _upsert_integrated(ctx, namespace)


async def _upsert_integrated(ctx: RunContext, namespace: str) -> None:
    """Upsert text chunks via Pinecone integrated inference (no Gemini needed)."""
    idx = _get_integrated_index()

    records = []
    chunk_id = 0
    for f in ctx.files:
        if not f.extracted_text:
            continue
        chunks = chunk_text(f.extracted_text)
        for chunk in chunks:
            records.append({
                "_id": f"run-{ctx.run_id}-chunk-{chunk_id}",
                "text": chunk,
                "filename": f.filename,
                "file_type": f.file_type,
                "chunk_index": chunk_id,
            })
            chunk_id += 1

    if records:
        batch_size = 96  # Pinecone integrated inference limit
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            idx.upsert_records(namespace=namespace, records=batch)
        _log.info(
            "Run %d: upserted %d text chunks to namespace %s (integrated)",
            ctx.run_id, len(records), namespace,
        )


async def _upsert_gemini_vectors(ctx: RunContext, namespace: str) -> None:
    """Embed ALL content via Gemini Embedding 2 and upsert raw vectors.

    When media files are present, both text chunks AND media files are embedded
    through Gemini so everything lives in the same 3072-dim vector space.
    """
    _ensure_gemini_index_exists()
    idx = _get_gemini_index()

    vectors = []
    vec_id = 0

    # Embed text chunks
    for f in ctx.files:
        if not f.extracted_text:
            continue
        chunks = chunk_text(f.extracted_text)
        for chunk in chunks:
            try:
                embedding = _embed_text_with_gemini(chunk)
                vectors.append({
                    "id": f"run-{ctx.run_id}-text-{vec_id}",
                    "values": embedding,
                    "metadata": {
                        "text": chunk,
                        "filename": f.filename,
                        "file_type": f.file_type,
                        "modality": "text",
                        "chunk_index": vec_id,
                    },
                })
                vec_id += 1
            except Exception as e:
                _log.warning("Failed to embed text chunk %d from %s: %s", vec_id, f.filename, e)

    # Embed media files
    for f in ctx.files:
        if f.file_type not in MEDIA_TYPES:
            continue
        try:
            embedding = _embed_bytes_with_gemini(f.raw_bytes, f.content_type)
            vectors.append({
                "id": f"run-{ctx.run_id}-media-{vec_id}",
                "values": embedding,
                "metadata": {
                    "text": f"[{f.file_type}: {f.filename}]",
                    "filename": f.filename,
                    "file_type": f.file_type,
                    "modality": f.file_type,
                    "size_bytes": len(f.raw_bytes),
                },
            })
            vec_id += 1
            _log.info("Embedded %s file: %s (%d bytes)", f.file_type, f.filename, len(f.raw_bytes))
        except Exception as e:
            _log.warning("Failed to embed media file %s: %s", f.filename, e)

    if vectors:
        batch_size = 100  # standard Pinecone upsert limit
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            idx.upsert(vectors=batch, namespace=namespace)
        _log.info(
            "Run %d: upserted %d vectors to namespace %s (Gemini)",
            ctx.run_id, len(vectors), namespace,
        )


async def retrieve_context(
    namespace: str,
    query: str,
    top_k: int = 10,
    use_gemini: bool = False,
) -> str:
    """Retrieve relevant context chunks from Pinecone for a query.

    Args:
        namespace: Pinecone namespace (``run-{id}``).
        query: User's question to match against.
        top_k: Number of results to return.
        use_gemini: If True, query the Gemini index with a Gemini-embedded query
            vector. Otherwise use integrated inference on the standard index.

    Returns formatted text with source attribution.
    """
    if use_gemini:
        return await _retrieve_gemini(namespace, query, top_k)
    return await _retrieve_integrated(namespace, query, top_k)


async def _retrieve_integrated(namespace: str, query: str, top_k: int) -> str:
    """Retrieve from integrated-inference index."""
    idx = _get_integrated_index()

    results = idx.search(
        namespace=namespace,
        query={"top_k": top_k, "inputs": {"text": query}},
    )

    chunks = []
    for match in results.get("result", {}).get("hits", []):
        text = match.get("fields", {}).get("text", "")
        score = match.get("_score", 0)
        source = match.get("fields", {}).get("filename", "unknown")
        if text:
            chunks.append(f"[Source: {source}, relevance: {score:.2f}]\n{text}")

    return "\n\n---\n\n".join(chunks)


async def _retrieve_gemini(namespace: str, query: str, top_k: int) -> str:
    """Retrieve from Gemini index using a Gemini-embedded query vector."""
    idx = _get_gemini_index()

    query_embedding = _embed_text_with_gemini(query)
    results = idx.query(
        namespace=namespace,
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
    )

    chunks = []
    for match in results.get("matches", []):
        meta = match.get("metadata", {})
        text = meta.get("text", "")
        score = match.get("score", 0)
        source = meta.get("filename", "unknown")
        modality = meta.get("modality", "text")
        if text:
            prefix = f"[Source: {source}, relevance: {score:.2f}, type: {modality}]"
            chunks.append(f"{prefix}\n{text}")

    return "\n\n---\n\n".join(chunks)


async def cleanup_run_context(namespace: str) -> None:
    """Delete a run-scoped Pinecone namespace from both indexes."""
    # Clean up from integrated index
    try:
        idx = _get_integrated_index()
        idx.delete(namespace=namespace, delete_all=True)
    except Exception as e:
        _log.debug("Integrated index cleanup for %s: %s", namespace, e)

    # Clean up from Gemini index
    try:
        idx = _get_gemini_index()
        idx.delete(namespace=namespace, delete_all=True)
    except Exception as e:
        _log.debug("Gemini index cleanup for %s: %s", namespace, e)

    _log.info("Cleaned up Pinecone namespace: %s", namespace)


# ── Question augmentation ────────────────────────────────────────────────────


async def build_effective_question(question: str, context: RunContext) -> str:
    """Augment a question with context from uploaded files.

    Inline mode: prepend full extracted text.
    RAG mode: retrieve top-K relevant chunks from Pinecone.
    """
    if context.mode == "inline" and context.inline_text:
        return (
            f"## Uploaded Context\n\n"
            f"{context.inline_text}\n\n"
            f"---\n\n"
            f"## Question\n\n{question}"
        )

    if context.mode == "rag" and context.pinecone_namespace:
        retrieved = await retrieve_context(
            context.pinecone_namespace, question, use_gemini=context.has_media,
        )
        if retrieved:
            return (
                f"## Retrieved Context (from uploaded files)\n\n"
                f"{retrieved}\n\n"
                f"---\n\n"
                f"## Question\n\n{question}"
            )

    return question
