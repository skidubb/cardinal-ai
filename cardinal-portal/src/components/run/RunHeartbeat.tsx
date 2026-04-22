"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Check, Loader } from "lucide-react";
import type { RunTimeline } from "./runTimeline";
import { iconForTool } from "./toolIcon";

type Props = {
  timeline: RunTimeline;
};

function formatElapsed(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(s < 10 ? 1 : 0)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.floor(s % 60);
  return `${m}m ${rem}s`;
}

export function RunHeartbeat({ timeline }: Props) {
  const { status, startedAt, endedAt, activeAgent, activeTool, stageMessage, contextNote, routerDecision, eventCount, agents, error } =
    timeline;

  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (status !== "running") return;
    const id = window.setInterval(() => setNow(Date.now()), 200);
    return () => window.clearInterval(id);
  }, [status]);

  const elapsed =
    startedAt !== null ? (endedAt ?? now) - startedAt : 0;

  if (status === "idle") return null;

  const totalToolCalls = agents.reduce((acc, a) => acc + a.toolCalls.length, 0);

  return (
    <div
      role="status"
      aria-live="polite"
      className={[
        "sticky top-0 z-10 flex items-center justify-between gap-3 rounded-xl border px-4 py-2.5",
        status === "error"
          ? "border-destructive/40 bg-destructive/10 text-destructive"
          : status === "done"
            ? "border-[rgb(var(--ce-green-500))]/40 bg-[rgb(var(--ce-green-500))]/5 text-foreground"
            : "border-primary/40 bg-primary/5 text-foreground",
      ].join(" ")}
    >
      <div className="flex min-w-0 items-center gap-3 text-sm">
        <StatusGlyph status={status} />
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <PrimaryLabel
            status={status}
            activeAgent={activeAgent}
            stageMessage={stageMessage}
            contextNote={contextNote}
            routerDecision={routerDecision}
            error={error}
          />
          {activeTool && status === "running" ? (
            <ToolPill agentName={activeTool.agentName} toolName={activeTool.toolName} />
          ) : null}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3 font-mono text-[11px] tabular-nums text-muted-foreground">
        {elapsed > 0 ? <span>{formatElapsed(elapsed)}</span> : null}
        {totalToolCalls > 0 ? <span>{totalToolCalls} tool{totalToolCalls === 1 ? "" : "s"}</span> : null}
        <span>{eventCount} ev</span>
      </div>
    </div>
  );
}

function StatusGlyph({ status }: { status: RunTimeline["status"] }) {
  if (status === "done") {
    return (
      <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[rgb(var(--ce-green-500))]/20 text-[rgb(var(--ce-green-500))]">
        <Check size={12} strokeWidth={3} />
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-destructive/20 text-destructive">
        <AlertTriangle size={12} strokeWidth={2.5} />
      </span>
    );
  }
  return (
    <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center text-primary">
      <Loader size={14} className="anim-spin-slow" />
    </span>
  );
}

function PrimaryLabel({
  status,
  activeAgent,
  stageMessage,
  contextNote,
  routerDecision,
  error,
}: {
  status: RunTimeline["status"];
  activeAgent: string | null;
  stageMessage: string | null;
  contextNote: string | null;
  routerDecision: RunTimeline["routerDecision"];
  error: string | null;
}) {
  if (status === "error") {
    return (
      <span className="truncate font-medium">
        Run failed{error ? ` · ${error.slice(0, 120)}` : ""}
      </span>
    );
  }
  if (status === "done") {
    return <span className="font-medium">Run complete</span>;
  }
  if (activeAgent) {
    return (
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary anim-pulse-soft" />
        <span className="font-medium">
          <span className="font-mono text-primary">{activeAgent}</span> is thinking
        </span>
      </span>
    );
  }
  if (contextNote) {
    return <span className="truncate text-muted-foreground">{contextNote}</span>;
  }
  if (routerDecision) {
    return (
      <span className="truncate">
        Router chose <span className="font-mono text-primary">{routerDecision.protocolId}</span>
      </span>
    );
  }
  if (stageMessage) {
    return <span className="truncate text-muted-foreground">{stageMessage}</span>;
  }
  return <span className="text-muted-foreground">Starting…</span>;
}

function ToolPill({ agentName, toolName }: { agentName: string; toolName: string }) {
  const Icon = iconForTool(toolName);
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 font-mono text-[10px] text-primary anim-fade-in-up"
      title={`${agentName} → ${toolName}`}
    >
      <Icon size={10} />
      {toolName}
    </span>
  );
}
