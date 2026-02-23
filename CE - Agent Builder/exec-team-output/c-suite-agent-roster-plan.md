# Plan: Build C-Suite Agent Roster

## Context
You want to summon your exec team — individually as subagents or together as coordinated agent teams. Each exec brings a distinct decision-making lens (strategy, finance, marketing, tech, operations, product) so you can pressure-test ideas from multiple perspectives.

## What We're Building
6 agent files in `~/claude-dotfiles/agents/`, one per C-suite role. Since dotfiles/agents/ is already symlinked to `~/.claude/agents/`, they'll be available globally across all projects immediately — no setup needed.

## Files to Create

All in `~/claude-dotfiles/agents/`:

| File | Role | Thinking Style |
|---|---|---|
| `ceo.md` | Chief Executive Officer | Vision, strategy, market positioning, big bets |
| `cfo.md` | Chief Financial Officer | Unit economics, ROI, budget, risk quantification |
| `cmo.md` | Chief Marketing Officer | Brand, messaging, growth channels, audience |
| `cto.md` | Chief Technology Officer | Architecture, build vs. buy, tech debt, scalability |
| `coo.md` | Chief Operating Officer | Processes, scaling, execution, cross-functional ops |
| `cpo.md` | Chief Product Officer | User needs, roadmap, prioritization, product-market fit |

## Agent Design Pattern

Each agent follows the existing frontmatter pattern (matching `brand-analyst.md` and `brand-essence.md`):

```yaml
---
name: ceo              # kebab-case, used as subagent_type
description: ...       # 1-2 sentences, action-oriented
tools:
  - WebSearch
  - WebFetch
  - Read
  - Write
model: sonnet          # matches existing agents; cheaper for subagent work
---
```

### Tool Assignments
- **CEO, CFO, CMO, COO, CPO**: `WebSearch, WebFetch, Read, Write` — research + analysis + deliverables
- **CTO**: `WebSearch, WebFetch, Read, Write, Grep, Glob` — same plus code exploration (needs to inspect repos, read codebases, evaluate tech stacks)

### Persona Structure (each agent)
1. **Identity** — who they are, how they think
2. **When activated** — the research/analysis steps they execute autonomously
3. **Deliverable** — structured output format (brief, memo, recommendation)
4. **Decision framework** — the mental models they apply (e.g., CFO uses unit economics; CPO uses RICE prioritization)
5. **Rules** — tone, length, audience constraints (product/marketing professional, not engineers)

## How They'll Be Used

### Solo (subagent)
Claude spawns one exec via Task tool:
```
"Summon the CFO to evaluate this pricing model"
→ Task tool launches cfo agent as subagent
```

### Team (agent teams)
Claude creates a team and spawns multiple execs:
```
"Convene the exec team to evaluate this product idea"
→ TeamCreate → spawn 3-6 agents → TaskCreate for each → coordinate via SendMessage
```

### Board meeting pattern
Ask a strategic question → each exec researches from their angle → team lead synthesizes into a unified recommendation with dissenting opinions noted.

## Build Sequence

1. Create `~/claude-dotfiles/agents/ceo.md`
2. Create `~/claude-dotfiles/agents/cfo.md`
3. Create `~/claude-dotfiles/agents/cmo.md`
4. Create `~/claude-dotfiles/agents/cto.md`
5. Create `~/claude-dotfiles/agents/coo.md`
6. Create `~/claude-dotfiles/agents/cpo.md`
7. Verify symlink: confirm `~/.claude/agents/` contains all 6 new files alongside existing agents

## Verification
- `ls ~/claude-dotfiles/agents/` shows all 6 new files + existing 3 (brand-analyst, brand-essence, competitive-ads)
- `ls -la ~/.claude/agents/` confirms the symlink is still intact
- Spot-check frontmatter on 1-2 agents (valid YAML, correct tools list)
- Test one agent solo: ask Claude to "summon the CMO" and verify it activates with the right persona and tools
