# Features Research: Secrets Management, Cost Tracking & Shared Pricing

Research into standard features/capabilities for the three domains addressed by the CE-AGENTS critical debt remediation. Based on Python monorepo conventions, Anthropic SDK behavior, and the specific concerns in CONCERNS.md (C-1, C-3, C-4).

---

## Table Stakes

### Centralized Secrets / Env Management

- **Single root `.env` with project-level overrides** -- One `.env` at monorepo root holds all shared keys (ANTHROPIC_API_KEY, PINECONE_API_KEY, etc.). Projects only override when they genuinely differ. Eliminates C-1's duplicated keys across three `.env` files. | Complexity: **Low**
- **`.env.example` at root with all required/optional vars documented** -- Every key listed with a comment indicating which projects use it. Developers copy once, not three times. | Complexity: **Low**
- **`python-dotenv` with `find_dotenv()` or explicit root path resolution** -- Each project's Settings class loads from root `.env` via a shared path helper (e.g., `Path(__file__).resolve().parents[N] / ".env"`). Pydantic-settings already supports `env_file` parameter. | Complexity: **Low**
- **`.env` files in `.gitignore` at root level** -- Already in place, but verify after consolidation that old project-level `.env` paths are still ignored. | Complexity: **Low**
- **Validation on startup** -- Settings class fails fast with a clear error if a required key is missing or empty, rather than failing deep in an API call. Pydantic validators handle this. | Complexity: **Low**
- **No secrets in docker-compose.yml** -- Replace hardcoded `POSTGRES_PASSWORD: ce_local` with `${POSTGRES_PASSWORD}` referencing the root `.env`. Addresses part of I-7. | Complexity: **Low**

### SDK Cost Tracking / Token Estimation

- **Back-calculate tokens from `total_cost_usd`** -- When the SDK provides cost but not tokens, divide by known per-token price to produce estimated input/output token counts. This is the standard workaround when SDKs abstract away token-level billing. Addresses C-3 directly. | Complexity: **Medium**
- **Carry `total_cost_usd` as the authoritative cost field** -- The SDK-reported cost is ground truth. Estimated tokens are secondary/derived. All downstream consumers (Langfuse spans, budget alerts, cost dashboards) should prefer `total_cost_usd` when available and use estimated tokens only for display/analysis. | Complexity: **Low**
- **Flag estimated vs actual token counts** -- Any token count derived from cost division must be tagged `estimated=True` so downstream systems know the provenance. Without this flag, consumers cannot distinguish real counts from approximations. | Complexity: **Low**
- **Handle unknown model pricing gracefully** -- If a model string doesn't match the pricing table, fall back to the most expensive tier (Opus) for cost estimation. Both trackers already do this. Codify as explicit policy. | Complexity: **Low**

### Shared Pricing Configuration

- **Single pricing module importable by both projects** -- One Python file with a dict of model -> input/output prices per MTok. Both `CE - Agent Builder` and `CE - Multi-Agent Orchestration` import from this single source. Eliminates C-4's 3x pricing discrepancy. | Complexity: **Medium** (cross-project import in a monorepo with spaces in directory names requires careful path or package setup)
- **Pricing keyed by exact model ID with substring fallbacks** -- Both trackers already use this pattern. Standardize: exact match first (`claude-opus-4-6`), then substring match (`opus`). | Complexity: **Low**
- **Date-stamped pricing with a "last verified" field** -- Each pricing entry includes the date it was verified against Anthropic's published pricing page. Prevents the "February 2026 vs March 2026" confusion in C-4. | Complexity: **Low**
- **Cache pricing constants (batch discount, cache read/write multipliers)** -- Both trackers use cache multipliers. Consolidate into the shared module. | Complexity: **Low**

---

## Differentiators

### Centralized Secrets / Env Management

- **Per-environment `.env` layering** -- Support `.env.local` overrides for developer-specific settings (e.g., different Langfuse project) without touching the shared `.env`. Not strictly needed now but prevents the "works on my machine" problem as team grows. | Complexity: **Medium**
- **Startup env report** -- On protocol/CLI launch, log which env file was loaded and which keys are set (redacted values). Eliminates "is it reading my key or the other .env?" debugging. | Complexity: **Low**
- **Env validation CLI command** -- `python -m shared.env_check` that validates all keys across all projects, reports duplicates, and flags missing required vars. Useful for onboarding and CI. | Complexity: **Medium**

### SDK Cost Tracking / Token Estimation

- **Token estimation with input/output ratio heuristic** -- When back-calculating from cost, you need to split between input and output tokens. Use a configurable ratio (e.g., 4:1 input:output for typical agent calls) or derive from the prompt length vs response length if both are available. Better than reporting all tokens as output. | Complexity: **Medium**
- **Cost tracking that reconciles SDK-reported cost vs calculated cost** -- Log both the SDK's `total_cost_usd` and the price-table-calculated cost side by side. When they diverge, it signals a pricing table update is needed. Acts as a self-correcting mechanism for C-4/M-11. | Complexity: **Medium**
- **Per-turn cost attribution in multi-turn SDK sessions** -- SDK agents can have multiple turns (tool calls trigger re-entry). Track cost deltas per turn, not just total session cost. Enables "which tool call was expensive?" analysis. | Complexity: **High**
- **Budget guardrails** -- Configurable per-protocol or per-agent cost ceiling. If estimated cost exceeds threshold, warn or halt. Prevents runaway agent loops from burning budget silently. | Complexity: **Medium**

### Shared Pricing Configuration

- **Pricing verification script** -- A script or test that fetches current pricing from Anthropic's API headers or billing page and compares against the local pricing table. Alerts on drift. Addresses M-11 structurally. | Complexity: **Medium**
- **Model alias resolution** -- Map aliases like `"opus"`, `"sonnet"`, `"haiku"` to current canonical model IDs (`claude-opus-4-6`, etc.) in one place. Both projects do this ad-hoc today; centralizing prevents divergence. | Complexity: **Low**
- **Pricing as configuration, not code** -- Store pricing in a TOML/JSON/YAML file rather than Python dicts. Allows non-developer updates and version-controlled diffing of price changes over time. | Complexity: **Low**

---

## Anti-Features

### Things to Deliberately NOT Build

- **Secrets manager integration (1Password, Vault, AWS Secrets Manager)** -- Explicitly out of scope per PROJECT.md. Centralize first, encrypt later. Adding a secrets manager now adds operational complexity (service dependencies, token rotation) without solving the immediate duplication problem. Revisit when deploying to shared/production infrastructure.
- **Dynamic pricing fetched from Anthropic at runtime** -- Anthropic does not expose a pricing API. Scraping or inferring from billing headers is fragile and adds a network dependency to every cost calculation. Static pricing table with manual verification is more reliable.
- **Automatic token counting via tiktoken/tokenizer** -- The Claude Agent SDK does not expose raw messages for external tokenization. Even if it did, tokenizer-based counting is an approximation that drifts across model versions. The SDK's `total_cost_usd` is the authoritative source; back-calculation is sufficient.
- **Centralized config service / microservice for env vars** -- Overengineered for a solo-developer monorepo with three projects. A shared `.env` file and a Python module solve the problem without runtime service dependencies.
- **Multi-region or multi-account key management** -- Not relevant for a single-operator consultancy. All API keys belong to one Anthropic account, one Pinecone org, etc.
- **Encryption at rest for `.env` files** -- Explicitly deferred per PROJECT.md. The files are gitignored and on a single developer machine. Encryption adds complexity (key management for the key manager) without meaningful security improvement in this threat model.
- **Per-request pricing lookups** -- Checking pricing on every API call adds latency and complexity. Pricing changes infrequently (quarterly at most). A static dict with periodic manual verification is the right granularity.

---

## Feature Dependencies

```
Single root .env ─────────────┬──► Startup env report (needs to know which file loaded)
                              ├──► Env validation CLI (needs to know expected keys)
                              └──► Docker compose env refs (needs root .env to exist)

Shared pricing module ────────┬──► Token back-calculation (needs prices to divide by)
                              ├──► Cost reconciliation (needs calculated vs SDK cost)
                              ├──► Budget guardrails (needs price-per-token for estimates)
                              └──► Pricing verification script (needs baseline to compare)

Token back-calculation ───────┬──► Langfuse generation spans (need non-zero token counts)
                              ├──► Per-turn cost attribution (extends basic estimation)
                              └──► estimated=True flag (metadata on derived counts)

Shared pricing module ────────┬──► Model alias resolution (centralized alias map)
                              └──► Date-stamped pricing (metadata on the shared dict)
```

### Recommended Implementation Order

1. **Shared pricing module** -- Unblocks everything else. Create one file, verify prices, import from both projects. Fixes C-4 immediately.
2. **Single root `.env`** -- Consolidate keys, update Settings classes to load from root. Fixes C-1.
3. **Token back-calculation** -- Use shared pricing to estimate tokens from SDK cost. Fixes C-3.
4. **Differentiators** -- Layer on reconciliation, budget guardrails, verification scripts as time permits.

---

*Generated: 2026-03-09 | Domains: Python monorepo env management, Anthropic SDK cost tracking, cross-project pricing configuration*
