# CE Orchestrator API Reference

Base URL: `http://localhost:8000`

## Quick Start

```bash
# 1. Activate the venv and start the server
cd "CE - Multi-Agent Orchestration"
source venv/bin/activate
uvicorn api.server:app --reload --port 8000

# 2. Health check
curl http://localhost:8000/api/health

# 3. List available protocols
curl http://localhost:8000/api/protocols

# 4. Run a protocol with SSE streaming
curl -N -X POST http://localhost:8000/api/runs/protocol \
  -H "Content-Type: application/json" \
  -d '{
    "protocol_key": "p06_triz",
    "question": "Should we expand into Europe?",
    "agent_keys": ["ceo", "cfo", "cto"]
  }'
```

**Authentication:** Disabled by default (`SKIP_AUTH=true`). To enable, set `API_KEY=<secret>` in `.env` and pass `X-API-Key: <secret>` on every request.

**CORS:** Allowed origins are `http://localhost:5173` and `http://127.0.0.1:5173` (the Vite dev server).

**Interactive docs:** `http://localhost:8000/docs` (Swagger UI) and `/redoc`.

---

## Agents

`prefix: /api/agents`

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| GET | `/api/agents` | List all 56 built-in agents merged with DB overrides | — | `list[AgentDetail]` |
| POST | `/api/agents` | Create a custom (non-builtin) agent | `Agent` model (see below) | `Agent` (201) |
| GET | `/api/agents/{key}` | Get a single agent by key | — | `AgentDetail` |
| PUT | `/api/agents/{key}` | Update agent fields; creates DB record for builtins on first edit | Partial `AgentDetail` fields | `AgentDetail` |
| POST | `/api/agents/import-rich` | Seed DB with rich agent configs from Agent Builder | — | `{"status":"ok", ...stats}` |
| GET | `/api/tools` | List available tool and MCP server catalogs | — | `{"tools": [...], "mcp_servers": [...]}` |

**Agent model (POST body):**
```json
{
  "key": "custom-analyst",
  "name": "Custom Analyst",
  "category": "executive",
  "model": "claude-opus-4-6",
  "temperature": 1.0,
  "max_tokens": 8192,
  "system_prompt": "You are a strategic analyst...",
  "tools_json": "[]",
  "mcp_servers_json": "[]",
  "kb_namespaces_json": "[]",
  "kb_write_enabled": false,
  "deliverable_template": "",
  "frameworks_json": "[]",
  "delegation_json": "[]",
  "constraints_json": "[]",
  "personality": "",
  "communication_style": ""
}
```

**AgentDetail response shape:**
```json
{
  "key": "ceo",
  "name": "Chief Executive Officer",
  "category": "executive",
  "model": "",
  "temperature": 1.0,
  "max_tokens": 8192,
  "system_prompt": "...",
  "context_scope": [],
  "is_builtin": true,
  "tools": ["web_search", "calculator"],
  "mcp_servers": [],
  "kb_namespaces": [],
  "kb_write_enabled": false,
  "deliverable_template": "",
  "frameworks": [],
  "delegation": [],
  "constraints": [],
  "personality": "",
  "communication_style": ""
}
```

**Notes:**
- Built-in agents (from `protocols/agents.py`) are always returned even without a DB record.
- `PUT` merges: list fields (`tools`, `mcp_servers`, `frameworks`, etc.) are replaced; scalar fields are patched.
- Attempting to `POST` with a key that matches a built-in returns `409 Conflict`.

**Example curl:**
```bash
# List all agents
curl http://localhost:8000/api/agents

# Get a single agent
curl http://localhost:8000/api/agents/cfo

# Update an agent's system prompt
curl -X PUT http://localhost:8000/api/agents/ceo \
  -H "Content-Type: application/json" \
  -d '{"system_prompt": "You are the CEO focused on growth..."}'
```

---

## Protocols

`prefix: /api/protocols`

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| GET | `/api/protocols` | List all 48 available protocols with metadata | — | `list[ProtocolManifestEntry]` |

**Response shape (per entry):**
```json
{
  "key": "p06_triz",
  "name": "TRIZ Contradiction Analysis",
  "category": "Liberating Structures",
  "description": "...",
  "supports_rounds": false
}
```

**Example curl:**
```bash
curl http://localhost:8000/api/protocols
```

---

## Teams

`prefix: /api/teams`

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| GET | `/api/teams` | List all saved teams | — | `list[TeamResponse]` |
| POST | `/api/teams` | Create a new team | `TeamCreate` | `TeamResponse` (201) |
| GET | `/api/teams/{team_id}` | Get a team by ID | — | `TeamResponse` |
| PUT | `/api/teams/{team_id}` | Update team name, description, and agent list | `TeamCreate` | `TeamResponse` |
| DELETE | `/api/teams/{team_id}` | Delete a team | — | 204 No Content |

**TeamCreate request body:**
```json
{
  "name": "Strategy Council",
  "description": "Core executive team for strategic decisions",
  "agent_keys": ["ceo", "cfo", "cto", "cmo"]
}
```

**TeamResponse:**
```json
{
  "id": 1,
  "name": "Strategy Council",
  "description": "Core executive team for strategic decisions",
  "agent_keys": ["ceo", "cfo", "cto", "cmo"],
  "created_at": "2026-03-03T12:00:00+00:00",
  "last_used_at": null
}
```

**Example curl:**
```bash
# Create a team
curl -X POST http://localhost:8000/api/teams \
  -H "Content-Type: application/json" \
  -d '{"name":"Strategy Council","agent_keys":["ceo","cfo","cto"]}'

# Delete a team
curl -X DELETE http://localhost:8000/api/teams/1
```

---

## Pipelines

`prefix: /api/pipelines`

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| GET | `/api/pipelines` | List all saved pipelines | — | `list[Pipeline]` |
| POST | `/api/pipelines` | Create a pipeline with ordered steps | `PipelineCreate` | `PipelineWithSteps` (201) |
| GET | `/api/pipelines/{pipeline_id}` | Get a pipeline with its steps | — | `PipelineWithSteps` |

**PipelineCreate request body:**
```json
{
  "name": "Strategic Review",
  "description": "Synthesize then debate",
  "team_id": 1,
  "steps": [
    {
      "protocol_key": "p03_parallel_synthesis",
      "question_template": "What are the key strategic options for {question}?",
      "thinking_model": "claude-opus-4-6",
      "orchestration_model": "claude-haiku-4-5-20251001",
      "rounds": null,
      "output_passthrough": true,
      "no_tools": false
    },
    {
      "protocol_key": "p04_multi_round_debate",
      "question_template": "Debate the options identified: {prev_output}",
      "rounds": 3,
      "output_passthrough": true,
      "no_tools": false
    }
  ]
}
```

**PipelineWithSteps response:**
```json
{
  "id": 1,
  "name": "Strategic Review",
  "description": "...",
  "team_id": 1,
  "created_at": "2026-03-03T12:00:00+00:00",
  "steps": [
    {
      "id": 1,
      "order": 0,
      "protocol_key": "p03_parallel_synthesis",
      "question_template": "...",
      "agent_key_override_json": "[]",
      "rounds": null,
      "thinking_model": "claude-opus-4-6",
      "orchestration_model": "claude-haiku-4-5-20251001",
      "output_passthrough": true
    }
  ]
}
```

**Note:** Use `{prev_output}` in `question_template` to pass the previous step's synthesis into the next step's question.

**Example curl:**
```bash
curl -X POST http://localhost:8000/api/pipelines \
  -H "Content-Type: application/json" \
  -d '{"name":"Two-Step","steps":[{"protocol_key":"p03_parallel_synthesis","question_template":"Analyze: {question}","output_passthrough":true}]}'
```

---

## Runs

`prefix: /api/runs`

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| GET | `/api/runs` | List recent runs (paginated) | Query: `limit` (default 20), `offset` (default 0) | `list[RunSummary]` |
| GET | `/api/runs/{run_id}` | Get a run with all steps and agent outputs | — | `RunDetail` |
| POST | `/api/runs/protocol` | Start a single-protocol run; returns SSE stream | `ProtocolRunRequest` | `text/event-stream` |
| POST | `/api/runs/pipeline` | Start a multi-step pipeline run; returns SSE stream | `PipelineRunRequest` | `text/event-stream` |

**ProtocolRunRequest:**
```json
{
  "protocol_key": "p06_triz",
  "question": "Should we expand into Europe?",
  "agent_keys": ["ceo", "cfo", "cto"],
  "thinking_model": "claude-opus-4-6",
  "orchestration_model": "claude-haiku-4-5-20251001",
  "rounds": null,
  "no_tools": false
}
```

**PipelineRunRequest:**
```json
{
  "pipeline_name": "My Pipeline",
  "question": "Should we expand into Europe?",
  "agent_keys": ["ceo", "cfo", "cto"],
  "steps": [
    {
      "protocol_key": "p03_parallel_synthesis",
      "question_template": "{question}",
      "output_passthrough": true,
      "no_tools": false
    }
  ]
}
```

**SSE event sequence (protocol run):**

| Event | Payload |
|-------|---------|
| `run_start` | `{"run_id": 42, "protocol_key": "p06_triz"}` |
| `agent_roster` | `{"agents": [{"key": "ceo", "name": "Chief Executive Officer"}, ...]}` |
| `stage` | `{"message": "Running protocol..."}` |
| `tool_call` | `{"agent_name": "CEO", "tool_name": "web_search", "tool_input": "...", "iteration": 0}` |
| `tool_result` | `{"agent_name": "CEO", "tool_name": "web_search", "result_preview": "...", "elapsed_ms": 120.4}` |
| `agent_output` | `{"agent_key": "ceo", "agent_name": "Chief Executive Officer", "text": "..."}` |
| `synthesis` | `{"text": "Final synthesized recommendation..."}` |
| `run_complete` | `{"run_id": 42, "elapsed_seconds": 34.2, "status": "completed"}` |
| `error` | `{"message": "...", "traceback": "..."}` (only on failure) |

**Pipeline run adds these additional events:**

| Event | Payload |
|-------|---------|
| `step_start` | `{"step": 0, "protocol_key": "p03_parallel_synthesis"}` |
| `step_complete` | `{"step": 0, "protocol_key": "p03_parallel_synthesis"}` |

**RunDetail response:**
```json
{
  "id": 42,
  "type": "protocol",
  "protocol_key": "p06_triz",
  "pipeline_id": null,
  "question": "Should we expand into Europe?",
  "team_id": null,
  "status": "completed",
  "cost_usd": 0.0,
  "started_at": "2026-03-03T12:00:00+00:00",
  "completed_at": "2026-03-03T12:00:34+00:00",
  "steps": [],
  "outputs": [
    {
      "id": 1,
      "agent_key": "ceo",
      "model": "claude-opus-4-6",
      "output_text": "...",
      "tool_calls": [],
      "input_tokens": 0,
      "output_tokens": 0,
      "cost_usd": 0.0
    },
    {
      "id": 4,
      "agent_key": "_synthesis",
      "model": "claude-opus-4-6",
      "output_text": "Final synthesis..."
    }
  ]
}
```

**Example curl:**
```bash
# Start a protocol run (SSE)
curl -N -X POST http://localhost:8000/api/runs/protocol \
  -H "Content-Type: application/json" \
  -d '{"protocol_key":"p06_triz","question":"Expand to Europe?","agent_keys":["ceo","cfo","cto"]}'

# Get run history (last 5)
curl "http://localhost:8000/api/runs?limit=5&offset=0"

# Get a specific run with all outputs
curl http://localhost:8000/api/runs/42
```

---

## Health

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/api/health` | Liveness check | `{"status": "ok"}` |

---

## Data Models Summary

Defined in `api/models.py` using SQLModel (SQLite-backed).

| Model | Table | Key Fields |
|-------|-------|------------|
| `Agent` | `agent` | `key` (unique), `name`, `category`, `model`, `system_prompt`, `tools_json`, `mcp_servers_json` |
| `Team` | `team` | `name`, `agent_keys_json` |
| `Pipeline` | `pipeline` | `name`, `team_id` |
| `PipelineStep` | `pipelinestep` | `pipeline_id`, `order`, `protocol_key`, `question_template`, `rounds`, `output_passthrough` |
| `Run` | `run` | `type` (`protocol`/`pipeline`), `protocol_key`, `status`, `cost_usd` |
| `RunStep` | `runstep` | `run_id`, `step_order`, `protocol_key`, `status` |
| `AgentOutput` | `agentoutput` | `run_id`, `agent_key`, `output_text`, `tool_calls_json`, `input_tokens`, `output_tokens` |
