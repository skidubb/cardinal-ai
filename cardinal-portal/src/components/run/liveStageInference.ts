import type { Stage } from "./ProtocolDiagram";

export type LiveEvent = {
  event: string;
  data: Record<string, unknown>;
};

export type LiveStageState = {
  activeStageKey: string | null;
  completedStageKeys: string[];
};

const keyOf = (s: Stage, idx: number) => s.key ?? `stage-${idx}`;

/**
 * Coarse-grained stage inference from SSE events.
 *
 * Rules:
 *  - No events yet: nothing highlighted.
 *  - agent_output events: highlight the agent-type stage whose ordinal
 *    equals max round seen (clamped). Earlier mechanical stages and
 *    earlier-ordinal agent stages are marked completed.
 *  - synthesis event: synthesis-type stage active; agent stages visited
 *    so far (ordinal <= maxRound) are completed. Stages never visited
 *    (e.g. "closing" when rounds=2) stay pending.
 *  - run_complete / error: synthesis marked completed, no active stage.
 */
export function inferLiveStage(
  stages: Stage[],
  events: LiveEvent[],
): LiveStageState {
  if (stages.length === 0 || events.length === 0) {
    return { activeStageKey: null, completedStageKeys: [] };
  }

  const agentStageIdxs = stages
    .map((s, i) => (s.stage_type === "agent" ? i : -1))
    .filter((i) => i >= 0);
  const synthesisIdx = stages.findIndex((s) => s.stage_type === "synthesis");

  const agentEvents = events.filter((e) => e.event === "agent_output");
  const maxRound = agentEvents.reduce((acc, e) => {
    const r = typeof e.data.round === "number" ? e.data.round : 0;
    return Math.max(acc, r);
  }, 0);

  const hasSynthesis = events.some((e) => e.event === "synthesis");
  const hasRunComplete = events.some(
    (e) => e.event === "run_complete" || e.event === "error" || e.event === "router_error",
  );

  const visitedAgentStageIdxs = agentStageIdxs.filter((_, ord) => ord <= maxRound);
  const leadingMechanicalIdxs = stages
    .slice(0, agentStageIdxs[0] ?? stages.length)
    .map((_, i) => i);

  if (hasRunComplete) {
    const completed = new Set<string>();
    for (const i of leadingMechanicalIdxs) completed.add(keyOf(stages[i], i));
    if (agentEvents.length > 0) {
      for (const i of visitedAgentStageIdxs) completed.add(keyOf(stages[i], i));
    }
    if (hasSynthesis && synthesisIdx >= 0) {
      completed.add(keyOf(stages[synthesisIdx], synthesisIdx));
    }
    return { activeStageKey: null, completedStageKeys: Array.from(completed) };
  }

  if (hasSynthesis && synthesisIdx >= 0) {
    const completed = new Set<string>();
    for (const i of leadingMechanicalIdxs) completed.add(keyOf(stages[i], i));
    for (const i of visitedAgentStageIdxs) completed.add(keyOf(stages[i], i));
    return {
      activeStageKey: keyOf(stages[synthesisIdx], synthesisIdx),
      completedStageKeys: Array.from(completed),
    };
  }

  if (agentEvents.length > 0 && agentStageIdxs.length > 0) {
    const targetOrdinal = Math.min(agentStageIdxs.length - 1, maxRound);
    const activeIdx = agentStageIdxs[targetOrdinal];
    const completed = new Set<string>();
    for (const i of leadingMechanicalIdxs) completed.add(keyOf(stages[i], i));
    for (let ord = 0; ord < targetOrdinal; ord++) {
      const idx = agentStageIdxs[ord];
      completed.add(keyOf(stages[idx], idx));
    }
    return {
      activeStageKey: keyOf(stages[activeIdx], activeIdx),
      completedStageKeys: Array.from(completed),
    };
  }

  // Run started but no agent/synthesis events yet — highlight first stage.
  return {
    activeStageKey: keyOf(stages[0], 0),
    completedStageKeys: [],
  };
}
