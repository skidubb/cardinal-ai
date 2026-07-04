# Roadmap: CE-AGENTS

## Milestones

- ✅ **v1.0 Critical Debt Remediation** - Phases 1-3 (shipped 2026-03-09)
- 🚧 **v1.1 Full-Stack Integration** - Phases 4-8 (in progress)
- 📋 **v1.2 Fair Academic Bench** - Phases 9-12 (planned)

---

<details>
<summary>✅ v1.0 Critical Debt Remediation (Phases 1-3) - SHIPPED 2026-03-09</summary>

### Phase 1: Shared Package and Pricing Unification
**Goal**: Create the ce-shared package with verified Anthropic pricing and migrate both cost trackers to use it
**Status**: Complete (3/3 plans, 2026-03-09)
**Requirements**: SHPK-01 through SHPK-03, PRIC-01 through PRIC-08

Plans:
- [x] 01-01: ce-shared package with verified pricing
- [x] 01-02: Agent Builder cost tracker migration to ce-shared
- [x] 01-03: Orchestration cost tracker migrated to ce-shared

### Phase 2: Environment Consolidation
**Goal**: Consolidate all API keys into a single root .env, make all projects load from it deterministically
**Status**: Complete (5/5 plans, 2026-03-09)
**Requirements**: ENVR-01 through ENVR-09

Plans:
- [x] 02-01: ce-shared env module with loader, registry, validation
- [x] 02-02: Consolidated root .env, .env.example, docker-compose.yml interpolation
- [x] 02-03: Migrated all load_dotenv call sites to ce-shared loader
- [x] 02-04: env_check diagnostic CLI with Rich output
- [x] 02-05: Deleted stale .env files, full end-to-end verification passed

### Phase 3: Token Estimation and Documentation
**Goal**: Back-calculate token counts from SDK cost data, add budget guardrails, and document bypassPermissions
**Status**: Complete (4/4 plans, 2026-03-09)
**Requirements**: TOKN-01 through TOKN-06, DOCS-01 through DOCS-02

Plans:
- [x] 03-01: estimate_tokens_from_cost() in ce-shared pricing
- [x] 03-02: Budget guardrails in ProtocolCostTracker
- [x] 03-03: Wired token estimation into production agent path and Langfuse
- [x] 03-04: BYPASS_PERMISSIONS.md and ce-shared README documentation

</details>

---

## v1.1 Full-Stack Integration

**Milestone Goal:** Wire the existing CLI, protocols, API stubs, and React UI into a single deployable product accessible via browser at a cloud URL. A client question goes in; a polished ProtocolReport comes out.

### Phase 4: Agent Provider
**Goal**: Production-mode SdkAgents load reliably in any environment; the API refuses to start if agent imports fail
**Depends on**: Phase 3 (foundation complete)
**Requirements**: AGNT-01, AGNT-02, AGNT-03
**Success Criteria** (what must be TRUE):
  1. API server starts and logs confirmed production mode with no manual path configuration
  2. API server fails immediately with a clear error message if SdkAgent cannot be imported — no silent fallback to research mode
  3. Running a protocol via CLI after the path fix produces the same output as before the change
**Plans**: 1 plan

Plans:
- [x] 04-01: Fix agent provider absolute path and add startup production assertion

### Phase 5: API Wiring
**Goal**: Every protocol is executable from a single HTTP call; run history, agent list, and cost data are retrievable; SSE streams live progress; client disconnect cancels the run
**Depends on**: Phase 4
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, API-07, API-08, API-09, API-10
**Success Criteria** (what must be TRUE):
  1. POST /api/protocols/run with a valid protocol, question, and agent list returns a run ID and executes the protocol
  2. GET /api/runs/{id}/stream delivers SSE stage events while the protocol runs, with X-Accel-Buffering disabled
  3. Closing the browser tab or network connection stops the in-flight orchestrator task and stops burning API credits
  4. GET /api/runs returns a paginated list of past runs with cost, status, and timestamp
  5. POST /api/pipelines/run executes a protocol chain where each protocol's output feeds the next as context
**Plans**: 2 plans

Plans:
- [x] 05-01: Canonical URL routing, SSE headers, trace_id, stream replay, and test infrastructure
- [x] 05-02: Client disconnect cancellation, context var isolation, and pipeline presets

### Phase 6: Structured Output and Reports
**Goal**: Protocol results display as executive-readable ProtocolReports with scannable sections, disagreement highlighting, and confidence indicators; PDF export produces a client-deliverable document
**Depends on**: Phase 5
**Requirements**: OUT-01, OUT-02, OUT-03, OUT-04, OUT-05, OUT-06, REPT-01, REPT-02, REPT-03
**Success Criteria** (what must be TRUE):
  1. Any completed protocol run displays a ProtocolReport with executive summary, key findings, disagreements, and per-agent contribution cards
  2. Agent disagreement sections are visually distinct from consensus sections in the browser view
  3. Confidence score displays as a visual indicator — not a raw decimal number
  4. Clicking "Download PDF" on a run detail page produces a polished document ready to send to a client
  5. Shareable URL for a run (GET /share/{id}) renders the full ProtocolReport without requiring login
**Plans**: 2 plans

Plans:
- [x] 06-01-PLAN.md — ProtocolReport dataclass, from_envelope transform, judge_verdict persistence, DB helpers
- [x] 06-02-PLAN.md — Jinja2 template, PDF endpoint, shareable HTML route, React report component

### Phase 7: Frontend and Auth
**Goal**: The React UI is fully connected to the live API with no mock data; login gate protects all routes; SSE streaming works through auth; CORS is environment-configured
**Depends on**: Phase 6
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, UI-09, UI-10, AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06
**Success Criteria** (what must be TRUE):
  1. Unauthenticated users see the login page; valid credentials grant access to all features
  2. Protocol library loads real protocols from the API, filterable by category, with a curated "greatest hits" section prominently visible
  3. Submitting the execution form starts a protocol run and shows live SSE stage progress in the browser without page reload
  4. Run history page loads real data; clicking a past run shows the full ProtocolReport without re-executing the protocol
  5. PDF download button on the run detail page saves a client-deliverable PDF to disk
**Plans**: 3 plans

Plans:
- [ ] 07-01: JWT auth backend and React auth context with protected routes
- [ ] 07-02: Wire protocol library, execution form, run history, and result view to live API
- [ ] 07-03: Curated protocol collection, pipeline preset selector, and PDF download button

### Phase 8: Deployment
**Goal**: The full stack is accessible at a Vercel URL; one command starts the local development environment; first-time setup requires no detective work
**Depends on**: Phase 7
**Requirements**: INFR-01, INFR-02, INFR-03, INFR-04, INFR-05, INFR-06, INFR-07
**Success Criteria** (what must be TRUE):
  1. `make dev` brings up the full local stack (API, UI, Postgres) with no additional configuration steps
  2. The Vercel deployment URL is accessible from any browser and all features work end-to-end through the cloud proxy
  3. SSE streaming delivers live events in the cloud deployment — verified through Vercel's proxy, not just localhost
  4. A new developer can complete first-time environment setup by following the getting-started doc without asking for help
**Plans**: 2 plans

Plans:
- [ ] 08-01: Multi-stage Dockerfile, docker-compose extension, and Makefile
- [ ] 08-02: Vercel deployment, managed Postgres, and getting-started documentation

---

## v1.2 Fair Academic Bench (planned, not started)

**Milestone Goal:** Give every decisioning family a fair chance in the eval harness. Debate and negotiation protocols currently dominate scores because of structural advantages in the harness (generous token budgets, debate-shaped test questions, generic rubric). Other protocols likely underperform for harness reasons, not protocol reasons. Prove or disprove this by giving every family category-appropriate tokens, questions, and rubrics — then re-run.

**Why this matters:** The adaptive router thesis depends on having real, comparable scores per protocol. Right now the scores are contaminated by the harness. Fixing this is a prerequisite for any protocol-selection learning.

### Phase 9: Token Cap Audit
**Goal**: Every max_tokens site in the orchestration layer is classified as mechanical or reasoning, with reasoning steps raised to 6k minimum and mechanical steps annotated with a justifying comment. The inline eval scorer and judge backends get real rationale headroom.
**Depends on**: v1.1 complete
**Success Criteria**:
  1. `docs/token-cap-audit.md` ledger exists with one row per cap site: file:line, old value, new value, classification, rationale
  2. `protocols/multiagent_evals.py:144` raised from 500 → 4096+ with thinking enabled
  3. `CE - Evals/src/ce_evals/core/judge_backends.py` — Anthropic/OpenAI/Gemini backends raised from 4096 → 8192
  4. Every remaining `max_tokens < 4096` site has an inline comment explaining why it stays small (mechanical step)
  5. Six Hats, Crazy Eights, Cynefin Probe, and other flagged creative/systems protocols have their reasoning steps raised to 6k+
**Plans**: 1 plan

Plans:
- [ ] 09-01: Full cap audit + ledger + per-site changes across 49 protocols

### Phase 10: Decisioning Taxonomy and Test Bank
**Goal**: The 49 non-meta protocols are grouped into 8 decisioning families, each with 3 canonical test questions designed to let that family shine. No more using debate-shaped questions to test creative or systems protocols.
**Depends on**: Phase 9
**Success Criteria**:
  1. 8 decisioning families defined: adversarial, intelligence, forecasting, creative, systems, facilitation, abductive, wicked
  2. `benchmark-questions-v2.json` exists with 24 new questions (3 per family), each tagged with `decisioning_family`
  3. Every protocol in `protocols/agents.py` is mapped to a family in a new `protocols/families.py`
  4. The new questions are demonstrably different in shape from the existing debate-centric Q-series
**Plans**: 1 plan

Plans:
- [ ] 10-01: Family taxonomy + 24 new test questions + protocol-to-family mapping

### Phase 11: Family-Aware Rubrics
**Goal**: The eval judge scores each protocol against dimensions that match its decisioning family. Creative protocols are scored on novelty and recombination, not on stakeholder coverage. Systems protocols are scored on loop identification, not on preference aggregation.
**Depends on**: Phase 10
**Success Criteria**:
  1. 8 YAML rubric files under `CE - Evals/rubrics/{family}.yaml`, each with common dimensions + family-specific dimensions
  2. `CE - Evals/src/ce_evals/core/rubric.py` has a `load_family_rubric(family)` dispatch
  3. `scripts/evaluate.py` accepts `--family` flag and routes to the right rubric
  4. A dry-run against each family loads its rubric without error
**Plans**: 1 plan

Plans:
- [ ] 11-01: 8 family rubrics + rubric loader + eval harness --family flag

### Phase 12: Fair Bench Run and Comparison Report
**Goal**: The academic test bench is run twice (baseline + fair bench) and a public comparison report shows which protocols were harness-handicapped and which are genuinely weaker. This is the evidence that earns the "adaptive router" narrative.
**Depends on**: Phase 11
**Success Criteria**:
  1. Baseline run (current code + scorer fix only) completes against all 49 protocols on the new test bank, persisted to Postgres with Langfuse traces
  2. Fair bench run (cap raises + family rubrics) completes against the same protocols and questions
  3. `CE - Evals/research/fair-bench-apr-2026.md` exists with per-protocol score deltas
  4. At least one previously-underperforming protocol shows a statistically meaningful gain under the fair bench (proof the bench isn't broken)
  5. Protocols that still underperform after fair treatment are explicitly called out as genuinely weaker (not harness artifacts)
**Plans**: 1 plan

Plans:
- [ ] 12-01: Baseline run + fair bench run + comparison report

---

## Progress

**Execution Order:**
4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Shared Package and Pricing Unification | v1.0 | 3/3 | Complete | 2026-03-09 |
| 2. Environment Consolidation | v1.0 | 5/5 | Complete | 2026-03-09 |
| 3. Token Estimation and Documentation | v1.0 | 4/4 | Complete | 2026-03-09 |
| 4. Agent Provider | v1.1 | 1/1 | Complete | 2026-03-10 |
| 5. API Wiring | v1.1 | 2/2 | Complete | 2026-03-10 |
| 6. Structured Output and Reports | v1.1 | 2/2 | Complete | 2026-03-11 |
| 7. Frontend and Auth | v1.1 | 0/3 | Not started | - |
| 8. Deployment | v1.1 | 0/2 | Not started | - |
| 9. Token Cap Audit | v1.2 | 0/1 | Not started | - |
| 10. Decisioning Taxonomy and Test Bank | v1.2 | 0/1 | Not started | - |
| 11. Family-Aware Rubrics | v1.2 | 0/1 | Not started | - |
| 12. Fair Bench Run and Comparison Report | v1.2 | 0/1 | Not started | - |
