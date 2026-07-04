# ce-graph — Customer Onboarding Playbook

This is the SOP for standing up a customer's knowledge graph. Used internally by Cardinal Element, also serves as the documentation a customer's IT team would receive at handoff.

## What the customer gets

A **dedicated, isolated knowledge graph** of their business — entities (companies, people, engagements, decisions), relationships (who decided what about which client when), corrections (the rules-of-the-road for working with their domain), and lessons (patterns that compound across engagements). Queryable via natural language or Cypher. Visual via the FalkorDB browser. Wired to the C-Suite agents that reason against it.

## Tier 1 — Knowledge Graph Audit (kickoff to handoff)

### Day 1: Discovery (with customer)

Identify their **canonical sources of institutional knowledge**:

| Source | What it gives the graph | Connector |
|---|---|---|
| CRM (HubSpot / Salesforce) | Client / Person / Engagement entities | `hubspot` (direct API) |
| Doc store (Notion / Confluence) | Engagement notes, audit reports, decision logs | `notion` (MCP) |
| Meeting tool (Granola / Otter / Fireflies) | Discovery calls, working sessions | `granola` (MCP) |
| Email (Gmail / Outlook) | Client comms, scope changes | `gmail` (MCP) |
| Drive (Google / OneDrive) | Proposals, contracts, deliverables | `google_drive` (MCP) |
| Chat (Slack / Teams) | Working-channel decisions, async context | `slack` (MCP) |

**Important:** Don't ingest everything. The graph is for *structured institutional learning*, not full-text search. For each source, agree on:
- **Scope** — which databases, channels, folders are in/out
- **Time horizon** — usually last 12 months for backfill
- **Frequency** — incremental refresh cadence (daily / hourly)

### Day 1: Provision the tenant

```bash
cd "/Users/scottewalt/Documents/CE - AGENTS/ce-graph"
source venv/bin/activate
cegraph create <slug> --display "Customer Name" --vertical "Industry"
cegraph init --tenant <slug>
```

Edit `tenants/<slug>.yaml` to enable the connectors agreed on with the customer. Add any per-connector config (workspace IDs, channel filters, etc.).

### Day 2-3: Credentials + connector setup

Per connector:

**HubSpot (direct API):** Customer creates a Private App in HubSpot with read scopes for `crm.objects.companies/contacts/deals`. They share the token with you. Add `<TENANT_SLUG>_HUBSPOT_TOKEN` to `.env` and reference in their tenant config.

**MCP-driven (Notion / Granola / Gmail / Drive / Slack):** Customer authorises the relevant Claude.ai integration with their workspace. Once OAuth is complete in their Claude account, the MCP tools work for the duration of their session. No tokens to manage.

### Day 3-5: Backfill

Run the backfill agent inside Claude Code. From the CE-AGENTS repo:

```
Use the Task tool with subagent_type: ce-graph-backfill
Prompt: "backfill notion + granola for tenant <slug>, last 12 months, dry-run first"
```

Review the dry-run output. Confirm scope. Re-run without `dry-run`.

Cost estimate: $0.001-0.005 per episode (Haiku 4.5 entity extraction). 1,000 episodes ≈ $1-5. Backfilling a year of a typical mid-size company runs ~$20-100.

### Day 5-7: Verification + first queries

```bash
cegraph status --tenant <slug>
```

Open FalkorDB browser at http://localhost:3000 and select the customer's graph. Run sample Cypher:

```cypher
MATCH (c:Client) RETURN c.name, c.vertical
MATCH (d:Decision)-[:USING_PROTOCOL]->(p:Protocol) RETURN d.summary, p.name
MATCH (cor:Correction) RETURN cor.text, cor.scope
```

Walk the customer through 5-10 queries that answer their *specific* questions ("show me all decisions about pricing for client X," "what corrections apply when working with vertical Y," etc.).

### Day 7: Handoff deliverable

Customer receives:

1. **Graph access** — FalkorDB instance (managed by CE for Tier 1, or migrated to their infra for self-hosted)
2. **Connector setup docs** — per-connector how-they-work, how-to-rotate-credentials
3. **Entity model documentation** — Client / Engagement / Decision / Correction / Lesson schemas
4. **Query cookbook** — 10-20 queries answering questions they raised in Discovery
5. **Refresh runbook** — how to run incremental updates (cron / LaunchAgent / Claude Code task)
6. **Phase 2 proposal** — wire the C-Suite agents to query their graph; ongoing retainer

## Active tenant slugs (April 2026)

| Slug | Display | Status | Vertical |
|---|---|---|---|
| `cardinal-element` | Cardinal Element | Reference (live) | Consulting |
| `imagine-wireless` | Imagine Wireless | Provisioned, awaiting connectors | Wireless / Telecom |
| `workload` | Workload | Provisioned, awaiting connectors | TBD |
| `silver-lake-auto` | Silver Lake Auto | Provisioned, awaiting connectors | Auto Retail |
| `public-safety-wireless` | Public Safety Wireless | Provisioned, awaiting connectors | Public Sector |
| `on3` | On3 | Provisioned, awaiting connectors | Sports Media |

All 6 graphs are seeded with the **53 Cardinal Element coordination protocols** (Decision Doctrine layer) -- the IP that grounds the C-Suite agents' methodology.

## What NOT to ingest into the graph

- Every email (use the data lake / Pinecone instead)
- Every meeting transcript verbatim (extract structured facts; raw text → Pinecone)
- Generic web articles
- Cross-tenant data unless explicitly authorised

The graph is a *curated brain*, not a swamp. Keep node count high-signal: most healthy customer graphs sit at **500-5,000 nodes**, not 50,000+.

## Pricing reference (Tier 1)

- **Knowledge Graph Audit**: $25-50K, 4-6 weeks
  - Discovery + entity model design
  - Connector setup for 4-6 sources
  - Backfill + verification
  - Documentation + query cookbook
  - Handoff
- **Tier 2 (retainer)**: Tier 1 + ongoing AI agents wired to graph + monthly insights, $5-15K/mo
- **Tier 3 (self-serve, future)**: SaaS, customer-managed
