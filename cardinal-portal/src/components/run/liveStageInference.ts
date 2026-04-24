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

const slug = (s: string): string =>
  s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");

/**
 * Match an orchestrator-emitted stage name (e.g. "evidence_search") against
 * the YAML stage manifest. Names don't always line up exactly — the YAML
 * tends to be verbose ("Active evidence search"), the span short. Use a
 * substring check on the slugified forms so "evidence_search" hits
 * "active_evidence_search" and "verdict" hits "verdict".
 */
function matchStageIdx(stages: Stage[], stageName: string): number {
  const needle = slug(stageName);
  if (!needle) return -1;
  for (let i = 0; i < stages.length; i++) {
    const haystack = slug(stages[i].key ?? stages[i].name ?? "");
    if (!haystack) continue;
    if (haystack === needle || haystack.includes(needle) || needle.includes(haystack)) {
      return i;
    }
  }
  return -1;
}

/**
 * Coarse-grained stage inference from SSE events.
 *
 * Primary signal: `stage_start` / `stage_complete` events emitted by
 * `protocols/langfuse_tracing.py:create_span` whenever a protocol enters a
 * stage:xxx span. Works for every protocol that uses the span helpers.
 *
 * Fallback (legacy): `agent_output` round_number + `synthesis` event — used
 * for backends that haven't deployed the stage-event emission yet, or for
 * protocols that don't wrap their stages in span helpers.
 *
 * Terminal: `run_complete` marks everything done.
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
  const hasRunComplete = events.some((e) => e.event === "run_complete");
  const hasRunError = events.some(
    (e) => e.event === "error" || e.event === "router_error",
  );

  const visitedAgentStageIdxs = agentStageIdxs.filter((_, ord) => ord <= maxRound);
  const leadingMechanicalIdxs = stages
    .slice(0, agentStageIdxs[0] ?? stages.length)
    .map((_, i) => i);

  // Primary path: stage_start / stage_complete events from the backend.
  const stageEvents = events.filter(
    (e) =>
      e.event === "stage_start" ||
      e.event === "stage_complete" ||
      e.event === "stage_error",
  );
  if (stageEvents.length > 0 && !hasRunComplete) {
    const completedFromStages = new Set<string>();
    let activeFromStages: string | null = null;
    for (const e of stageEvents) {
      const name = typeof e.data.stage_name === "string" ? e.data.stage_name : "";
      const idx = matchStageIdx(stages, name);
      if (idx < 0) continue;
      if (e.event === "stage_start") {
        activeFromStages = keyOf(stages[idx], idx);
      } else {
        completedFromStages.add(keyOf(stages[idx], idx));
        if (activeFromStages === keyOf(stages[idx], idx)) {
          activeFromStages = null;
        }
      }
    }
    // Also complete the synthesis stage when a synthesis event arrives.
    if (hasSynthesis && synthesisIdx >= 0) {
      completedFromStages.add(keyOf(stages[synthesisIdx], synthesisIdx));
    }
    if (activeFromStages || completedFromStages.size > 0) {
      return {
        activeStageKey: activeFromStages,
        completedStageKeys: Array.from(completedFromStages),
      };
    }
  }

  // Successful run ⇒ every required stage ran by definition. The SSE payload
  // only carries `round` (0 for linear non-rounds protocols), so rounds-based
  // inference undercounts agent stages for protocols like P39, P48, P52.
  if (hasRunComplete) {
    const completed = new Set<string>();
    for (let i = 0; i < stages.length; i++) {
      const s = stages[i];
      if (s.stage_type === "synthesis" && !hasSynthesis) continue;
      completed.add(keyOf(s, i));
    }
    return { activeStageKey: null, completedStageKeys: Array.from(completed) };
  }

  // Errored run ⇒ best-effort partial progress from whatever we did observe.
  if (hasRunError) {
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
