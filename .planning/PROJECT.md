# CE-AGENTS Critical Debt Remediation

## What This Is

A focused remediation project to resolve the 4 critical issues identified in the CE-AGENTS monorepo codebase audit. Addresses secrets management, cost tracking accuracy, and pricing consistency across Agent Builder and Multi-Agent Orchestration projects.

## Core Value

Cost tracking and pricing data across the monorepo must be accurate and consistent — every dollar reported should reflect reality.

## Requirements

### Validated

- ✓ Monorepo structure with Agent Builder, Multi-Agent Orchestration, Evals — existing
- ✓ SDK Agent with tool execution and MCP server access — existing
- ✓ Cost tracking in both Agent Builder and Orchestration — existing (but inaccurate)
- ✓ Protocol execution with Langfuse tracing — existing

### Active

- [ ] Single centralized `.env` at repo root, all projects reference it
- [ ] Duplicate keys across project `.env` files eliminated
- [ ] SDK Agent permission bypass documented as intentional design decision
- [ ] SDK Agent back-calculates token counts from `total_cost_usd` using pricing table
- [ ] Downstream systems receive estimated token counts instead of 0
- [ ] Both cost trackers use identical, verified current Anthropic pricing
- [ ] Single shared pricing source of truth (one file, imported by both projects)

### Out of Scope

- Secrets manager integration (1Password, Vault, etc.) — centralize first, encrypt later
- Removing `bypassPermissions` — intentional for automation speed, document the risk
- Important/Minor concerns from CONCERNS.md — separate project
- New features or protocol additions — this is debt-only

## Context

CONCERNS.md was generated during a codebase mapping exercise on 2026-03-09. The monorepo has three sub-projects each with their own `.env` files containing overlapping API keys. The SDK Agent (Agent Builder) reports 0 tokens because the Claude Agent SDK doesn't expose token counts, but it does provide `total_cost_usd`. Two separate cost trackers have a 3x pricing discrepancy for Opus ($5/$25 vs $15/$75 per MTok).

Key files:
- `CE - Agent Builder/src/csuite/agents/sdk_agent.py` — permission bypass (line 264), token reporting (lines 307-315)
- `CE - Agent Builder/src/csuite/tools/cost_tracker.py` — pricing constants (lines 41-48)
- `CE - Multi-Agent Orchestration/protocols/cost_tracker.py` — pricing constants (lines 27-38)
- `.env` files in all three project directories

## Constraints

- **No breaking changes**: Existing CLI commands, protocol runs, and API endpoints must continue working
- **Brownfield**: Must work within existing project structure (spaces in directory names, separate venvs)
- **Shared pricing file**: Must be importable from both Agent Builder (package) and Orchestration (scripts)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Centralize .env only (no encryption) | Reduces duplication immediately; encryption is a separate concern | — Pending |
| Keep bypassPermissions | Intentional for automation; document risk instead of removing | — Pending |
| Estimate tokens from cost | SDK provides total_cost_usd; back-calculation gives usable data | — Pending |
| Research current Anthropic pricing | Neither project's prices are verified; get ground truth first | — Pending |
| Single shared pricing module | Eliminates drift between projects; one update propagates to both | — Pending |

---
*Last updated: 2026-03-09 after initialization*
