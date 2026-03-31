# Run Context Upload — Design Spec

**Date**: 2026-03-30
**Status**: Approved
**Author**: Scott Ewalt + Claude

## Problem

Protocol runs accept only a text question. Users need to upload files (contracts, data, media) as context for agents to analyze alongside the question. Example: Imagine Wireless stakeholders negotiating a contract, or an internal team reviewing uploaded data as part of a strategy question.

## Solution

Add file upload support to protocol runs. Files are processed, embedded, and injected into agent prompts automatically. Context is ephemeral — scoped to a single run and deleted after completion.

## Architecture

### Multimodal Embedding via Gemini Embedding 2

Google's Gemini Embedding 2 natively embeds text, images, audio (up to 120s), video (up to 120s), and PDFs into a single 3072-dimensional vector space. No transcription or text extraction needed for media files.

### Threshold-Based Routing

- **Inline mode**: Total extracted text < ~50K tokens AND no media files. Full text prepended to the question string. No Pinecone needed.
- **RAG mode**: Large text or media files present. Content chunked/embedded, stored in Pinecone namespace `run-{run_id}`, top-K retrieved before each agent turn.

### Vector Space Consistency

- Text-only RAG runs: Use Pinecone integrated inference (existing `multilingual-e5-large` model). No Gemini API needed.
- Media-present RAG runs: Use Gemini Embedding 2 for ALL content (text + media) to keep the vector space consistent.

## Components

### 1. Context Processing Pipeline

**New file**: `CE - Multi-Agent Orchestration/api/context_pipeline.py`

#### Data Structures

```python
@dataclass
class ProcessedFile:
    filename: str
    content_type: str
    file_type: str  # "text" | "pdf" | "docx" | "image" | "audio" | "video"
    extracted_text: str | None  # None for media files
    raw_bytes: bytes
    token_estimate: int

@dataclass
class RunContext:
    run_id: int
    files: list[ProcessedFile]
    mode: str  # "inline" | "rag"
    inline_text: str | None
    pinecone_namespace: str | None  # "run-{run_id}" when mode="rag"
```

#### File Processing

| File Type | Extension | Processing |
|-----------|-----------|------------|
| Text | .txt, .md, .csv | UTF-8 decode |
| PDF | .pdf | PyMuPDF (existing dep) |
| DOCX | .docx | python-docx (new dep) |
| Image | .png, .jpg, .jpeg | Raw bytes to Gemini Embedding 2 |
| Audio | .mp3, .wav | Raw bytes to Gemini Embedding 2 |
| Video | .mp4, .mov | Raw bytes to Gemini Embedding 2 |

#### Processing Flow

```
process_uploaded_files(run_id, files)
  |
  +--> detect file type (MIME + extension)
  +--> extract text (PDF/DOCX/TXT) or keep raw bytes (media)
  +--> estimate tokens: sum(len(text) / 4)
  |
  +--> if total_tokens < 50K AND no media:
  |      mode = "inline"
  |      inline_text = format_all_extracted_text(files)
  |
  +--> else:
         mode = "rag"
         has_media = any(f.file_type in ("image","audio","video") for f in files)
         |
         +--> if has_media:
         |      embed ALL content via Gemini Embedding 2
         |      upsert raw vectors to Pinecone namespace run-{run_id}
         |
         +--> else:
                chunk text via chunk_text() (1500 char, 200 overlap)
                upsert_records() to Pinecone (integrated inference)
```

#### Chunking

Extract `chunk_text()` from `scripts/ingest_papers.py` (lines 116-143) into a shared utility `api/text_utils.py`. The original script has module-level side effects and heavy dependencies that make direct import impractical. The function itself is self-contained (1500-char chunks, 200-char overlap, smart paragraph/sentence boundary detection).

#### Gemini Embedding 2 Integration

Model: `gemini-embedding-2-preview` (3072-dim output, cosine metric).

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Media embedding (image/audio/video)
result = client.models.embed_content(
    model="gemini-embedding-2-preview",
    contents=[types.Part.from_bytes(data=raw_bytes, mime_type=content_type)],
)
embedding = result.embeddings[0].values  # 3072-dim vector

# Text embedding (same vector space)
result = client.models.embed_content(
    model="gemini-embedding-2-preview",
    contents="query text here",
)
```

Input limits: audio max 80s, video max 120s, images max 6/request, PDFs max 6 pages.

Used only when media files are present. When media is detected, ALL content (text + media) is embedded via Gemini to keep the vector space consistent. Text-only RAG uses Pinecone integrated inference (no Gemini needed).

#### Dual Pinecone Index Strategy

- **Text-only RAG**: existing `ce-gtm-knowledge` index (integrated inference, `upsert_records` / `search`)
- **Media-present RAG**: dedicated `ce-run-context` index (3072-dim, cosine, serverless). Auto-created on first media upload. Queried via `idx.query(vector=gemini_embed(query))`.

Both indexes use run-scoped namespaces (`run-{id}`) that are deleted after run completion. Cleanup sweeps both indexes.

### 2. API Changes

**Modified**: `CE - Multi-Agent Orchestration/api/routers/protocols.py`

Add a separate endpoint `/run/with-context` for file uploads. The existing `/run` JSON endpoint stays untouched for backward compatibility.

```python
MAX_FILE_SIZE = 50 * 1024 * 1024      # 50MB per file
MAX_TOTAL_SIZE = 200 * 1024 * 1024    # 200MB total

@router.post("/run/with-context")
async def start_protocol_run_with_context(
    protocol_key: str = Form(...),
    question: str = Form(...),
    agent_keys: str = Form(...),  # JSON-encoded list
    thinking_model: str = Form(THINKING_MODEL),
    orchestration_model: str = Form(ORCHESTRATION_MODEL),
    rounds: int | None = Form(None),
    no_tools: bool = Form(False),
    files: list[UploadFile] = File(default=[]),
) -> StreamingResponse:
    # Validate file sizes before processing
    total_size = 0
    for f in files:
        content = await f.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(413, f"File '{f.filename}' exceeds 50MB limit")
        total_size += len(content)
        await f.seek(0)  # reset for downstream read
    if total_size > MAX_TOTAL_SIZE:
        raise HTTPException(413, f"Total upload size ({total_size // (1024*1024)}MB) exceeds 200MB limit")
```

**Modified**: `CE - Multi-Agent Orchestration/api/runner.py`

Add `context: RunContext | None = None` parameter to `run_protocol_stream()`. Wire context injection and cleanup.

### 3. Context Injection

Zero changes to orchestrators. Context injected at the runner level by augmenting the question string.

**Inline mode**:
```
## Uploaded Context
[full extracted text from all files]
---
## Question
[user's original question]
```

**RAG mode** — retrieve top-K chunks before calling orchestrator. The retrieval method depends on how vectors were stored:

```python
async def retrieve_context(
    namespace: str, query: str, top_k: int = 10, use_gemini: bool = False
) -> str:
    idx = pc.Index(os.getenv("PINECONE_INDEX"))

    if use_gemini:
        # Media runs: query with Gemini-generated vector (same space as stored vectors)
        query_embedding = embed_text_with_gemini(query)
        results = idx.query(namespace=namespace, vector=query_embedding, top_k=top_k,
                           include_metadata=True)
    else:
        # Text-only runs: use Pinecone integrated inference
        results = idx.search(namespace=namespace,
                            query={"top_k": top_k, "inputs": {"text": query}})
    # Format as source-attributed text blocks
```

**Pinecone index requirements**: The existing `ce-gtm-knowledge` index uses `multilingual-e5-large` (1024-dim) via integrated inference. Gemini Embedding 2 produces 3072-dim vectors. These cannot coexist in the same index. Options:
- **Recommended**: Create a dedicated `ce-run-context` index with 3072 dimensions for media-present runs. Text-only runs continue using the existing index.
- **Alternative**: Use Gemini Embedding 2 for all run context (both text and media) and always use the `ce-run-context` index. Simpler routing but requires Gemini API key even for text-only RAG.

Injected as:
```
## Retrieved Context (from uploaded files)
[Source: contract.pdf, relevance: 0.94]
Section 4.2: The licensee agrees to...
---
## Question
[user's original question]
```

### 4. Pinecone Namespace Lifecycle

- **Creation**: Implicit on first upsert (Pinecone creates namespaces on write)
- **Namespace format**: `run-{run_id}`
- **Cleanup**: In `runner.py`, initialize `run_context = None` **before** the `try` block. Set it inside `try` after processing files. In the existing `finally` block, check `if run_context and run_context.pinecone_namespace:` and call `idx.delete(namespace=..., delete_all=True)`. This ensures cleanup runs even if the orchestrator crashes.
- **Orphan cleanup**: On server startup, delete all `run-*` namespaces from both the existing index and the `ce-run-context` index (if it exists). Pinecone does not expose namespace creation timestamps, so we clean all orphans unconditionally — acceptable since run context is ephemeral.

### 5. Database Schema

**Modified**: `CE - Multi-Agent Orchestration/api/models.py`

Add to `Run` model:
```python
context_mode: Optional[str] = None       # "inline" | "rag" | None
context_files_json: str = "[]"           # [{filename, content_type, size_bytes}]
```

Metadata only — actual file content is not persisted (ephemeral).

Note: SQLite requires deleting `orchestrator.db` to pick up schema changes (per existing warning in models.py).

### 6. UI Changes

**Modified**: `CE - Multi-Agent Orchestration/ui/src/pages/RunView.tsx`

File upload zone between question textarea and Run button:
- Multi-file select with drag-and-drop
- File list with name, size, remove button
- Accepted types: `.pdf, .docx, .txt, .md, .csv, .png, .jpg, .jpeg, .mp3, .wav, .mp4, .mov`
- File size limits: 50MB per file, 200MB total

**Modified**: `CE - Multi-Agent Orchestration/ui/src/hooks/useRunStream.ts`

When files present, switch from JSON POST to FormData (same pattern as `api.knowledge.upload()`). No Content-Type header — browser sets multipart boundary automatically.

New SSE event `context_processing` shows progress during file processing phase. Handle in `useRunStream.ts`:
```typescript
// In handleEvent():
case 'context_processing':
    setState(s => ({ ...s, currentStage: data.message }))
    break
```

### 7. New Dependencies

Add to `CE - Multi-Agent Orchestration/requirements.txt`:
```
python-docx>=1.1.0       # DOCX text extraction
google-genai>=1.0.0       # Gemini Embedding 2 (media embedding)
```

### 8. Environment Variables

New optional env var:
```
GEMINI_API_KEY=...        # Required only for media file uploads (audio/video/image)
```

Text-only uploads work without Gemini API key (uses Pinecone integrated inference or inline injection).

## Implementation Sequence

### Phase 1: Backend Foundation
1. Create `api/context_pipeline.py` with data structures, text extraction, threshold routing
2. Add schema fields to `Run` model
3. Add `python-docx` dependency

### Phase 2: API Integration
4. Add multipart endpoint to `protocols.py`
5. Wire `RunContext` into `run_protocol_stream()` in `runner.py`
6. Implement inline context injection (question augmentation)
7. Implement RAG context injection (Pinecone retrieval)
8. Add namespace cleanup to `finally` block

### Phase 3: UI
9. Add file upload widget to `RunView.tsx`
10. Modify `useRunStream.ts` for FormData submission
11. Handle `context_processing` SSE event

### Phase 4: Media Support ✅ IMPLEMENTED
12. Add `google-genai` dependency
13. Auto-create `ce-run-context` Pinecone index (3072-dim, cosine, serverless)
14. Implement Gemini Embedding 2 for media files (image/audio/video) + text (same space)
15. Dual retrieval path: integrated inference for text-only, Gemini query for media runs
16. Cleanup sweeps both indexes

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Large uploads block event loop | `UploadFile.read()` is async in FastAPI; processing happens before SSE stream starts. Enforce 50MB per file / 200MB total limit. |
| Namespace not cleaned on crash | `finally` block handles normal exits; startup sweep deletes all orphan `run-*` namespaces unconditionally |
| Token estimate inaccurate | 50K threshold is a guideline; off by 2x is acceptable with modern context windows |
| Mixed vector spaces (integrated + Gemini) | When media present, use Gemini for ALL content in that run |
| No GEMINI_API_KEY configured | Text-only uploads still work via Pinecone integrated inference or inline. Media uploads return clear error. |

## Files Modified

| File | Change |
|------|--------|
| `api/context_pipeline.py` | **NEW** — core processing pipeline |
| `api/text_utils.py` | **NEW** — `chunk_text()` extracted from `scripts/ingest_papers.py` |
| `api/routers/protocols.py` | Add multipart form endpoint |
| `api/runner.py` | Accept RunContext, inject into question, cleanup namespace |
| `api/models.py` | Add context_mode, context_files_json to Run |
| `ui/src/pages/RunView.tsx` | File upload widget |
| `ui/src/hooks/useRunStream.ts` | FormData submission path |
| `requirements.txt` | python-docx, google-genai |

## Verification

1. **Inline mode**: Upload a 2-page PDF + run a protocol. Verify the question sent to orchestrator includes extracted text.
2. **RAG mode**: Upload a 50-page document + run. Verify Pinecone namespace created, chunks retrieved, namespace deleted after completion.
3. **Media**: Upload an image + run. Verify Gemini embedding created, stored in Pinecone, retrievable.
4. **Backward compatibility**: Run a protocol with no files (JSON POST). Verify existing behavior unchanged.
5. **Cleanup**: Kill a run mid-flight. Verify namespace eventually cleaned up (startup sweep or finally block).
