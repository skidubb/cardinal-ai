---
name: audit-drift
description: Detect prompt drift between the two agent registries (Agent Builder fat prompts vs Orchestration thin BUILTIN_AGENTS). Use when the user asks "is there drift?", "audit agent prompts", or when a role's behavior differs between csuite and protocols.
---

# /audit-drift

The Cardinal Element system holds agent identity in two places:

- **Agent Builder** — `CE - Agent Builder/src/csuite/prompts/*_prompt.py` — the fat prompts (100-300 lines each) used by `SdkAgent`.
- **Orchestration** — `CE - Multi-Agent Orchestration/protocols/agents.py` `BUILTIN_AGENTS` dict — thin one-line system prompts used when `AgentBridge` exposes `agent["system_prompt"]` to non-`chat` consumers.

`AgentBridge` (`protocols/agent_provider.py`) stores the thin prompt in `self.system_prompt` and delegates `chat()` to the SdkAgent, which uses the fat one. **A protocol that reads `agent["system_prompt"]` sees one identity; the actual LLM call runs the other.** This is the prompt drift risk called out in root `CLAUDE.md`.

## Run the drift check

1. **List roles present in both registries.** For each role key:
   ```
   fat_prompt   = Agent Builder src/csuite/prompts/{role}_prompt.py
   thin_prompt  = Orchestration protocols/agents.py BUILTIN_AGENTS[role]["system_prompt"]
   ```

2. **Detect divergence.** Two failure modes:
   - **Semantic divergence**: fat and thin say different things about the role's mission, tools, or values. Flag as `DRIFT`.
   - **Coverage gap**: role exists in one registry, not the other. Flag as `ONLY_FAT` or `ONLY_THIN`.

3. **Report** using this format:
   ```
   | role | fat lines | thin lines | verdict |
   |---|---|---|---|
   | ceo | 224 | 1 | DRIFT — fat mentions "elite consultant" identity, thin says "chief executive officer" |
   ```

4. **Recommend the fix.** Two options:
   - **Merge**: replace thin prompts with fat ones (Orchestration `BUILTIN_AGENTS` reads from Agent Builder). Single source of truth.
   - **Isolate**: rename thin registry `RESEARCH_MODE_AGENTS` and document that production always uses fat. Two sources, but honest about it.

The Sprint 3 plan calls for **merge**.

## Do not

- Do NOT silently edit `BUILTIN_AGENTS` to look more like fat prompts. That hides drift instead of exposing it.
- Do NOT rewrite fat prompts to look thin. The fat prompts are the product.

## Post-check

After a merge:

```bash
cd "CE - Multi-Agent Orchestration"
pytest tests/ -m "not integration"     # confirm nothing else read the old thin prompts
python -m protocols.p03_parallel_synthesis.run -q "quick smoke" -a ceo cfo cto
```

If a protocol synthesis stage was quoting `agent["system_prompt"]` in its prompt, verify the merged (fat) prompt doesn't blow the token budget. If it does, add a `agent["system_prompt_short"]` helper.
