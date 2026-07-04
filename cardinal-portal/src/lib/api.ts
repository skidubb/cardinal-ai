// Typed fetch wrapper that calls the Railway FastAPI backend with the
// active user's Clerk JWT attached. Use from Server Components / Server Actions.
//
// Maps to the existing CE - Multi-Agent Orchestration API. The product surface
// is protocols + agents + runs + reports — the knowledge graph is one of the
// stores backing the agents, not the front door.

import { getRailwayToken, RAILWAY_API_BASE } from "@/lib/railway";

async function authedFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getRailwayToken();

  const res = await fetch(`${RAILWAY_API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} from ${path}: ${body}`);
  }
  return (await res.json()) as T;
}

// ---- Auth ----

export type AuthMe = {
  sub: string;
  org_id?: string;
  org_slug?: string;
  org_role?: string;
  tier?: number;
  plan?: string | null;
  features?: string[];
};

export async function fetchAuthMe(): Promise<AuthMe> {
  return authedFetch<AuthMe>("/api/auth/me");
}

// ---- Runs (the actual product surface) ----

export type Run = {
  id: string;
  protocol_key: string;
  question: string;
  status: "running" | "completed" | "failed" | "cancelled";
  agent_keys?: string[];
  started_at?: string;
  completed_at?: string;
  cost_usd?: number;
};

export async function fetchRuns(limit: number = 20): Promise<Run[]> {
  return authedFetch<Run[]>(`/api/runs?limit=${limit}`);
}

// ---- Protocol report (attached to completed runs) ----

export type StageAuditStatus = "ok" | "missing" | "partial" | "degraded" | "implicit" | "unknown";

export type StageAudit = {
  name: string;
  intent: string;
  status: StageAuditStatus;
  observed: string;
  advice: string | null;
};

export type RunAudit = {
  stages: StageAudit[];
  completeness: string;
  overall_advice: string | null;
};

export type ToolCall = {
  tool: string;
  input_summary?: string;
  result_summary?: string;
  elapsed_ms?: number;
  iteration?: number;
  id?: string;
};

export type ProtocolReport = {
  participants: string[];
  executive_summary: string;
  key_findings: string[];
  disagreements: string[];
  confidence_score: number;
  confidence_label: string;
  synthesis: string;
  agent_contributions: Array<{
    agent_key: string;
    agent_name: string;
    text: string;
    cost_usd: number;
    model: string;
    tool_calls: unknown[];
  }>;
  cost_summary: Record<string, unknown>;
  metadata: Record<string, unknown>;
  audit: RunAudit | Record<string, never>;
};

export async function fetchRun(id: string): Promise<Run & {
  result?: unknown;
  outputs?: Array<{
    id: number;
    agent_key: string;
    model?: string | null;
    output_text: string;
    cost_usd?: number;
    input_tokens?: number;
    output_tokens?: number;
    tool_calls?: ToolCall[];
  }>;
  steps?: Array<{ id: number; step_order: number; protocol_key: string; status: string }>;
  error_message?: string | null;
  protocol_report?: ProtocolReport | null;
}> {
  return authedFetch(`/api/runs/${id}`);
}

export async function deleteRun(id: string | number): Promise<{ deleted: number }> {
  return authedFetch<{ deleted: number }>(`/api/runs/${id}`, { method: "DELETE" });
}

export type BulkDeleteResult = {
  deleted: number;
  deleted_ids: number[];
  skipped: number[];
};

export async function deleteRunsBulk(ids: Array<string | number>): Promise<BulkDeleteResult> {
  const numericIds = ids.map((id) => Number(id)).filter((n) => Number.isFinite(n));
  return authedFetch<BulkDeleteResult>("/api/runs/bulk", {
    method: "DELETE",
    body: JSON.stringify({ ids: numericIds }),
  });
}

// ---- Protocols ----

export type Protocol = {
  key: string;             // e.g. "p04_multi_round_debate"
  code?: string;           // not always set; "P04" / "P0a"
  protocol_id?: string;    // Railway returns protocol_id; we treat it as code
  name: string;            // e.g. "Multi-Round Debate"
  category: string;        // e.g. "Liberating Structures"
  description?: string;
  when_to_use?: string;
  when_not_to_use?: string;
  min_agents?: number;
  max_agents?: number;
  cost_tier?: "low" | "medium" | "high";
  supports_rounds?: boolean;
  problem_types?: string[];
  orchestration_pattern?:
    | "single_agent"
    | "sequence"
    | "parallel"
    | "hub_and_spoke"
    | "hybrid_matrix"
    | "decentralized";
  recommended_agents?: string[];
  premium?: boolean;
};

export async function fetchProtocols(): Promise<Protocol[]> {
  return authedFetch<Protocol[]>("/api/protocols");
}

export type ProtocolStage = {
  key: string;
  name: string;
  stage_type?: string;
  description?: string;
  depends_on?: string[];
  agents_filter?: string | null;
};

export type ProtocolStagesResponse = {
  protocol_id: string;
  protocol_name: string;
  stages: ProtocolStage[];
  source?: "yaml" | "source" | "fallback";
};

export async function fetchProtocolStages(key: string): Promise<ProtocolStagesResponse> {
  return authedFetch<ProtocolStagesResponse>(
    `/api/protocols/${encodeURIComponent(key)}/stages`,
  );
}

// ---- Agents (the C-Suite + functional reports) ----

export type Agent = {
  key: string;             // e.g. "ceo", "gtm-vp-sales"
  name?: string;           // Railway returns "name"; we display this if present
  title?: string;          // alternative display
  category?: string;       // executive / cfo-team / cto-team / gtm-sales / etc.
  layer?: "c_suite" | "direct_report" | "functional";
  reports_to?: string;
  description?: string;
  model?: string;
  is_builtin?: boolean;
  tools?: string[];
  mcp_servers?: string[];
};

export async function fetchAgents(): Promise<Agent[]> {
  return authedFetch<Agent[]>("/api/agents");
}

// ---- Models (catalog of thinking/orchestration models) ----

export type ModelInfo = {
  id: string;
  display_name: string;
  provider: string;
  route: "anthropic" | "gateway";
  litellm_id: string;
  tier: string;
  input_price: number;
  output_price: number;
  supports_anthropic_tool_loop: boolean;
  context_window: number;
  notes: string;
};

export type ModelsResponse = {
  models: ModelInfo[];
  defaults: {
    thinking: string;
    orchestration: string;
    balanced: string;
  };
  tiers: string[];
};

export async function fetchModels(): Promise<ModelsResponse> {
  return authedFetch<ModelsResponse>("/api/models");
}

// ---- Knowledge graph stats (the fuel layer, not the front door) ----

export type GraphStatsResponse = {
  tenant_slug: string;
  graph_name: string;
  total_nodes: number;
  counts: Record<string, number>;
  all_labels: Record<string, number>;
};

export async function fetchGraphStats(): Promise<GraphStatsResponse> {
  return authedFetch<GraphStatsResponse>("/api/graph/stats");
}

export type GraphNode = {
  id: number;
  label: string;
  name: string;
  props: Record<string, unknown>;
  degree: number;
};

export type GraphEdge = {
  source: number;
  target: number;
  type: string;
};

export type GraphSubgraphResponse = {
  tenant_slug: string;
  graph_name: string;
  limit: number;
  node_count: number;
  edge_count: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export async function fetchGraphSubgraph(
  limit: number = 500,
): Promise<GraphSubgraphResponse> {
  return authedFetch<GraphSubgraphResponse>(`/api/graph/nodes?limit=${limit}`);
}

// ---- Usage (per-tenant cost + run totals) ----

export type Usage = {
  tenant_slug: string;
  total_runs: number;
  total_cost_usd: number;
  last_run_at: string | null;
  by_status: Record<string, { count: number; cost_usd: number }>;
  completed_runs: number;
  completed_cost_usd: number;
  plan: string;
  features: string[];
  period_start: string;
  period_end: string;
  period_runs: number;
  period_cost_usd: number;
  runs_limit: number | null;
  runs_remaining: number | null;
  run_cost_cap_usd: number | null;
};

export async function fetchUsage(): Promise<Usage> {
  return authedFetch<Usage>("/api/usage");
}

// ---- Connectors ----

export type ConnectorMode = "direct_api" | "mcp_driven";

export type ConnectorStatus = {
  name: string;
  mode: ConnectorMode;
  enabled: boolean;
  auth: string;
  notes?: string | null;
};

export async function fetchConnectorsStatus(): Promise<{
  tenant_slug: string;
  connectors: ConnectorStatus[];
}> {
  return authedFetch("/api/connectors/status");
}

export type BackfillResponse = {
  mode: "direct_api" | "mcp_runbook";
  connector: string;
  tenant_slug: string;
  status: "queued" | "runbook_only";
  message: string;
  runbook?: string | null;
};

export async function startConnectorBackfill(
  connector: string,
  opts: { since?: string; limit?: number; dry_run?: boolean } = {},
): Promise<BackfillResponse> {
  return authedFetch("/api/connectors/start", {
    method: "POST",
    body: JSON.stringify({ connector, ...opts }),
  });
}

// ---- Adaptive Router (smart routing) ----

export type RouterPlan = {
  protocol_key: string;
  protocol_id: string;
  name: string;
  cost_tier: "low" | "medium" | "high";
  agent_keys: string[];
  supports_rounds: boolean;
};

export type RouterDecision = {
  question: string;
  problem_type: string;
  confidence: number;
  tier: "high" | "medium" | "low";
  auto_executable: boolean;
  reasoning: string;
  adjustments: string[];
  plan: RouterPlan | null;
  raw_router?: unknown;
};

// ---- Pipelines ----

export type PipelineStep = {
  id?: number;
  order: number;
  protocol_key: string;
  question_template?: string | null;
  agent_key_override_json?: string | null;
  rounds?: number | null;
  thinking_model?: string | null;
  orchestration_model?: string | null;
  output_passthrough?: boolean;
  no_tools?: boolean;
};

export type Pipeline = {
  id: number | string;
  name: string;
  description?: string | null;
  team_id?: number | null;
  created_at?: string;
  steps: PipelineStep[];
};

export async function fetchPipelines(): Promise<Pipeline[]> {
  return authedFetch<Pipeline[]>("/api/pipelines");
}

export async function fetchPipeline(id: string | number): Promise<Pipeline> {
  return authedFetch<Pipeline>(`/api/pipelines/${id}`);
}

// ---- Teams ----

export type Team = {
  id: number;
  name: string;
  description: string;
  agent_keys: string[];
  created_at: string;
  last_used_at: string | null;
};

export async function fetchTeams(): Promise<Team[]> {
  return authedFetch<Team[]>("/api/teams");
}

// ---- Agent detail (full shape including system prompt + tools) ----

export type AgentDetail = {
  key: string;
  name: string;
  category: string;
  model: string;
  temperature: number;
  max_tokens: number;
  system_prompt: string;
  tools: string[];
  mcp_servers: string[];
  kb_namespaces: string[];
  kb_write_enabled: boolean;
  deliverable_template: string;
  frameworks: string[];
  delegation: string[];
  constraints: string[];
  personality: string;
  communication_style: string;
  is_builtin: boolean;
};

export async function fetchAgentDetail(key: string): Promise<AgentDetail> {
  return authedFetch<AgentDetail>(`/api/agents/${encodeURIComponent(key)}`);
}

// ---- Tool + MCP catalog ----

export type ToolDirection = "input" | "output" | "internal";

export type ToolDef = {
  name: string;
  description: string;
  domain: string;
  direction?: ToolDirection;
  brand?: string;
};

export type MCPServerDef = {
  name: string;
  description: string;
  transport: string;
  brand?: string;
};

export type ToolCatalog = {
  tools: Record<string, ToolDef>;
  mcp_servers: Record<string, MCPServerDef>;
};

export async function fetchToolCatalog(): Promise<ToolCatalog> {
  return authedFetch<ToolCatalog>("/api/tools");
}

// ---- Knowledge namespaces ----

export type KnowledgeNamespace = {
  name: string;
  vector_count: number | null;
  assigned_roles: string[];
};

export async function fetchNamespaces(): Promise<KnowledgeNamespace[]> {
  return authedFetch<KnowledgeNamespace[]>("/api/knowledge/namespaces");
}

// ---- Integrations (tenant-scoped enable/disable + custom additions) ----

export type Integration = {
  id: number;
  name: string;
  type: "tool_domain" | "mcp_server" | "custom_api" | string;
  enabled: boolean;
  config: Record<string, unknown>;
  api_key_configured: boolean;
  description: string;
  is_builtin: boolean;
};

export async function fetchIntegrations(): Promise<Integration[]> {
  return authedFetch<Integration[]>("/api/integrations");
}

