# CE-AGENTS: Full Stack Integration

## What This Is

A multi-agent AI platform for Cardinal Element's growth architecture consulting. 52 coordination protocols orchestrate 56+ AI agents (executives, specialists, external perspectives) to produce structured strategic analysis for client engagements. This milestone wires the existing CLI, protocols, API, and UI into a single deployable product that Scott can use on real client work.

## Core Value

A client question goes in, a structured multi-agent analysis comes out — viewable in a browser, exportable as a polished report, powered by production agents with tools and memory.

## Requirements

### Validated

<!-- Shipped and confirmed valuable — from completed Critical Debt Remediation milestone. -->

- ✓ Shared pricing package (ce-shared) with verified Anthropic rates — Phase 1
- ✓ Both cost trackers (Agent Builder + Orchestration) use ce-shared pricing — Phase 1
- ✓ Single root .env with deterministic loading across all projects — Phase 2
- ✓ Environment validation CLI (ce-shared env_check) — Phase 2
- ✓ Token estimation from SDK cost data with Langfuse integration — Phase 3
- ✓ Budget guardrails (cost ceiling warnings) — Phase 3
- ✓ bypassPermissions design decision documented — Phase 3
- ✓ 7 executive agents with tools, MCP servers, memory (Agent Builder) — existing
- ✓ 52 coordination protocols with CLI entry points — existing
- ✓ 56-agent registry with @category group syntax — existing
- ✓ Dual agent mode (production/research) with AgentBridge adapter — existing
- ✓ Langfuse tracing on all protocols — existing
- ✓ Postgres persistence via ce-db — existing
- ✓ FastAPI server structure with 7 routers — existing
- ✓ React UI with pages for all major features — existing
- ✓ CI pipeline (lint, test, UI build) — existing

### Active

<!-- Current scope — wiring everything together for real client use. -->

- [ ] API endpoints execute protocol orchestrators and return structured results
- [ ] SSE streaming delivers live protocol progress to the UI
- [ ] UI calls API to run protocols, display results, and show run history
- [ ] Protocol chains execute as packaged workflows (e.g., Cynefin → TRIZ → Popper)
- [ ] Curated "greatest hits" protocol collection surfaced in UI alongside full library
- [ ] Structured ProtocolReport output format (executive summary, disagreements, confidence, agent contributions)
- [ ] Report export to PDF/document format for client delivery
- [ ] Browser-viewable report with scannable sections and deep-dive capability
- [ ] Production mode as default agent mode with clear errors if Agent Builder unavailable
- [ ] Simple authentication (login gate for sharing URLs with clients)
- [ ] Cloud deployment (API + UI + Postgres accessible via URL)
- [ ] One-command local startup (docker-compose or Makefile for full stack)
- [ ] Setup wizard or script for first-time environment configuration
- [ ] Getting-started documentation for new developer/user onboarding

### Out of Scope

- Multi-user role-based access control — simple auth only for this milestone
- Real-time collaborative protocol runs — single-user operation
- Mobile app or responsive mobile UI — desktop browser only
- QuickBooks integration — stub exists, not needed for client engagements
- Custom protocol builder UI — protocols are code-defined
- Self-hosted Langfuse — using Langfuse Cloud
- CE-Evals integration into UI — evaluation is a separate workflow for now

## Context

**Brownfield project.** Three previously separate repos (ce-c-suite, coordination-lab, CE-Evals) consolidated into monorepo. Critical Debt Remediation milestone (3 phases, 12 plans) completed 2026-03-09 — shared pricing, env consolidation, token estimation all done. Foundation is solid but pieces aren't connected.

**Existing infrastructure:** CLI works end-to-end. Protocols work via CLI. API server starts but endpoints are stubs. UI builds and dev server runs but doesn't call backend. Docker Compose brings up Postgres + Metabase. CI passes.

**Client workflow:** Scott uses this for CE consulting engagements — prep before client meetings (run protocols, bring structured output), show UI live in meetings (speed secondary to output quality), and async delivery (run protocols, export polished report). Output quality is the differentiator, not speed.

**Previous milestone decisions:** Opus 4.6 = $5/$25 pricing (not legacy $15/$75). Unknown models default to Opus-tier as conservative fallback. Cost ceiling is warn-only, never halts.

## Constraints

- **Tech stack**: Python 3.11+ backend, React 19 + TypeScript frontend, FastAPI, PostgreSQL 16 — all established
- **Agent mode**: Production mode (full SdkAgent with tools/memory) required for client work — research mode insufficient
- **Model policy**: claude-opus-4-6 for executives, claude-haiku-4-5-20251001 for mechanical steps — non-negotiable for quality
- **Deployment**: Must be cloud-accessible (not just localhost) for client URL sharing
- **Auth**: Simple auth sufficient — no enterprise SSO or RBAC needed yet
- **Observability**: Langfuse Cloud tracing must continue working through the integration

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Production mode as default | Client engagements need full agent capabilities (tools, memory, MCP) | — Pending |
| Cloud deploy target | Clients need URL access, not screen-share of localhost | — Pending |
| Simple auth over no auth | URL sharing with clients requires basic access control | — Pending |
| PDF/doc export over slides | Client deliverables are reports, not presentations | — Pending |
| All 52 protocols available | Curated set for quick access, full library for flexibility | — Pending |

---
*Last updated: 2026-03-10 after initialization*
