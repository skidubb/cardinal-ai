# bypassPermissions Design Decision

> **Audience:** Internal developers only. Not client-facing.

## Overview

The `permission_mode="bypassPermissions"` option in `ClaudeAgentOptions` instructs the Claude Agent SDK to execute all tool calls without prompting for user approval. When set, the SDK agent will invoke MCP servers, file operations, and other tools autonomously — no interactive confirmation dialogs are presented.

## Location

- **File:** `src/csuite/agents/sdk_agent.py`, line 266
- **Configuration:** Set in the `ClaudeAgentOptions` constructor within `SdkAgent._run_sdk()`

```python
options = ClaudeAgentOptions(
    system_prompt=self._build_system_prompt(),
    model=self.config.model or get_settings().default_model,
    mcp_servers=self.mcp_servers,
    max_turns=15,
    permission_mode="bypassPermissions",
    cwd=str(get_settings().project_root),
)
```

## Rationale

SDK agents run autonomously as part of multi-agent protocols orchestrated by CE - Multi-Agent Orchestration. Protocols execute agents in parallel via `asyncio.gather` — blocking on user approval for each tool call would deadlock parallel execution across all 48 protocols.

Key constraints that require bypass:
- **Parallel execution:** Multiple agents run simultaneously within a single protocol turn. Interactive approval would serialize all tool calls.
- **Protocol throughput:** A single protocol run may involve 3-7 agents each making 5-15 tool calls. Manual approval would make protocol execution impractical.
- **Headless operation:** Protocols run from CLI and API contexts where no interactive terminal is available for approval prompts.

## MCP Servers Accessed

All MCP server assignments are defined in `src/csuite/agents/mcp_config.py`.

| Server | Transport | Access | Roles |
|--------|-----------|--------|-------|
| **Pinecone** (`ce-gtm-knowledge`) | stdio (npx) | Read/Write | All roles (via `_COMMON`) |
| **Notion** | HTTP | Read/Write | All roles (via `_COMMON`) |
| **SEC EDGAR** | stdio (custom) | Read-only | CFO, CRO, and their direct reports |
| **Pricing Calculator** | stdio (custom) | Read-only | CFO, CRO, and their direct reports |
| **GitHub Intel** | stdio (custom) | Read-only | CTO and direct reports |

## Risk Assessment

| Risk | Severity | Notes |
|------|----------|-------|
| Pinecone write without approval | Medium | Agents can upsert to `agent-insights` namespace. Data is additive (no delete operations exposed). |
| Notion write without approval | Medium | Agents can create/update pages in the workspace. No bulk delete operations in the MCP server. |
| SEC EDGAR uncontrolled reads | Low | Public data, read-only. Rate-limited by SEC fair access policy. |
| Pricing Calculator reads | Low | Local computation only, no external calls. |
| GitHub Intel reads | Low | Read-only API queries against public repositories. |
| Runaway tool loops | Medium | Agent could enter a tool-call loop consuming API credits. |

**Overall risk:** Medium. The primary concern is unreviewed writes to Pinecone and Notion. Both are bounded by the MCP server operation sets (no destructive operations like delete-all) and the agent turn limit.

## Mitigations

1. **Role-based MCP mapping** (`mcp_config.py`): Each role only receives the MCP servers relevant to its function. A CMO agent cannot access SEC EDGAR or GitHub Intel.

2. **Turn limit** (`max_turns=15`): Caps the maximum number of tool-call rounds per agent invocation. Prevents unbounded tool loops and limits cost exposure per run.

3. **Read-only external APIs:** SEC EDGAR, Pricing Calculator, and GitHub Intel MCP servers expose only read operations. No write/mutate endpoints.

4. **Custom MCP servers with constrained operation sets:** The three custom servers in `mcp_servers/` expose a curated set of operations — not arbitrary API access. Each server defines explicit tool schemas.

5. **Pinecone namespace isolation:** Agent writes go to the `agent-insights` namespace, separate from the primary `ce-gtm-knowledge` data. Reads are scoped to role-specific namespaces defined in `prompts/kb_instructions.py`.

6. **No destructive operations:** Neither the Pinecone nor Notion MCP configurations expose bulk-delete or workspace-destructive operations.

## Review Cadence

Any addition of new MCP servers to `mcp_config.py` should be reviewed for permission implications:

- **Does the new server have write access?** If yes, document what it can modify and whether operations are reversible.
- **Does it access external services?** If yes, confirm rate limits and credential scoping.
- **Does it need to be in `_COMMON` (all roles)?** Prefer role-specific assignment over blanket access.
- **Are operations bounded?** Ensure no unbounded loops or recursive tool patterns are possible.

Update this document when MCP server configurations change.

---
*Last updated: 2026-03-09*
*Internal developer reference — not for client distribution*
