"use client";

import { useEffect, useState } from "react";
import { Check, Loader, Network, Repeat, Share2, Workflow } from "lucide-react";
import { iconForTool } from "./toolIcon";
import type { AgentRow, RunTimeline } from "./runTimeline";
import {
  FUNCTION_STYLE,
  PATTERN_DESC,
  PATTERN_LABEL,
  inferOrchestrationPattern,
  inferStageFunction,
  type OrchestrationPattern,
  type StageFunction,
} from "./orchestrationPattern";

type StageType = "agent" | "synthesis" | "mechanical";

export type Stage = {
  key?: string;
  name: string;
  stage_type: StageType | string;
  depends_on?: string[];
  agents_filter?: string | null;
  description?: string;
};

type StagesResponse = {
  protocol_id: string;
  protocol_name: string;
  stages: Stage[];
  source?: "yaml" | "regex" | "fallback";
};

type Props = {
  protocolKey: string;
  /** When provided, skips the internal fetch and uses these stages directly. */
  initialData?: StagesResponse | null;
  /** Override the current active stage (for live runs). */
  activeStageKey?: string | null;
  /** Stages already completed (for live runs). */
  completedStageKeys?: string[];
  /** Live timeline; lets agent-type stages show per-stage activity summary. */
  timeline?: RunTimeline | null;
  /** Number of agents selected — used to render parallelism dots in fan-out stages. */
  agentCount?: number;
};

export function ProtocolDiagram({
  protocolKey,
  initialData,
  activeStageKey = null,
  completedStageKeys = [],
  timeline = null,
  agentCount = 0,
}: Props) {
  const [data, setData] = useState<StagesResponse | null>(initialData ?? null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialData) {
      setData(initialData);
      return;
    }
    if (!protocolKey) return;
    const ctrl = new AbortController();
    setData(null);
    setError(null);
    (async () => {
      try {
        const resp = await fetch(
          `/api/proxy/protocols/${encodeURIComponent(protocolKey)}/stages`,
          { signal: ctrl.signal },
        );
        if (!resp.ok) throw new Error(`${resp.status}`);
        const payload = (await resp.json()) as StagesResponse;
        setData(payload);
      } catch (e) {
        if ((e as { name?: string })?.name !== "AbortError") {
          setError(e instanceof Error ? e.message : String(e));
        }
      }
    })();
    return () => ctrl.abort();
  }, [protocolKey, initialData]);

  if (error) {
    return (
      <div className="rounded-lg border border-border bg-card p-3 text-xs text-muted-foreground">
        Couldn&apos;t load protocol diagram ({error}).
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-lg border border-border bg-card p-3 text-xs text-muted-foreground">
        Loading protocol diagram…
      </div>
    );
  }

  const { stages, source } = data;
  const isLive = !!activeStageKey || completedStageKeys.length > 0;
  const sourceLabel = source === "yaml"
    ? "Curated"
    : source === "regex"
      ? "Auto-extracted"
      : "Inferred";

  const pattern = inferOrchestrationPattern(stages, Math.max(agentCount, 1));
  const fanOutAgents = Math.max(agentCount, 0);

  let prevState: StageState = "idle";
  let agentOrdinal = -1;

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="ce-label">How this protocol runs</div>
          <div className="mt-0.5 text-xs text-muted-foreground">
            {stages.length} stage{stages.length === 1 ? "" : "s"} · {sourceLabel}
            {isLive ? " · live" : ""}
          </div>
        </div>
        <PatternBadge pattern={pattern} agentCount={fanOutAgents} />
      </div>

      <FunctionLegend stages={stages} />

      <ol className="space-y-0">
        {stages.map((s, i) => {
          const key = s.key ?? `stage-${i}`;
          const state: StageState = isLive
            ? activeStageKey === key
              ? "active"
              : completedStageKeys.includes(key)
                ? "done"
                : "pending"
            : "idle";

          const stageFn = inferStageFunction(s);

          let agent: AgentRow | null = null;
          if (s.stage_type === "agent") {
            agentOrdinal++;
            if (timeline && timeline.agents[agentOrdinal]) {
              agent = timeline.agents[agentOrdinal];
            }
          }

          const showConnector = i < stages.length - 1;
          const connectorLit = prevState === "done" || state === "done" || state === "active";
          prevState = state;

          const isFanOut = s.stage_type === "agent" && s.agents_filter === "all" && fanOutAgents > 1;

          return (
            <StageRow
              key={key}
              stage={s}
              index={i}
              state={state}
              fn={stageFn}
              agent={agent}
              showConnector={showConnector}
              connectorLit={connectorLit}
              fanOutCount={isFanOut ? fanOutAgents : 0}
              pattern={pattern}
            />
          );
        })}
      </ol>
    </div>
  );
}

type StageState = "idle" | "pending" | "active" | "done";

const PATTERN_ICON: Record<OrchestrationPattern, typeof Network> = {
  parallel: Share2,
  hub_and_spoke: Network,
  hybrid_matrix: Repeat,
  decentralized: Network,
  pipeline: Workflow,
};

function PatternBadge({
  pattern,
  agentCount,
}: {
  pattern: OrchestrationPattern;
  agentCount: number;
}) {
  const Icon = PATTERN_ICON[pattern];
  return (
    <div
      className="inline-flex max-w-[55%] flex-col items-end gap-0.5 text-right"
      title={PATTERN_DESC[pattern]}
    >
      <span className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-primary">
        <Icon size={10} />
        {PATTERN_LABEL[pattern]}
      </span>
      {agentCount > 1 ? (
        <span className="text-[10px] text-muted-foreground">
          {agentCount} agents fan out per stage
        </span>
      ) : null}
    </div>
  );
}

function FunctionLegend({ stages }: { stages: Stage[] }) {
  const fns = new Set<StageFunction>();
  for (const s of stages) fns.add(inferStageFunction(s));
  if (fns.size <= 1) return null;
  const order: StageFunction[] = ["input", "router", "agent", "eval", "mechanical", "synthesis"];
  const ordered = order.filter((f) => fns.has(f));
  return (
    <div className="mb-3 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
      {ordered.map((f) => {
        const style = FUNCTION_STYLE[f];
        return (
          <span key={f} className="inline-flex items-center gap-1">
            <span className={`inline-block h-1.5 w-1.5 rounded-full ${style.dot}`} />
            <span className={style.accent}>{style.label}</span>
          </span>
        );
      })}
    </div>
  );
}

function StageRow({
  stage,
  index,
  state,
  fn,
  agent,
  showConnector,
  connectorLit,
  fanOutCount,
  pattern,
}: {
  stage: Stage;
  index: number;
  state: StageState;
  fn: StageFunction;
  agent: AgentRow | null;
  showConnector: boolean;
  connectorLit: boolean;
  fanOutCount: number;
  pattern: OrchestrationPattern;
}) {
  const [open, setOpen] = useState(false);
  const style = FUNCTION_STYLE[fn];

  const stateStyle =
    state === "active"
      ? "ring-2 ring-primary ring-offset-2 ring-offset-card shadow-[var(--shadow-indigo)]"
      : state === "done"
        ? "opacity-70"
        : "";

  return (
    <li className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`group relative flex w-full items-start gap-3 overflow-hidden rounded-lg border p-3 text-left transition-all ${style.border} ${style.bg} ${stateStyle}`}
        aria-expanded={open}
      >
        {state === "active" ? (
          <span
            aria-hidden="true"
            className="anim-shimmer pointer-events-none absolute inset-x-0 top-0 h-[2px]"
          />
        ) : null}

        <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-background font-mono text-[11px] font-semibold text-foreground">
          {state === "done" ? (
            <Check size={12} strokeWidth={3} className="anim-fade-in-up text-[rgb(var(--ce-green-500))]" />
          ) : state === "active" ? (
            <Loader size={12} className="anim-spin-slow text-primary" />
          ) : (
            index + 1
          )}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-foreground">{stage.name}</span>
            <span className={`shrink-0 text-[10px] uppercase tracking-wider ${style.accent}`}>
              {style.label}
              {state === "active" ? " · running" : state === "done" ? " · done" : ""}
            </span>
          </div>

          {fanOutCount > 1 ? (
            <FanOutDots count={fanOutCount} dotClass={style.dot} pattern={pattern} />
          ) : null}

          {agent && (state === "active" || state === "done") ? (
            <StageActivitySummary agent={agent} state={state} />
          ) : null}

          {stage.description ? (
            <p
              className={`mt-1 text-xs leading-relaxed text-muted-foreground ${open ? "" : "line-clamp-1"}`}
            >
              {stage.description}
            </p>
          ) : null}
        </div>
      </button>
      {showConnector ? (
        <div className="ml-[22px] flex h-3 items-stretch" aria-hidden="true">
          <span
            className={[
              "block w-px origin-top",
              connectorLit ? "bg-primary anim-draw-line" : "bg-border",
            ].join(" ")}
          />
        </div>
      ) : null}
    </li>
  );
}

function FanOutDots({
  count,
  dotClass,
  pattern,
}: {
  count: number;
  dotClass: string;
  pattern: OrchestrationPattern;
}) {
  const cap = Math.min(count, 8);
  const overflow = count - cap;
  const label = pattern === "hybrid_matrix" ? "per round" : "in parallel";
  return (
    <div className="mt-1.5 flex items-center gap-1.5">
      <div className="flex items-center gap-0.5">
        {Array.from({ length: cap }).map((_, i) => (
          <span
            key={i}
            className={`inline-block h-1.5 w-1.5 rounded-full ${dotClass}`}
            style={{ opacity: 0.4 + (0.6 * (i + 1)) / cap }}
          />
        ))}
        {overflow > 0 ? (
          <span className="ml-1 text-[10px] text-muted-foreground">+{overflow}</span>
        ) : null}
      </div>
      <span className="text-[10px] text-muted-foreground">
        {count} {label}
      </span>
    </div>
  );
}

function StageActivitySummary({ agent, state }: { agent: AgentRow; state: StageState }) {
  const elapsed =
    agent.startedAt !== null ? (agent.finishedAt ?? Date.now()) - agent.startedAt : null;
  const lastTool = agent.toolCalls[agent.toolCalls.length - 1];
  const Icon = lastTool ? iconForTool(lastTool.toolName) : null;
  return (
    <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-muted-foreground">
      <span className="font-mono text-foreground">{agent.displayName}</span>
      {agent.toolCalls.length > 0 ? (
        <span>
          {agent.toolCalls.length} tool{agent.toolCalls.length === 1 ? "" : "s"}
        </span>
      ) : null}
      {elapsed !== null ? <span className="tabular-nums">{Math.round(elapsed / 1000)}s</span> : null}
      {state === "active" && lastTool && Icon ? (
        <span className="anim-fade-in-up inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-1.5 py-0.5 font-mono text-[10px] text-primary">
          <Icon size={9} /> {lastTool.toolName}
        </span>
      ) : null}
    </div>
  );
}
