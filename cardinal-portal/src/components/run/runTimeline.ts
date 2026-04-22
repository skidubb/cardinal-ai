/**
 * Pure derivation: SSE event sequence → unified timeline state for the
 * heartbeat, activity log, and per-stage summary on the protocol diagram.
 *
 * The backend emits a rich vocabulary (run_start, agent_roster, agent_start,
 * agent_done, tool_call, agent_output, synthesis, judge_verdict, run_complete,
 * error, stage, context_processing, router_decision). This builder consumes
 * all of them and folds them into one easy-to-render structure so each UI
 * surface stays presentational.
 *
 * Timestamps come from receivedAt (set in handleEvent at ingest time) — the
 * server payloads themselves don't include wall-clock times, so we derive
 * elapsed durations from event arrival order on the client.
 */

export type TimelineEvent = {
  event: string;
  data: Record<string, unknown>;
  receivedAt: number;
};

export type AgentRosterEntry = { key: string; name?: string };

export type ToolChip = {
  toolName: string;
  inputSummary: string | null;
  iteration: number;
  receivedAt: number;
};

export type AgentRow = {
  key: string;
  displayName: string;
  status: "idle" | "thinking" | "done" | "error";
  toolCalls: ToolChip[];
  startedAt: number | null;
  finishedAt: number | null;
  costUsd?: number;
  inputTokens?: number;
  outputTokens?: number;
  text?: string;
};

export type SynthesisRow = {
  text: string;
  receivedAt: number;
  verdict?: {
    completeness?: number;
    consistency?: number;
    actionability?: number;
    overall?: number;
    recommendation?: string;
  };
};

export type RunTimeline = {
  status: "idle" | "running" | "done" | "error";
  startedAt: number | null;
  endedAt: number | null;
  activeAgent: string | null;
  activeTool: { agentName: string; toolName: string } | null;
  stageMessage: string | null;
  contextNote: string | null;
  routerDecision: { protocolId: string; rationale: string | null } | null;
  agents: AgentRow[];
  synthesis: SynthesisRow | null;
  error: string | null;
  eventCount: number;
};

const EMPTY: RunTimeline = {
  status: "idle",
  startedAt: null,
  endedAt: null,
  activeAgent: null,
  activeTool: null,
  stageMessage: null,
  contextNote: null,
  routerDecision: null,
  agents: [],
  synthesis: null,
  error: null,
  eventCount: 0,
};

function asString(v: unknown, fallback = ""): string {
  return typeof v === "string" ? v : fallback;
}

function asNumber(v: unknown): number | undefined {
  return typeof v === "number" && Number.isFinite(v) ? v : undefined;
}

function summarizeToolInput(input: unknown): string | null {
  if (input == null) return null;
  if (typeof input === "string") return input.slice(0, 80);
  if (typeof input === "object") {
    const obj = input as Record<string, unknown>;
    const firstKey = Object.keys(obj)[0];
    if (!firstKey) return null;
    const val = obj[firstKey];
    const valStr = typeof val === "string" ? val : JSON.stringify(val);
    return `${firstKey}: ${valStr.slice(0, 70)}`;
  }
  return String(input).slice(0, 80);
}

export function buildRunTimeline(
  events: TimelineEvent[],
  initialRoster: AgentRosterEntry[] = [],
): RunTimeline {
  if (events.length === 0 && initialRoster.length === 0) return EMPTY;

  const agentMap = new Map<string, AgentRow>();
  const upsertAgent = (key: string, displayName?: string): AgentRow => {
    const k = key.toLowerCase();
    let row = agentMap.get(k);
    if (!row) {
      row = {
        key: k,
        displayName: displayName || key,
        status: "idle",
        toolCalls: [],
        startedAt: null,
        finishedAt: null,
      };
      agentMap.set(k, row);
    } else if (displayName && row.displayName === row.key) {
      row.displayName = displayName;
    }
    return row;
  };

  for (const a of initialRoster) {
    upsertAgent(a.key, a.name);
  }

  let status: RunTimeline["status"] = "idle";
  let startedAt: number | null = null;
  let endedAt: number | null = null;
  let activeAgent: string | null = null;
  let activeTool: RunTimeline["activeTool"] = null;
  let stageMessage: string | null = null;
  let contextNote: string | null = null;
  let routerDecision: RunTimeline["routerDecision"] = null;
  let synthesis: SynthesisRow | null = null;
  let error: string | null = null;

  for (const ev of events) {
    const d = ev.data;
    switch (ev.event) {
      case "run_start": {
        if (status === "idle") status = "running";
        if (startedAt === null) startedAt = ev.receivedAt;
        break;
      }
      case "agent_roster": {
        const roster = Array.isArray(d.agents) ? d.agents : [];
        for (const a of roster) {
          if (a && typeof a === "object") {
            const obj = a as Record<string, unknown>;
            const k = asString(obj.key);
            if (k) upsertAgent(k, asString(obj.name) || k);
          }
        }
        break;
      }
      case "stage": {
        const msg = asString(d.message);
        if (msg) stageMessage = msg;
        break;
      }
      case "context_processing": {
        const files = Array.isArray(d.files) ? d.files.length : 0;
        const msg = asString(d.message);
        contextNote = msg || (files > 0 ? `Ingesting ${files} file${files === 1 ? "" : "s"}…` : null);
        break;
      }
      case "router_decision": {
        const plan = d.plan && typeof d.plan === "object" ? (d.plan as Record<string, unknown>) : null;
        const protocolId = asString(plan?.protocol_id) || asString(d.protocol_id);
        if (protocolId) {
          routerDecision = {
            protocolId,
            rationale: asString(d.rationale) || asString(plan?.rationale) || null,
          };
        }
        break;
      }
      case "agent_start": {
        const name = asString(d.agent_name);
        if (!name) break;
        const row = upsertAgent(name);
        if (row.status !== "done") row.status = "thinking";
        if (row.startedAt === null) row.startedAt = ev.receivedAt;
        activeAgent = name;
        break;
      }
      case "agent_done": {
        const name = asString(d.agent_name);
        if (!name) break;
        const row = upsertAgent(name);
        row.status = "done";
        row.finishedAt = ev.receivedAt;
        if (activeAgent && activeAgent.toLowerCase() === name.toLowerCase()) {
          activeAgent = null;
        }
        if (activeTool && activeTool.agentName.toLowerCase() === name.toLowerCase()) {
          activeTool = null;
        }
        break;
      }
      case "tool_call": {
        const agentName = asString(d.agent_name);
        const toolName = asString(d.tool_name);
        if (!agentName || !toolName) break;
        const row = upsertAgent(agentName);
        row.toolCalls.push({
          toolName,
          inputSummary: summarizeToolInput(d.tool_input),
          iteration: asNumber(d.iteration) ?? row.toolCalls.length + 1,
          receivedAt: ev.receivedAt,
        });
        activeTool = { agentName, toolName };
        break;
      }
      case "agent_output": {
        const key = asString(d.agent_key) || asString(d.agent_name);
        if (!key) break;
        const row = upsertAgent(key);
        row.status = "done";
        if (row.finishedAt === null) row.finishedAt = ev.receivedAt;
        row.costUsd = asNumber(d.cost_usd);
        row.inputTokens = asNumber(d.input_tokens);
        row.outputTokens = asNumber(d.output_tokens);
        const text = asString(d.text) || asString(d.output_text);
        if (text) row.text = text;
        break;
      }
      case "synthesis": {
        synthesis = {
          text: asString(d.text),
          receivedAt: ev.receivedAt,
        };
        activeAgent = null;
        activeTool = null;
        break;
      }
      case "judge_verdict": {
        if (synthesis) {
          synthesis.verdict = {
            completeness: asNumber(d.completeness),
            consistency: asNumber(d.consistency),
            actionability: asNumber(d.actionability),
            overall: asNumber(d.overall),
            recommendation: asString(d.recommendation) || undefined,
          };
        }
        break;
      }
      case "run_complete": {
        status = error ? "error" : "done";
        endedAt = ev.receivedAt;
        activeAgent = null;
        activeTool = null;
        for (const row of agentMap.values()) {
          if (row.status === "thinking") row.status = "done";
          if (row.startedAt !== null && row.finishedAt === null) {
            row.finishedAt = ev.receivedAt;
          }
        }
        break;
      }
      case "error":
      case "router_error": {
        status = "error";
        endedAt = ev.receivedAt;
        error = asString(d.message) || asString(d.error) || "Run failed";
        if (activeAgent) {
          const row = agentMap.get(activeAgent.toLowerCase());
          if (row) {
            row.status = "error";
            row.finishedAt = ev.receivedAt;
          }
        }
        activeAgent = null;
        activeTool = null;
        break;
      }
    }
  }

  if (status === "idle" && events.length > 0) status = "running";

  return {
    status,
    startedAt,
    endedAt,
    activeAgent,
    activeTool,
    stageMessage,
    contextNote,
    routerDecision,
    agents: Array.from(agentMap.values()),
    synthesis,
    error,
    eventCount: events.length,
  };
}

/**
 * Helper: per-stage activity summary derived from the timeline. Maps a stage
 * (by ordinal among agent-type stages) to its agent's tool count + elapsed.
 * Used by ProtocolDiagram to render "{agentName} · {n} tools · {s}s" under
 * the stage name when active.
 */
export function summarizeStageActivity(
  timeline: RunTimeline,
  stageAgentOrdinal: number,
): { agentName: string; toolCount: number; elapsedMs: number | null } | null {
  const agent = timeline.agents[stageAgentOrdinal];
  if (!agent) return null;
  const elapsedMs =
    agent.startedAt !== null
      ? (agent.finishedAt ?? Date.now()) - agent.startedAt
      : null;
  return {
    agentName: agent.displayName,
    toolCount: agent.toolCalls.length,
    elapsedMs,
  };
}
