# CE-AGENTS Directory Structure

Purpose: Document the directory layout, key file locations, and naming conventions for the CE-AGENTS monorepo.

---

## Top-Level Layout

```
CE - AGENTS/
|-- CE - Agent Builder/          # Agent factory: 80+ agents with tools + MCP servers
|-- CE - Multi-Agent Orchestration/  # 53 protocols + FastAPI + React UI
|-- CE - Evals/                  # LLM-as-judge evaluation framework
|-- ce-db/                       # Shared database layer (SQLAlchemy + Alembic)
|-- n8n Workflows/               # Automation workflow exports
|-- Shared/                      # Cross-project scripts
|-- Scripts/                     # Utility scripts
|-- docker-compose.yml           # Postgres + Metabase
|-- Makefile                     # Monorepo-level commands
|-- CLAUDE.md                    # Project instructions for Claude Code
|-- README.md                    # Project overview
|-- constraints.txt              # Shared Python constraints
```

---

## CE - Agent Builder

The agent factory. Builds and configures all AI agents used across the platform.

```
CE - Agent Builder/
|-- src/csuite/
|   |-- __init__.py
|   |-- main.py                  # CLI entry point (Click). Commands: ceo, cfo, synthesize, debate, interactive, report
|   |-- config.py                # Settings (pydantic-settings from .env) + AGENT_CONFIGS per role
|   |-- session.py               # Session/Message Pydantic models + SessionManager (JSON persistence)
|   |-- orchestrator.py          # Multi-agent synthesis orchestrator
|   |-- debate.py                # Multi-round debate orchestrator
|   |-- audit.py                 # Growth Strategy Audit pipeline (7-agent sequential)
|   |
|   |-- agents/
|   |   |-- __init__.py          # Re-exports all 7 agent classes
|   |   |-- base.py              # BaseAgent ABC: session management, tool loop, cost tracking, memory
|   |   |-- sdk_agent.py         # SdkAgent: Claude Agent SDK backend with MCP tools (80+ roles)
|   |   |-- factory.py           # create_agent() -- routes to BaseAgent or SdkAgent
|   |   |-- mcp_config.py        # Per-role MCP server mappings
|   |   |-- ceo.py               # CEOAgent(BaseAgent) -- ROLE="ceo"
|   |   |-- cfo.py               # CFOAgent(BaseAgent) -- ROLE="cfo"
|   |   |-- cto.py               # CTOAgent(BaseAgent) -- ROLE="cto"
|   |   |-- cmo.py               # CMOAgent(BaseAgent) -- ROLE="cmo"
|   |   |-- coo.py               # COOAgent(BaseAgent) -- ROLE="coo"
|   |   |-- cpo.py               # CPOAgent(BaseAgent) -- ROLE="cpo"
|   |   |-- cro.py               # CROAgent(BaseAgent) -- ROLE="cro"
|   |
|   |-- prompts/
|   |   |-- __init__.py          # Re-exports all prompt constants
|   |   |-- ceo_prompt.py        # CEO_SYSTEM_PROMPT
|   |   |-- cfo_prompt.py        # CFO_SYSTEM_PROMPT (industry frameworks, KPIs)
|   |   |-- cto_prompt.py        # CTO_SYSTEM_PROMPT
|   |   |-- cmo_prompt.py        # CMO_SYSTEM_PROMPT
|   |   |-- coo_prompt.py        # COO_SYSTEM_PROMPT
|   |   |-- cpo_prompt.py        # CPO_SYSTEM_PROMPT
|   |   |-- cro_prompt.py        # CRO_SYSTEM_PROMPT
|   |   |-- sub_agents.py        # 40+ sub-agent prompts (CEO team, CFO team, GTM, etc.)
|   |   |-- walk_agents.py       # 14 Walk protocol cognitive lens prompts
|   |   |-- debate_prompt.py     # Debate-specific prompts
|   |   |-- kb_instructions.py   # KB_INSTRUCTIONS: Pinecone read/write guidance for all agents
|   |   |-- airport_*.py         # Airport 5G simulation agent prompts (6 files)
|   |
|   |-- tools/
|   |   |-- schemas.py           # Anthropic tool definitions (input_schema format)
|   |   |-- registry.py          # Tool registry: role -> allowed tools mapping, async dispatch
|   |   |-- cost_tracker.py      # API cost tracking (per-query, per-session, per-agent)
|   |   |-- resilience.py        # Retry with backoff, TTL cache, circuit breaker
|   |   |-- pinecone_kb.py       # Pinecone knowledge base queries
|   |   |-- web_search.py        # Brave Search API + URL fetching
|   |   |-- sec_edgar.py         # SEC EDGAR API for company filings
|   |   |-- census_api.py        # US Census Bureau API
|   |   |-- bls_api.py           # Bureau of Labor Statistics API
|   |   |-- github_api.py        # GitHub API integration
|   |   |-- notion_api.py        # Notion API (search, database, page creation)
|   |   |-- image_gen.py         # OpenAI GPT Image 1 + Gemini Imagen 3
|   |   |-- pricing_calculator.py # Pricing model calculations
|   |   |-- report_generator.py  # Prospect research brief export (MD + PDF)
|   |   |-- qa_protocol.py       # QA protocol tooling
|   |   |-- quickbooks_mcp.py    # QuickBooks stub (not functional)
|   |
|   |-- memory/
|   |   |-- store.py             # Pinecone-backed semantic memory (integrated inference)
|   |   |-- extractor.py         # Memory extraction from conversations
|   |   |-- provider.py          # Memory provider interface
|   |
|   |-- storage/
|   |   |-- duckdb_store.py      # DuckDB-backed storage (experience logs, preferences, sessions)
|   |   |-- provider.py          # Storage provider interface
|   |
|   |-- learning/
|   |   |-- experience_log.py    # Experience logging for agent learning
|   |   |-- feedback_loop.py     # Closed-loop self-eval + Pinecone score storage
|   |   |-- preferences.py       # User preference tracking
|   |
|   |-- events/
|   |   |-- strategy_meeting.py  # Strategy meeting orchestration
|   |   |-- sprint.py            # Sprint planning events
|   |   |-- board_meeting.py     # Board meeting simulation
|   |   |-- notion_writer.py     # Write event outputs to Notion
|   |
|   |-- evaluation/
|   |   |-- benchmark.py         # Benchmark runner
|   |   |-- judge.py             # Judge implementation
|   |   |-- report.py            # Evaluation report generation
|   |
|   |-- coordination/
|   |   |-- constraints.py       # Constraint negotiation models
|   |
|   |-- formatters/
|   |   |-- audit_formatter.py   # Audit output formatting
|   |   |-- dual_output.py       # Dual output (console + file)
|   |
|   |-- tracing/
|   |   |-- graph.py             # Causal graph DAG
|   |
|   |-- __init__.py
|
|-- mcp_servers/                 # 3 custom MCP servers (stdio)
|   |-- sec_edgar_server.py
|   |-- pricing_calculator_server.py
|   |-- github_intel_server.py
|
|-- demo/
|   |-- app.py                   # Streamlit demo (prospect research, ICP scoring, agent queries)
|   |-- demo_data.py             # Pre-cached data for ODSC demo mode
|
|-- tests/                       # pytest tests (mark integration for real API calls)
|-- pyproject.toml               # hatchling build system
|-- .claude/CLAUDE.md            # Detailed project instructions
```

### Key Files

| File | Why It Matters |
|------|---------------|
| `src/csuite/agents/sdk_agent.py` | The production agent implementation. 80+ roles with MCP tools. |
| `src/csuite/agents/factory.py` | Agent creation routing -- determines BaseAgent vs SdkAgent |
| `src/csuite/agents/base.py` | Legacy agent with full tool loop, session, memory, learning |
| `src/csuite/main.py` | CLI entry point -- all user-facing commands |
| `src/csuite/config.py` | Settings singleton from `.env` + per-role agent configs |
| `src/csuite/tools/registry.py` | Maps agent roles to allowed tools, dispatches calls |
| `src/csuite/prompts/sub_agents.py` | All 40+ sub-agent system prompts in one file |

---

## CE - Multi-Agent Orchestration

The protocol engine. 53 coordination protocols + FastAPI backend + React UI.

```
CE - Multi-Agent Orchestration/
|-- protocols/
|   |-- __init__.py
|   |-- agents.py                # Master agent registry: 56 agents, 15 categories, @group syntax
|   |-- agent_provider.py        # AgentBridge adapter: wraps SdkAgent for protocol compatibility
|   |-- llm.py                   # LLM dispatch: agent_complete(), llm_complete(), retry, JSON parsing
|   |-- config.py                # Model config: THINKING_MODEL, ORCHESTRATION_MODEL, cognitive tiers
|   |-- cost_tracker.py          # ProtocolCostTracker: per-call cost tracking by model and agent
|   |-- langfuse_tracing.py      # @trace_protocol decorator, record_generation(), span management
|   |-- persistence.py           # persist_run() -- writes Run + AgentOutput to Postgres via ce-db
|   |-- run_envelope.py          # RunEnvelope: standardized result container for all protocols
|   |-- synthesis.py             # SynthesisEngine: shared synthesis logic used by many protocols
|   |-- tracing.py               # make_client() -- creates traced AsyncAnthropic client
|   |-- blackboard.py            # Blackboard pattern for shared agent state
|   |-- judge.py                 # QualityJudge: scores synthesis against agent outputs
|   |-- multiagent_evals.py      # Multi-agent evaluation utilities
|   |-- orchestrator_loop.py     # Generic orchestrator loop utilities
|   |-- triggers.py              # Protocol trigger/routing logic
|   |
|   |-- p0a_reasoning_router/    # Meta: routes questions to optimal protocol
|   |-- p0b_skip_gate/           # Meta: determines if multi-agent is needed
|   |-- p0c_tiered_escalation/   # Meta: escalates complexity tier
|   |-- p03_parallel_synthesis/  # Baseline: parallel agent query + synthesis
|   |-- p04_multi_round_debate/  # Baseline: N-round debate with position evolution
|   |-- p05_constraint_negotiation/ # Baseline: constraint extraction + negotiation
|   |-- p06_triz/                # TRIZ Inversion: failure -> solution
|   |-- p07_wicked_questions/    # Wicked Questions: paradox identification
|   |-- p08_min_specs/           # Min Specs: minimal viable specification
|   |-- p09_troika_consulting/   # Troika: presenter-consultant-observer
|   |-- p10_heard_seen_respected/ # HSR: perspective validation
|   |-- p11_discovery_action_dialogue/ # DAD: discovery -> action
|   |-- p12_twenty_five_ten/     # 25/10: crowdsourced idea ranking
|   |-- p13_ecocycle_planning/   # Ecocycle: portfolio lifecycle mapping
|   |-- p14_one_two_four_all/    # 1-2-4-All: progressive group synthesis
|   |-- p15_what_so_what_now_what/ # WSW: observation -> insight -> action
|   |-- p16_ach/                 # Analysis of Competing Hypotheses
|   |-- p17_red_blue_white/      # Red/Blue/White Team analysis
|   |-- p18_delphi_method/       # Delphi: iterative expert consensus
|   |-- p19_vickrey_auction/     # Vickrey Auction: sealed-bid prioritization
|   |-- p20_borda_count/         # Borda Count: ranked preference aggregation
|   |-- p21_interests_negotiation/ # Interests-Based Negotiation
|   |-- p22_sequential_pipeline/ # Sequential Pipeline: staged processing
|   |-- p23_cynefin_probe/       # Cynefin: domain-aware probe-sense-respond
|   |-- p24_causal_loop_mapping/ # Causal Loop: feedback system mapping
|   |-- p25_system_archetype_detection/ # System Archetypes: pattern detection
|   |-- p26_crazy_eights/        # Crazy Eights: rapid ideation
|   |-- p27_affinity_mapping/    # Affinity Mapping: cluster analysis
|   |-- p28_six_hats/            # Six Thinking Hats
|   |-- p29_pmi_enumeration/     # PMI: Plus-Minus-Interesting
|   |-- p30_llull_combinatorial/ # Llull: combinatorial analysis
|   |-- p31_wittgenstein_language_game/ # Language game analysis
|   |-- p32_tetlock_forecast/    # Tetlock: superforecasting
|   |-- p33_evaporation_cloud/   # TOC Evaporation Cloud
|   |-- p34_current_reality_tree/ # TOC Current Reality Tree
|   |-- p35_satisficing/         # Satisficing: bounded rationality
|   |-- p36_peirce_abduction/    # Peirce: abductive reasoning
|   |-- p37_hegel_sublation/     # Hegel: thesis-antithesis-synthesis
|   |-- p38_klein_premortem/     # Klein: premortem analysis
|   |-- p39_popper_falsification/ # Popper: falsification testing
|   |-- p40_boyd_ooda/           # Boyd OODA: observe-orient-decide-act
|   |-- p41_duke_decision_quality/ # Duke: decision quality framework
|   |-- p42_aristotle_square/    # Aristotle: square of opposition
|   |-- p43_leibniz_audit/       # Leibniz: formal audit
|   |-- p44_kant_pre_router/     # Kant: pre-routing evaluation
|   |-- p45_whitehead_weights/   # Whitehead: meta-protocol weights
|   |-- p46_incubation/          # Incubation: delayed insight
|   |-- p47_polya_lookback/      # Polya: problem-solving lookback
|   |-- p48_black_swan_detection/ # Black Swan: tail risk identification
|   |-- p49_walk_base/           # Walk: base cognitive exploration
|   |-- p50_tournament_walk/     # Walk: tournament selection variant
|   |-- p51_wildcard_walk/       # Walk: wildcard injection variant
|   |-- p52_drift_return_walk/   # Walk: drift-return variant
|   |-- walk_shared/             # Shared Walk protocol agents and utilities
|   |-- airport_5g_pipeline/     # Domain-specific: airport 5G simulation
|
|-- api/
|   |-- __init__.py
|   |-- server.py                # FastAPI app entry point
|   |-- runner.py                # Protocol execution engine (SSE streaming, cost tracking, judging)
|   |-- database.py              # SQLite database for API-local state
|   |-- models.py                # SQLModel definitions (Run, AgentOutput, RunStep, Agent, Pipeline)
|   |-- manifest.py              # Protocol manifest generator
|   |-- tool_registry.py         # API-level tool registry
|   |-- tool_executor.py         # Tool execution with timeout and error handling
|   |-- import_rich_agents.py    # Import Agent Builder agents into API DB
|   |-- routers/
|   |   |-- protocols.py         # Protocol listing + execution endpoints
|   |   |-- runs.py              # Run history + SSE streaming endpoints
|   |   |-- agents.py            # Agent CRUD + tools endpoints
|   |   |-- teams.py             # Team management endpoints
|   |   |-- pipelines.py         # Multi-protocol pipeline endpoints
|   |   |-- knowledge.py         # Knowledge base endpoints
|   |   |-- integrations.py      # External service integration endpoints
|
|-- ui/                          # React frontend (Vite + TypeScript)
|   |-- src/
|   |   |-- App.tsx              # Root app with routing
|   |   |-- main.tsx             # Entry point
|   |   |-- api.ts               # API client
|   |   |-- types.ts             # TypeScript type definitions
|   |   |-- pages/
|   |   |   |-- Dashboard.tsx    # Overview dashboard
|   |   |   |-- ProtocolLibrary.tsx # Browse and select protocols
|   |   |   |-- RunView.tsx      # Single run detail with SSE updates
|   |   |   |-- RunHistory.tsx   # Historical runs list
|   |   |   |-- AgentRegistry.tsx # View and manage agents
|   |   |   |-- AgentEditor.tsx  # Edit agent configuration
|   |   |   |-- Pipelines.tsx    # Create and run multi-protocol pipelines
|   |   |   |-- Teams.tsx        # Team management
|   |   |   |-- KnowledgeExplorer.tsx # Knowledge base browser
|   |   |   |-- ToolsHub.tsx     # Tool registry viewer
|   |   |   |-- Settings.tsx     # Application settings
|   |   |   |-- ProtocolDiagram.tsx # Protocol flow visualization
|   |   |-- components/          # Reusable UI components
|   |   |-- hooks/               # Custom React hooks
|   |   |-- stores/              # State management
|   |   |-- assets/              # Static assets
|
|-- scripts/
|   |-- evaluate.py              # Evaluation harness runner
|   |-- run_batch.py             # Batch protocol execution
|   |-- run_chain.py             # Protocol chaining
|   |-- run_pair.py              # Pairwise protocol comparison
|   |-- judge.py                 # Standalone judging script
|   |-- report.py                # Report generation
|   |-- emergence.py             # Emergence detection analysis
|   |-- emergence_report.py      # Emergence report generation
|   |-- emergence_certificate.py # Emergence certification
|   |-- emergence_prompts.py     # Prompts for emergence analysis
|   |-- pairs_config.py          # Pairwise comparison config
|   |-- ingest_papers.py         # Research paper ingestion
|   |-- upload_benchmark_dataset.py # Upload benchmark data
|   |-- run_batch_p26_p48.py     # Batch runner for specific protocols
|
|-- tests/
|   |-- test_orchestrator_smoke.py  # Protocol smoke tests
|   |-- test_protocols_api.py       # API endpoint tests
|   |-- test_runs_api.py            # Run endpoint tests
|   |-- test_manifest.py            # Manifest tests
|   |-- test_walk_*.py              # Walk protocol tests (5 files)
|   |-- test_integration_live.py    # Live integration tests
|   |-- test_blackboard_smoke.py    # Blackboard pattern tests
|   |-- test_llm_no_tools.py        # LLM without tools tests
|   |-- test_output_correctness.py  # Output validation tests
|   |-- test_run_envelope.py        # Run envelope tests
|
|-- protocol-diagrams/           # Mermaid diagrams for protocols
|-- smoke-tests/                 # Saved protocol outputs for regression
|-- output/                      # Protocol run output files
|-- benchmark-questions.json     # 34 benchmark questions across 8 problem types
|-- CLAUDE.md                    # Project instructions
|-- requirements.txt             # Python dependencies
```

### Key Files

| File | Why It Matters |
|------|---------------|
| `protocols/agents.py` | Master agent registry. 56 agents, 15 categories, @group syntax. |
| `protocols/llm.py` | All LLM calls route through here. Agent detection, LiteLLM routing, retry, tool loop. |
| `protocols/config.py` | Model configuration. Change one line to switch models across all protocols. |
| `protocols/agent_provider.py` | The bridge between Agent Builder and Orchestration. AgentBridge adapter. |
| `api/runner.py` | Core execution engine. Dynamic protocol loading, SSE streaming, cost tracking. |
| `api/server.py` | FastAPI app with all routers registered. |

---

## CE - Evals

LLM-as-judge evaluation framework. Library-only -- imported programmatically.

```
CE - Evals/
|-- src/ce_evals/
|   |-- __init__.py
|   |-- config.py                # Settings (judge_models, API keys)
|   |-- core/
|   |   |-- __init__.py
|   |   |-- judge.py             # BlindJudge: anonymize, evaluate, aggregate across judge models
|   |   |-- judge_backends.py    # Claude, GPT-4, Gemini judge backends
|   |   |-- models.py            # CandidateResult, JudgeResult, EvalSuite (Pydantic models)
|   |   |-- rubric.py            # Rubric: YAML-defined scoring dimensions + judge prompt builder
|   |   |-- runner.py            # EvalRunner: candidates x questions -> judge -> persist
|   |   |-- cost.py              # Cost calculation utilities
|   |-- protocols/
|   |   |-- __init__.py
|   |   |-- blind.py             # anonymize() and strip_metadata() for blind evaluation
|   |-- report/
|   |   |-- __init__.py
|   |   |-- markdown.py          # Markdown report generator
|
|-- examples/
|   |-- run_protocol_eval.py     # Example: evaluate protocol outputs
|   |-- regenerate_report.py     # Example: regenerate report from saved data
|   |-- rerun_failed.py          # Example: rerun failed evaluations
|
|-- tests/
|   |-- test_judge_pipeline.py   # End-to-end judge pipeline tests
|   |-- test_rubric.py           # Rubric loading and prompt building tests
|   |-- test_blind.py            # Anonymization tests
|   |-- test_models.py           # Data model tests
|   |-- test_report.py           # Report generation tests
|   |-- test_cost.py             # Cost calculation tests
|
|-- pyproject.toml               # setuptools build system
```

### Key Files

| File | Why It Matters |
|------|---------------|
| `src/ce_evals/core/judge.py` | BlindJudge: multi-model blind evaluation with Borda aggregation |
| `src/ce_evals/core/runner.py` | EvalRunner: orchestrates full evaluation pipeline with Postgres persistence |
| `src/ce_evals/core/rubric.py` | Rubric: YAML-driven scoring dimensions, builds judge prompts |
| `src/ce_evals/core/models.py` | Core data models: CandidateResult, JudgeResult, EvalSuite |

---

## ce-db

Shared database layer used by Multi-Agent Orchestration and Evals.

```
ce-db/
|-- src/ce_db/
|   |-- __init__.py              # Public API: exports all models + session utilities
|   |-- engine.py                # SQLAlchemy async engine (asyncpg)
|   |-- session.py               # get_session() async context manager
|   |-- models/
|   |   |-- __init__.py          # Re-exports all models
|   |   |-- core.py              # Base declarative class + Agent model
|   |   |-- runs.py              # Run + AgentOutput models
|   |   |-- evals.py             # EvalRun + EvalSample + EvalRegression models
|
|-- alembic/
|   |-- env.py                   # Alembic environment config
|   |-- versions/
|   |   |-- 001_initial_schema.py    # Initial tables: agents, runs, agent_outputs
|   |   |-- 002_eval_economics_tables.py # eval_runs, eval_samples, eval_regressions
|
|-- alembic.ini                  # Alembic config
|-- pyproject.toml               # Build config
```

---

## n8n Workflows

```
n8n Workflows/
|-- n8n-workflows/               # Exported workflow JSON files
|-- p17-red-blue-white.json      # Protocol-specific workflow
|-- p22-sequential-pipeline.json # Protocol-specific workflow
```

---

## Naming Conventions

### Protocol Naming
- Directory: `p{NN}_{descriptor}` (e.g., `p06_triz`, `p38_klein_premortem`)
- Meta protocols: `p0{a|b|c}_{name}` (e.g., `p0a_reasoning_router`)
- Walk protocols: `p{49-52}_*_walk`
- Special: `airport_5g_pipeline` (domain-specific, no p-number)

### Agent Keys
- Kebab-case: `ceo`, `cfo-pricing-strategist`, `gtm-vp-sales`, `walk-framer`
- Executive: single word (`ceo`, `cfo`, `cto`, `cmo`, `coo`, `cpo`, `cro`)
- Sub-agent: `{executive}-{specialty}` (e.g., `cto-ml-engineer`)
- GTM: `gtm-{role}` (e.g., `gtm-sdr-agent`, `gtm-deal-desk`)
- Walk: `walk-{lens}` (e.g., `walk-analogy`, `walk-adversarial`)
- External: `{type}-{perspective}` (e.g., `vc-app-investor`)

### File Naming in Protocols
- `orchestrator.py` -- always contains `class *Orchestrator`
- `prompts.py` -- always contains uppercase string constants (e.g., `FAILURE_GENERATION_PROMPT`)
- `run.py` -- always the CLI entry point with argparse
- `protocol_def.py` -- protocol metadata (where present)

### Model Constants
- `THINKING_MODEL` = `claude-opus-4-6`
- `ORCHESTRATION_MODEL` = `claude-haiku-4-5-20251001`
- `BALANCED_MODEL` = `claude-sonnet-4-6`

### Python Package Names
- `csuite` -- Agent Builder package
- `ce_evals` -- Evals package
- `ce_db` -- Database package
- `protocols` -- Orchestration protocols (not a pip package, imported via path)

---

## Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| `.env` | Each sub-project root | Environment variables (API keys, model config) |
| `pyproject.toml` | Agent Builder, Evals, ce-db | Build system, dependencies, tool config |
| `requirements.txt` | Multi-Agent Orchestration | Python dependencies |
| `docker-compose.yml` | Monorepo root | Postgres + Metabase services |
| `alembic.ini` | ce-db | Database migration config |
| `CLAUDE.md` | Monorepo root + each sub-project | Claude Code instructions |

---

## Runtime Directories (gitignored)

| Directory | Location | Contents |
|-----------|----------|----------|
| `data/` | Agent Builder | DuckDB database (agent_memory.duckdb) |
| `sessions/` | Agent Builder | Session JSON files by agent role |
| `venv/` / `.venv/` | Each sub-project | Python virtual environments |
| `smoke-tests/` | Multi-Agent Orchestration | Saved protocol outputs |
| `output/` | Multi-Agent Orchestration | Protocol run output files |
| `ui/node_modules/` | Multi-Agent Orchestration | Node.js dependencies |
