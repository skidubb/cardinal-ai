// Typed fetch wrapper that calls the Railway FastAPI backend with the
// active user's Clerk JWT attached. Use from Server Components / Server Actions.
//
// Maps to the existing CE - Multi-Agent Orchestration API. The product surface
// is protocols + agents + runs + reports — the knowledge graph is one of the
// stores backing the agents, not the front door.

import { auth } from "@clerk/nextjs/server";

const API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

async function authedFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const { getToken } = await auth();
  const token = await getToken({ template: "ce-railway" }).catch(() => null);

  const res = await fetch(`${API_BASE}${path}`, {
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
  }>;
  steps?: Array<{ id: number; step_order: number; protocol_key: string; status: string }>;
  error_message?: string | null;
}> {
  return authedFetch(`/api/runs/${id}`);
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
};

export async function fetchProtocols(): Promise<Protocol[]> {
  return authedFetch<Protocol[]>("/api/protocols");
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

// ---- Knowledge graph stats (the fuel layer, not the front door) ----

export type GraphStats = Record<string, number>;

export async function fetchGraphStats(): Promise<GraphStats> {
  return authedFetch<GraphStats>("/api/graph/stats");
}
