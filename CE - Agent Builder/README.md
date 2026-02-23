# C-Suite: Elite AI Advisory Team

AI-powered executive advisory agents for professional services businesses. Built with the Anthropic API and Click CLI framework.

## The Seven Executives

| Agent | Role | Focus |
|-------|------|-------|
| CEO | Chief Executive Officer | Strategy, market positioning, competitive moats |
| CFO | Chief Financial Officer | Profitability, pricing, cash flow, financial KPIs |
| CTO | Chief Technology Officer | Architecture, build vs. buy, security, tech evaluation |
| CMO | Chief Marketing Officer | Brand, thought leadership, demand gen, content strategy |
| COO | Chief Operating Officer | Resource allocation, delivery, process optimization |
| CPO | Chief Product Officer | Product-market fit, roadmap, service design |
| CRO | Chief Revenue Officer | Pipeline, revenue ops, partnerships, sales execution |

## Installation

```bash
python -m venv venv
source venv/bin/activate

# Core install
pip install -e .

# With Agent SDK backend (optional)
pip install -e ".[sdk]"

# With dev tools
pip install -e ".[dev]"
```

## Configuration

```bash
cp .env.example .env
# Edit .env with your API keys (only ANTHROPIC_API_KEY is required)
```

Edit `.claude/CLAUDE.md` with your business context to personalize agent advice.

Set `AGENT_BACKEND=sdk` in `.env` to use the Agent SDK backend with MCP tool access (default is `legacy`).

## Usage

```bash
# Individual agent queries
csuite ceo "Should we expand into AI consulting?"
csuite cfo "Analyze our project profitability for Q4"

# Cross-functional synthesis (all or specific agents)
csuite synthesize "Evaluate acquiring a competitor" --agents cfo cto coo

# Multi-round executive debate
csuite debate "Build vs. buy our data platform" -a cfo cto cmo -r 3

# Growth Strategy Audit
csuite audit "A $12M firm with 45 employees" --revenue "$12M" --employees 45 -o audit.md

# Strategy events
csuite strategy-meeting "Q2 planning" -a cfo cto cmo -r 3 -o meeting.md
csuite sprint start --strategy-doc doc.md --number 4
csuite board-meeting --agenda "Q1 review, hiring plan" -o minutes.md

# Interactive mode (@ceo, @cfo, @all, @debate)
csuite interactive

# Session management
csuite sessions list
csuite sessions resume <id>

# Reports
csuite report financial --period quarterly --output report.md
csuite report strategic --output strategy.md
```

## Architecture

Two independent agent systems:

1. **Python CLI** (`src/csuite/`) -- 7 agents via Anthropic API, with synthesis, debate, audit, and event orchestration
2. **Claude Code agents** (`~/claude-dotfiles/agents/`) -- 7 executives + 30 sub-agents as Claude Code Task tool agents

See `.claude/CLAUDE.md` for full architecture documentation.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -m "not integration"   # Unit tests
ruff check src/ mcp_servers/         # Lint
mypy src/csuite --ignore-missing-imports  # Type check
```

## License

MIT
