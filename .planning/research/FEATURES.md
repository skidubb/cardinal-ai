# Feature Landscape: CE-AGENTS Full-Stack Integration

**Domain:** Multi-agent AI orchestration platform for consulting delivery
**Researched:** 2026-03-10
**Milestone scope:** Wiring CLI + protocols + API + UI into a usable product for real client engagements

---

## Table Stakes

Features users (Scott, client-facing) expect. Missing = product feels incomplete or unusable for client work.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Protocol selection UI | Users need to browse and pick from 52 protocols without knowing their codes | Medium | Library page exists in React; needs real data from API |
| Agent selection / team picker | Every protocol run needs an agent set; @category group syntax must be surfaceable | Medium | Registry endpoint needed; @executive, @cto-team etc. shortcuts are essential UX |
| Execute a protocol from the browser | Core value — question goes in, analysis comes out without touching CLI | High | api/runner.py exists; routers/protocols.py is a stub; SSE wiring is the primary gap |
| Live streaming progress during execution | Protocol runs take 30–120 seconds; silent waiting is unusable | High | SSE infrastructure in api/runner.py exists but is not wired to the UI |
| Structured result display | Output quality is the product's differentiator; raw JSON dump is unacceptable | High | ProtocolReport format needed; see the shared-report-layer todo |
| Run history list | "Show me last week's runs before the Acme meeting" is a real workflow | Medium | ce-db Run table exists; routers/runs.py is a stub |
| Re-open a past run | Recall without re-running; saves cost and time | Low | Result is persisted as result_json in the Run table |
| Cost display per run | Scott tracks client billing and API costs; invisible spend is unacceptable | Low | ProtocolCostTracker already populates; cost is persisted on the Run row |
| Login gate / simple auth | Client URLs cannot be publicly accessible | Medium | JWT + session cookie for SSE; EventSource cannot send auth headers |
| Error messaging | "Run failed" with no detail is worse than a CLI traceback | Low | API must return structured errors; UI must surface them humanely |
| Cloud URL access | Clients need to open a URL, not be screenshared a localhost | High | Deployment target TBD; must be decided before milestone closes |
| One-command local startup | Developer onboarding; Scott must be able to restart without debugging deps | Medium | docker-compose up for Postgres exists; needs to extend to API + UI |

---

## Differentiators

Features that set CE-AGENTS apart from generic AI workflow tools.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| ProtocolReport structured output | Executive-readable format with participants, findings, disagreements, confidence, synthesis | High | Primary output quality differentiator; requires shared report layer |
| Protocol chains as packaged workflows | "Run Cynefin → TRIZ → Popper" as a named engagement workflow | High | api/runner.py pipeline mode exists; UI needs workflow builder or preset selector |
| Curated "greatest hits" collection | 52 protocols is overwhelming; surface 8–10 best for common consulting questions | Low | Static curation: tag protocols in manifest or JSON config |
| Agent disagreement highlighting | Show where agents diverged — this is the content clients pay for | Medium | Synthesis content exists; UI rendering must call out dissent sections |
| Confidence level display | Signal: "agents reached strong consensus" vs "this is speculative" | Medium | Quality judge already scores runs; surface as visual signal |
| Per-agent contribution view | Show what each agent contributed — transparency into multi-agent process | Medium | AgentOutput rows are persisted; run view can render per-agent cards |
| Protocol chain output threading | Chain results feed forward (TRIZ output enriches Popper question) | High | Protocol chaining quality rule from MEMORY.md |
| Cost estimate before run | "This will cost ~$0.40" before submitting | Low | Token estimation from Phase 3 complete; needs /estimate endpoint |
| Export to polished PDF/doc | Consulting deliverable is a report, not a browser session | High | No existing export infrastructure; WeasyPrint recommended |
| Shareable run URL | Send a client a URL to a specific run's results (read-only) | Low | Run UUID already persisted; needs public-accessible route with auth |
| Protocol diagram view | Show protocol's multi-stage flow visually before running | Medium | ProtocolDiagram page exists; needs protocol metadata via API |
| LLM trace link (Langfuse) | Link from a run to its Langfuse trace for deep debugging | Low | langfuse_trace_id stored on Run row; render as link |

---

## Anti-Features

Things to deliberately NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Custom protocol builder UI | Protocols are complex multi-stage Python; a drag-and-drop builder produces inferior output | Keep protocols as code; surface metadata via API for display only |
| Real-time collaborative runs | SSE is single-subscriber per run; multi-user presence is a separate product | Single-user operation; share results via URL after completion |
| Multi-user RBAC | Scott is sole operator; client access is read-only URL sharing | Simple JWT auth with single admin credential |
| Mobile / responsive UI | Client meetings use laptop browser; mobile adds complexity with zero benefit | Desktop-first; min-width: 1024px acceptable |
| CE-Evals integration into UI | Evaluation is a separate research workflow | Keep CE-Evals as CLI/script; link to Langfuse for quality scores |
| Self-hosted Langfuse | Cloud Langfuse already working; self-hosting adds ops overhead | Continue using Langfuse Cloud |
| QuickBooks / billing integration | No consulting engagement needs automated invoicing from protocol runs | Remove stub; billing handled outside platform |
| Real-time token streaming | Protocols are multi-stage batch operations, not chat | Stream stage-level events, not individual tokens |
| Agent builder UI | SdkAgent configuration is complex Python with MCP server wiring | Agents configured in code; UI displays registry but doesn't edit |

---

## Feature Dependencies

```
Simple auth (login gate)
  └──► SSE streaming (EventSource needs session cookie after JWT verify)
  └──► Shareable run URL (read-only route needs auth scope)
  └──► Cloud deployment (auth must work at cloud URL, not just localhost)

Protocol execution endpoint (routers/protocols.py wired)
  └──► Live streaming progress (SSE drains event queue from api/runner.py)
  └──► Run history (persists Run row; history reads those rows)
  └──► Cost display (cost persisted on Run row after execution)
  └──► ProtocolReport output (structured result requires run to complete)

ProtocolReport structured format (shared report layer)
  └──► Agent disagreement highlighting (needs disagreements field)
  └──► Confidence display (needs confidence/quality_score field)
  └──► Per-agent contribution view (needs agent_contributions field)
  └──► PDF/doc export (export renders ProtocolReport, not raw result_json)
  └──► Shareable run URL (displays ProtocolReport at the URL)

Protocol chain endpoint (pipelines router wired)
  └──► Protocol chain output threading (chain must pass forward)
  └──► Packaged workflow presets (named chains referencing protocol sequence)

Cloud deployment
  └──► Shareable run URL (URL must be accessible outside localhost)
  └──► Simple auth (must work at cloud domain, CORS updated)
```

---

## MVP Recommendation

**Must-have (blocks client use):**
1. Protocol execution from browser with live progress
2. ProtocolReport structured output format
3. Run history with re-open
4. Simple auth login gate
5. Cloud deployment

**Should-have (first sprint after MVP):**
6. PDF/doc export
7. Protocol chains as packaged workflows
8. Curated protocol collection

**Defer with confidence:**
- Cost estimate pre-run (a few hours of work, not blocking)
- Protocol diagram view (page exists; metadata exposure is nice-to-have)
- Agent builder UI (explicitly out of scope)

---
*Feature research for: CE-AGENTS full-stack integration*
*Researched: 2026-03-10*
