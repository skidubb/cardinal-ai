# Phase 6: Structured Output and Reports - Research

**Researched:** 2026-03-10
**Domain:** Python dataclasses / FastAPI PDF endpoint / React report rendering / WeasyPrint PDF generation
**Confidence:** HIGH

---

## Summary

Phase 6 has two distinct halves. The first half (06-01) is a pure Python exercise: define a `ProtocolReport` dataclass in `protocols/` and write a transform that converts the existing `RunEnvelope` (already built in Phase 5) into it. The second half (06-02) is full-stack: add a FastAPI endpoint that renders a Jinja2 HTML template through WeasyPrint into a PDF, add a public HTML route for client sharing, and wire the React `RunView` to show all `ProtocolReport` fields.

The hard data-extraction problem is already solved. `run_envelope.py` extracts agent outputs, synthesis, cost, and tool calls from all 50 protocol result shapes into a normalized `RunEnvelope`. `ProtocolReport` is a presentation layer on top of it, not a new extraction layer. The `JudgeVerdict` (completeness, consistency, actionability, overall 1-5 scores) is already produced per-run and emitted via SSE, but NOT currently persisted to the Run table. This is the single most important infrastructure gap to close in 06-01.

The main open risk is WeasyPrint: it requires system-level libraries (pango, cairo, fontconfig) that may not be present on the macOS dev machine or in a Vercel Lambda. A working smoke test must be confirmed before plan 06-02 commits to WeasyPrint.

**Primary recommendation:** Build `ProtocolReport` as a thin dataclass populated from `RunEnvelope` fields. Add `judge_verdict_json` TEXT column to the `Run` table (drop-and-recreate `orchestrator.db` in dev; Alembic in Phase 8). Use `JudgeVerdict.overall` (integer 1-5) as the confidence source and render as filled dots. Use WeasyPrint + Jinja2 for PDF. Use `/share/{id}` (not `/runs/{id}`) for the public shareable URL to avoid React Router collision.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OUT-01 | ProtocolReport dataclass with: participants, key_findings, disagreements, confidence_score, synthesis, agent_contributions, cost_summary, metadata | RunEnvelope already holds all these fields; JudgeVerdict provides confidence score; transform is a mapping function, not new extraction |
| OUT-02 | All protocol result types transform into ProtocolReport | build_run_envelope() + extract_agent_outputs() already normalize all 50 protocol shapes; ProtocolReport transform reads from RunEnvelope, not raw result objects |
| OUT-03 | Browser view renders ProtocolReport with scannable sections | React RunView already renders synthesis + agent outputs; extend with executive summary, collapsible agent cards, disagreement panel |
| OUT-04 | Agent disagreement sections visually highlighted | Requires disagreement extraction heuristic (signal words in synthesis); render with amber border styling |
| OUT-05 | Confidence score displays as visual indicator (not raw number) | JudgeVerdict.overall is integer 1-5; render as filled circles; currently shown as raw number in JudgeVerdictCard |
| OUT-06 | Per-agent contribution cards showing what each agent contributed | AgentOutputEnvelope has agent_key, agent_name, text, cost_usd, tool_calls; render as expandable cards |
| REPT-01 | GET /api/reports/{run_id}/pdf generates PDF via WeasyPrint + Jinja2 | New endpoint; reads Run + AgentOutput from DB, builds ProtocolReport, renders template, returns application/pdf |
| REPT-02 | PDF includes executive summary, key findings, disagreements, agent contributions, cost metadata | Same data as browser report; Jinja2 template mirrors browser layout |
| REPT-03 | Browser-viewable HTML report at shareable URL with read-only access | New public FastAPI route at /share/{id}; bypasses auth_middleware; read-only |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python dataclasses | stdlib | ProtocolReport definition | Already used across all protocol result types in this codebase |
| Jinja2 | 3.1.6 (already installed in venv) | HTML and PDF templates | Already a transitive dep via FastAPI/Starlette; no new install needed |
| WeasyPrint | 62.x (not yet installed) | HTML-to-PDF rendering | Named in requirements spec (REPT-01); CSS-driven layout matches web output |
| React + Tailwind | 19.2 + 4.2 (already in UI) | Report browser view | Existing stack; ProtocolReport sections are new components in existing RunView |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FastAPI Response | same as FastAPI | Stream PDF bytes | Return Response(content=pdf_bytes, media_type='application/pdf') |
| FastAPI HTMLResponse | same | Serve shareable HTML | GET /share/{id} public route |
| dataclasses.asdict | stdlib | Serialize ProtocolReport to dict | JSON response from GET /api/runs/{id} with report field |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WeasyPrint | reportlab | reportlab requires programmatic layout (verbose); WeasyPrint renders HTML/CSS directly |
| WeasyPrint | pdfkit (wkhtmltopdf) | wkhtmltopdf is abandoned upstream; WeasyPrint is actively maintained |
| Jinja2 template | HTML string concat | Template is testable and maintainable; Jinja2 already in venv |

**Installation (new additions only):**
```
pip install weasyprint
# Add to api/requirements.txt
```

---

## Architecture Patterns

### Recommended Project Structure
```
protocols/
├── run_envelope.py          # Existing: RunEnvelope, AgentOutputEnvelope
└── protocol_report.py       # NEW: ProtocolReport dataclass + from_envelope()

api/
├── routers/
│   ├── runs.py              # Existing: extend GET /{run_id} to include protocol_report
│   └── reports.py           # NEW: GET /api/reports/{run_id}/pdf
├── templates/
│   └── report.html.j2       # NEW: Jinja2 template for PDF and shareable HTML

ui/src/
├── pages/RunView.tsx        # Existing: extend with ProtocolReport rendering sections
└── components/
    └── ProtocolReport.tsx   # NEW: ProtocolReport display component
```

### Pattern 1: ProtocolReport as Presentation Layer Over RunEnvelope

**What:** ProtocolReport is a pure dataclass (no ORM, no DB) populated by `from_envelope(envelope, judge_verdict) -> ProtocolReport`. All data comes from the already-normalized RunEnvelope.

**When to use:** Always. Never build ProtocolReport from raw protocol result objects -- RunEnvelope already handles all 50 protocol shape variations.

**Key data mappings:**
- `participants` <- `envelope.agent_keys`
- `executive_summary` <- first paragraph of `envelope.result_summary`
- `key_findings` <- bullet lines extracted from `envelope.result_summary`
- `disagreements` <- heuristic keyword scan on `envelope.result_summary`
- `confidence_score` <- `judge_verdict['overall']` (int 1-5), 0 if no verdict
- `synthesis` <- `envelope.result_summary` (full text)
- `agent_contributions` <- `envelope.agent_outputs` filtered to exclude `_synthesis`, `_result`, `_stage`
- `cost_summary` <- `envelope.cost`
- `metadata` <- `started_at`, `completed_at`, `trace_id` from envelope

### Pattern 2: GET /api/reports/{run_id}/pdf Endpoint

**What:** FastAPI endpoint that loads Run + AgentOutput rows from SQLite, reconstructs RunEnvelope, calls from_envelope(), renders Jinja2 template, passes to WeasyPrint, returns PDF bytes.

**Critical:** WeasyPrint is CPU-bound. Wrap write_pdf() in asyncio.to_thread() to avoid blocking the event loop.

```python
# api/routers/reports.py
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

@router.get('/{run_id}/pdf')
async def get_run_pdf(run_id: int, session=Depends(get_session)) -> Response:
    run = session.get(Run, run_id)
    if not run or run.status != 'completed':
        raise HTTPException(status_code=404)
    envelope = build_envelope_from_db(run, session)
    judge_verdict = _load_judge_verdict(run)
    report = from_envelope(envelope, judge_verdict)
    html = _jinja_env.get_template('report.html.j2').render(report=report)
    pdf_bytes = await asyncio.to_thread(weasyprint.HTML(string=html).write_pdf)
    filename = f'ce-report-{run.protocol_key}-{run.id}.pdf'
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )
```

### Pattern 3: Public Shareable HTML Route (REPT-03)

**What:** A FastAPI route at `/share/{run_id}` that serves styled HTML using the same Jinja2 template, bypassing auth middleware.

**How to exclude from auth:** In `server.py` `auth_middleware`, add `/share/` to the exclusion prefix list:

```python
PUBLIC_PATH_PREFIXES = ('/api/health', '/api/auth/login', '/share/')

@app.middleware('http')
async def auth_middleware(request, call_next):
    if SKIP_AUTH or request.method == 'OPTIONS':
        return await call_next(request)
    if any(request.url.path.startswith(p) for p in PUBLIC_PATH_PREFIXES):
        return await call_next(request)
    # ... auth check
```

### Pattern 4: Confidence Score Visual Indicator (React)

**What:** JudgeVerdict.overall is integer 1-5. Map to 5 filled/empty dots. Color: green (4-5), yellow (3), red (1-2), gray (0/unscored).

**Implementation:** New `ConfidenceIndicator` component with `data-testid='confidence-indicator'`. Replace raw number rendering in JudgeVerdictCard.

### Pattern 5: Disagreement Extraction Heuristic

**What:** Keyword scan on synthesis text. DISAGREEMENT_SIGNALS = ('however', 'disagree', 'contrary', 'alternative view', 'dissent', 'in contrast', 'on the other hand').

**Implementation:** Split synthesis on '. '. Return sentences containing any signal word. Cap at 4 disagreements.

### Anti-Patterns to Avoid

- **Building ProtocolReport from raw protocol result objects:** 50 different shapes. RunEnvelope already handles all. Always use from_envelope().
- **Persisting ProtocolReport to DB:** Computed on-read. Keep DB schema stable.
- **Calling write_pdf() on main async thread:** CPU-bound. Use asyncio.to_thread().
- **Using /runs/{id} as shareable HTML URL:** React Router owns /runs/*. Use /share/{id}.
- **Complex NLP for disagreement detection:** Keyword heuristic on synthesis text is sufficient for v1.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML-to-PDF conversion | Custom PDF layout code | WeasyPrint | CSS-driven; matches web template; handles pagination |
| Agent output normalization | New per-protocol extraction | build_run_envelope() + extract_agent_outputs() | Already handles all 50 protocol shapes; tested |
| HTML template rendering | String concatenation | Jinja2 Environment + FileSystemLoader | Auto-escaping, cacheable; already in venv |
| Confidence label mapping | Inline if/else chains | _score_label(score) in protocol_report.py | Centralized and unit-testable |

**Key insight:** The entire data pipeline from protocol result to normalized output is already built in run_envelope.py. Phase 6 only adds a presentation layer on top.

---

## Common Pitfalls

### Pitfall 1: WeasyPrint System Library Dependency
**What goes wrong:** `import weasyprint` succeeds but `write_pdf()` fails with `OSError: cannot load library 'pango-1.0'`.
**Why it happens:** WeasyPrint wraps native pango, cairo, fontconfig, gdk-pixbuf via cffi. Not bundled with the Python package.
**How to avoid:** On macOS: `brew install pango`. Verify with smoke test before building endpoint: `python -c 'import weasyprint; weasyprint.HTML(string="<p>test</p>").write_pdf()'`
**Warning signs:** cffi import errors, OSError: cannot load library, PDF endpoint returning 500.

### Pitfall 2: Routing Collision Between React SPA and FastAPI HTML Route
**What goes wrong:** /runs/{id} is owned by React Router client-side. FastAPI serving HTML at the same path conflicts with the StaticFiles catch-all that serves index.html.
**How to avoid:** Use /share/{run_id} for server-rendered HTML. This path is unknown to React Router. FastAPI handles /share/* before StaticFiles catch-all.

### Pitfall 3: JudgeVerdict Not Persisted to DB
**What goes wrong:** JudgeVerdict is emitted as SSE and scored to Langfuse but NOT in the Run table. PDF endpoint cannot show confidence score for past runs.
**How to avoid:** Add `judge_verdict_json: str = '{}'` to Run SQLModel class. Update runner.py to write it when persisting the completed run. In dev: delete orchestrator.db and restart.
**Warning signs:** PDF shows 'Unscored' even when the live run showed a quality score.

### Pitfall 4: key_findings Extraction Fragility
**What goes wrong:** Complex regex on free-form Opus prose breaks on style variations.
**How to avoid:** Extract lines starting with `- ` or `* ` as findings. Fall back to first 3 sentences. Keep it simple and unit-tested.

### Pitfall 5: Blocking Event Loop With WeasyPrint
**What goes wrong:** write_pdf() is synchronous and CPU-intensive (1-5 seconds). Called directly in async endpoint, it blocks uvicorn event loop.
**How to avoid:** `pdf_bytes = await asyncio.to_thread(weasyprint.HTML(string=html).write_pdf)`

---

## Code Examples

### Adding judge_verdict_json to Run Model

```python
# api/models.py -- add to Run class
class Run(SQLModel, table=True):
    # ... existing fields ...
    judge_verdict_json: str = '{}'  # serialized JudgeVerdict dict
```

Note: SQLite will not auto-add this column. Delete orchestrator.db and restart the server in dev.

### Updating runner.py to Persist judge_verdict_json

```python
# In run_protocol_stream(), after verdict = await judge.evaluate():
judge_verdict_dict = verdict.as_dict()
# In the 'Persist outputs' block where run.status is set to 'completed':
import json
run.judge_verdict_json = json.dumps(judge_verdict_dict)
```

### Reconstructing RunEnvelope From DB Records

```python
# api/report_helpers.py (new module)
from sqlmodel import Session, select
from api.models import Run, AgentOutput
from protocols.run_envelope import RunEnvelope, AgentOutputEnvelope

def build_envelope_from_db(run: Run, session: Session) -> RunEnvelope:
    outputs_db = session.exec(
        select(AgentOutput).where(AgentOutput.run_id == run.id)
    ).all()
    agent_outputs = [
        AgentOutputEnvelope(
            agent_key=o.agent_key, agent_name=o.agent_key,
            text=o.output_text, model=o.model,
            input_tokens=o.input_tokens, output_tokens=o.output_tokens,
            cost_usd=o.cost_usd,
        )
        for o in outputs_db if o.agent_key != '_synthesis'
    ]
    synthesis_row = next((o for o in outputs_db if o.agent_key == '_synthesis'), None)
    return RunEnvelope(
        protocol_key=run.protocol_key, question=run.question,
        agent_keys=[o.agent_key for o in agent_outputs],
        source='db', status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at or run.started_at,
        result_json={},
        result_summary=synthesis_row.output_text if synthesis_row else '',
        cost={'total_usd': run.cost_usd, 'calls': 0, 'by_model': {}, 'by_agent': {}},
        trace_id=run.trace_id, run_id=run.id,
        agent_outputs=agent_outputs,
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| downloadReport() in RunView.tsx builds Markdown blob client-side | Server-side PDF via WeasyPrint on GET /api/reports/{id}/pdf | Phase 6 | MD export stays as convenience; server PDF is the polished deliverable |
| Raw JudgeVerdict scores rendered as integers in JudgeVerdictCard | Filled-dot ConfidenceIndicator component | Phase 6 | OUT-05 compliance |
| No shareable URL | GET /share/{id} serves read-only styled HTML | Phase 6 | REPT-03 compliance |
| JudgeVerdict emitted only as SSE (not persisted) | judge_verdict_json column on Run table | Phase 6 | Enables PDF endpoint to show confidence score for any past run |

**Deprecated/outdated:**
- `downloadReport()` in RunView.tsx: Keep as fast Markdown export. PDF button (UI-10, Phase 7) calls the new server endpoint instead.

---

## Open Questions

1. **JudgeVerdict Persistence Strategy**
   - What we know: Currently not in DB; only in Langfuse and SSE stream.
   - Recommendation: Add `judge_verdict_json` TEXT column to Run. Drop-recreate orchestrator.db in dev. Alembic in Phase 8.

2. **WeasyPrint on Vercel Lambda**
   - What we know: STATE.md flags as unverified blocker. Vercel Lambda does not include pango/cairo.
   - Recommendation: Phase 6 confirms local functionality and documents system deps. Phase 8 resolves Vercel compatibility. Fallback: Playwright headless PDF if WeasyPrint fails in Lambda.

3. **Shareable URL Path: /share/{id} vs /runs/{id}**
   - What we know: REPT-03 specifies GET /runs/{id} but React Router also owns /runs/:id.
   - Recommendation: Use /share/{id}. The requirement intent is 'a URL a client can open without login' -- /share/{id} satisfies that. Update REPT-03 implementation note.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml or pytest.ini in CE - Multi-Agent Orchestration/ root |
| Quick run command | `pytest tests/test_protocol_report.py -x` |
| Full suite command | `pytest tests/ -m 'not integration' -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OUT-01 | ProtocolReport dataclass has all required fields | unit | `pytest tests/test_protocol_report.py::test_protocol_report_fields -x` | Wave 0 |
| OUT-02 | from_envelope() correctly maps all RunEnvelope fields | unit | `pytest tests/test_protocol_report.py::test_from_envelope -x` | Wave 0 |
| OUT-03 | Browser report view renders all sections | unit | `cd ui && npx vitest run src/__tests__/ProtocolReport.test.tsx` | Wave 0 |
| OUT-04 | Disagreements section has distinct styling | unit | included in ProtocolReport.test.tsx | Wave 0 |
| OUT-05 | Confidence score is visual indicator not raw decimal | unit | pytest test_confidence_label + vitest | Wave 0 |
| OUT-06 | Agent contribution cards render all required fields | unit | included in test_from_envelope | Wave 0 |
| REPT-01 | GET /api/reports/{run_id}/pdf returns 200 application/pdf | unit | `pytest tests/test_reports_api.py::test_pdf_endpoint -x` | Wave 0 |
| REPT-02 | PDF bytes non-empty, content-type correct | smoke | `pytest tests/test_reports_api.py::test_pdf_content_smoke -x` | Wave 0 |
| REPT-03 | GET /share/{run_id} returns 200 HTML without auth | unit | `pytest tests/test_reports_api.py::test_share_url_no_auth -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_protocol_report.py -x`
- **Per wave merge:** `pytest tests/ -m 'not integration' -x`
- **Phase gate:** Full suite green before /gsd:verify-work

### Wave 0 Gaps
- [ ] `tests/test_protocol_report.py` -- covers OUT-01, OUT-02, OUT-05, OUT-06
- [ ] `tests/test_reports_api.py` -- covers REPT-01, REPT-02, REPT-03
- [ ] `ui/src/__tests__/ProtocolReport.test.tsx` -- covers OUT-03, OUT-04
- [ ] WeasyPrint smoke test: `python -c 'import weasyprint; weasyprint.HTML(string="<p>ok</p>").write_pdf()'` -- confirm before 06-02
- [ ] `api/templates/report.html.j2` -- Jinja2 template file (Wave 0 asset)

---

## Sources

### Primary (HIGH confidence)
- `protocols/run_envelope.py` -- full source read; confirmed RunEnvelope fields, extract_agent_outputs covering all 50 protocol shapes
- `api/runner.py` -- full source read; confirmed JudgeVerdict emission, AgentOutput persistence, cost_summary structure; confirmed JudgeVerdict NOT written to Run table
- `api/models.py` -- full source read; confirmed Run table schema (no judge_verdict_json today)
- `api/routers/runs.py` -- full source read; confirmed GET /runs/{id} response shape
- `ui/src/pages/RunView.tsx` -- full source read; confirmed existing rendering, downloadReport(), JudgeVerdictCard raw number display
- `ui/package.json` -- confirmed react-markdown, react-router-dom, tailwindcss, vitest available
- `CE - Multi-Agent Orchestration/venv` -- confirmed Jinja2 3.1.6 installed; WeasyPrint NOT installed

### Secondary (MEDIUM confidence)
- FastAPI Response and HTMLResponse -- standard documented FastAPI patterns
- WeasyPrint HTML(string=html).write_pdf() -- primary documented WeasyPrint API; system lib dependency documented on WeasyPrint official site
- asyncio.to_thread() -- documented Python 3.9+ pattern for sync code in async context

### Tertiary (LOW confidence)
- Vercel Lambda WeasyPrint compatibility -- flagged as unverified in STATE.md; not independently confirmed in this session

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries confirmed in-venv or well-documented; WeasyPrint is the only new install
- Architecture: HIGH -- all data sources confirmed from source code; transform pattern is clear
- Pitfalls: HIGH -- WeasyPrint system lib risk real and documented; JudgeVerdict persistence gap confirmed; routing collision clearly visible

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable stack)
