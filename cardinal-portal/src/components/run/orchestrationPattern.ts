/**
 * Two derivations off the protocol stage list:
 *
 *   1. Overall orchestration pattern (parallel | hub_and_spoke | hybrid_matrix
 *      | decentralized | pipeline). Inferred from the stage dependency graph
 *      plus the agent fan-out attribute on each agent stage.
 *
 *   2. Per-stage *function* (agent | synthesis | router | eval | input |
 *      mechanical). The backend YAML only has 3 stage_type values (agent /
 *      synthesis / mechanical), so we recover finer function distinctions
 *      from stage names — "Route to Protocol", "Eliminate Weak Hypotheses",
 *      "Calibration Check", "Feature Extraction", etc. — without requiring
 *      a backend schema change.
 *
 * Function maps to a color so the diagram reads like a circuit board: you
 * can tell at a glance which stages are routers, which are scorers, which
 * are aggregators, which produce the final synthesis.
 */

import type { Stage } from "./ProtocolDiagram";

export type OrchestrationPattern =
  | "single_agent"
  | "sequence"
  | "parallel"
  | "hub_and_spoke"
  | "hybrid_matrix"
  | "decentralized";

export type StageFunction =
  | "agent"
  | "synthesis"
  | "router"
  | "eval"
  | "input"
  | "mechanical";

export const PATTERN_LABEL: Record<OrchestrationPattern, string> = {
  single_agent: "Single agent",
  sequence: "Sequence",
  parallel: "Parallel",
  hub_and_spoke: "Hub-and-spoke",
  hybrid_matrix: "Hybrid-matrix",
  decentralized: "Decentralized",
};

export const PATTERN_DESC: Record<OrchestrationPattern, string> = {
  single_agent: "One agent, one call — a direct response with no coordination.",
  sequence: "Stages run in order; each feeds the next. Agent count varies.",
  parallel: "All agents answer at once, one synthesizer merges.",
  hub_and_spoke: "An orchestrator coordinates each step; agents fan out and back in.",
  hybrid_matrix: "Same agents revisit across multiple rounds; positions evolve.",
  decentralized: "Agents talk peer-to-peer; no central synthesizer.",
};

/**
 * Map a function to the visual treatment used by ProtocolDiagram. Returns
 * Tailwind class fragments — kept as an object so multiple call sites stay
 * in sync (border, background tint, accent text, dot color).
 */
export type FunctionStyle = {
  label: string;
  border: string;
  bg: string;
  accent: string;
  dot: string;
};

export const FUNCTION_STYLE: Record<StageFunction, FunctionStyle> = {
  agent: {
    label: "agent",
    border: "border-primary/40",
    bg: "bg-primary/5",
    accent: "text-primary",
    dot: "bg-primary",
  },
  synthesis: {
    label: "synthesis",
    border: "border-[rgb(var(--ce-green-500))]/40",
    bg: "bg-[rgb(var(--ce-green-500))]/5",
    accent: "text-[rgb(var(--ce-green-500))]",
    dot: "bg-[rgb(var(--ce-green-500))]",
  },
  router: {
    label: "router",
    border: "border-[rgb(var(--ce-cyan-400))]/40",
    bg: "bg-[rgb(var(--ce-cyan-400))]/5",
    accent: "text-[rgb(var(--ce-cyan-400))]",
    dot: "bg-[rgb(var(--ce-cyan-400))]",
  },
  eval: {
    label: "eval",
    border: "border-[rgb(var(--ce-yellow-500))]/40",
    bg: "bg-[rgb(var(--ce-yellow-500))]/5",
    accent: "text-[rgb(var(--ce-yellow-500))]",
    dot: "bg-[rgb(var(--ce-yellow-500))]",
  },
  input: {
    label: "input",
    border: "border-[rgb(var(--ce-purple-500))]/40",
    bg: "bg-[rgb(var(--ce-purple-500))]/5",
    accent: "text-[rgb(var(--ce-purple-500))]",
    dot: "bg-[rgb(var(--ce-purple-500))]",
  },
  mechanical: {
    label: "mechanical",
    border: "border-border",
    bg: "bg-secondary",
    accent: "text-muted-foreground",
    dot: "bg-muted-foreground",
  },
};

const ROUTER_RE = /(route|routing|classify|classification|gate|select)/i;
const EVAL_RE = /(eliminate|calibrat|score|judge|verdict|rank|evaluat|prune|filter)/i;
const INPUT_RE = /(extract|ingest|preprocess|prepare|invert|reformulate|summari[sz]e)/i;
const AGGREGATE_RE = /(dedupe|deduplicat|cluster|aggregat|merge|consolidat)/i;

/** Best-effort function classification from stage_type + name. */
export function inferStageFunction(stage: Stage): StageFunction {
  if (stage.stage_type === "agent") return "agent";
  if (stage.stage_type === "synthesis") return "synthesis";
  const name = (stage.name ?? "") + " " + (stage.key ?? "");
  if (ROUTER_RE.test(name)) return "router";
  if (EVAL_RE.test(name)) return "eval";
  if (INPUT_RE.test(name)) return "input";
  if (AGGREGATE_RE.test(name)) return "mechanical";
  return "mechanical";
}

/**
 * Classify the protocol's overall orchestration pattern.
 *
 * Heuristics (same as Python classifier in api/manifest.py):
 *  - agentCount ≤ 1 and at most one agent stage → "single_agent".
 *  - Agent stages but no synthesis stage → "decentralized" (peer-to-peer).
 *  - Agent stage depends on a *prior agent* stage (revisit) → "hybrid_matrix".
 *  - One agent stage + synthesis (with multi-agent) → "parallel".
 *  - Multiple non-chained agent stages + synthesis → "hub_and_spoke".
 *  - Everything else (linear chain, mechanical-only) → "sequence".
 */
export function inferOrchestrationPattern(
  stages: Stage[],
  agentCount: number,
): OrchestrationPattern {
  const agentStages = stages.filter((s) => s.stage_type === "agent");
  const synthesisStages = stages.filter((s) => s.stage_type === "synthesis");

  // Single agent: one agent and no fan-out shape.
  if (agentCount <= 1 && agentStages.length <= 1) {
    return "single_agent";
  }

  if (agentStages.length === 0) return "sequence";

  // Decentralized: agents but no central synthesizer.
  if (synthesisStages.length === 0 && agentStages.length > 1) {
    return "decentralized";
  }

  // Hybrid / matrix: an agent stage depends on a *prior agent stage*.
  if (agentStages.length >= 2) {
    const agentKeys = new Set(
      agentStages.flatMap((s) => [s.key, s.name].filter(Boolean) as string[]),
    );
    const chained = agentStages.some((s) =>
      (s.depends_on ?? []).some((d) => agentKeys.has(d)),
    );
    if (chained) return "hybrid_matrix";
  }

  // Parallel: one agent stage + synthesis, multi-agent.
  if (agentStages.length === 1 && synthesisStages.length >= 1 && agentCount > 1) {
    return "parallel";
  }

  // Hub-and-spoke: multiple non-chained agent stages + synthesis.
  if (agentStages.length >= 2 && synthesisStages.length >= 1) {
    return "hub_and_spoke";
  }

  return "sequence";
}
