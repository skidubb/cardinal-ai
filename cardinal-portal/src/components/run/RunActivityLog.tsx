"use client";

import { useState } from "react";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  Loader,
  Sparkles,
} from "lucide-react";
import type { AgentRow, RunTimeline } from "./runTimeline";
import { iconForTool } from "./toolIcon";

type Props = {
  timeline: RunTimeline;
  defaultOpen?: boolean;
};

function formatElapsed(ms: number | null): string {
  if (ms === null) return "—";
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(s < 10 ? 1 : 0)}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${Math.floor(s % 60)}s`;
}

export function RunActivityLog({ timeline, defaultOpen = true }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const { agents, synthesis, status, error } = timeline;

  const visibleAgents = agents.filter((a) => a.status !== "idle" || a.toolCalls.length > 0);
  if (visibleAgents.length === 0 && !synthesis && status === "idle" && !error) {
    return null;
  }

  const totalCost = agents.reduce((acc, a) => acc + (a.costUsd ?? 0), 0);
  const totalToolCalls = agents.reduce((acc, a) => acc + a.toolCalls.length, 0);

  return (
    <div className="rounded-xl border border-border bg-card">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 p-3 text-left transition-colors hover:bg-secondary/40"
      >
        <span className="flex items-center gap-2">
          {open ? (
            <ChevronDown size={14} className="text-muted-foreground" />
          ) : (
            <ChevronRight size={14} className="text-muted-foreground" />
          )}
          <span className="ce-label">Activity log</span>
          <span className="text-[10px] text-muted-foreground">
            {visibleAgents.length} agent{visibleAgents.length === 1 ? "" : "s"}
            {totalToolCalls > 0 ? ` · ${totalToolCalls} tools` : ""}
            {totalCost > 0 ? ` · $${totalCost.toFixed(4)}` : ""}
          </span>
        </span>
      </button>

      {open ? (
        <ol className="divide-y divide-border border-t border-border">
          {visibleAgents.map((agent) => (
            <li key={agent.key} className="anim-fade-in-up">
              <AgentLogRow agent={agent} />
            </li>
          ))}
          {synthesis ? (
            <li className="anim-fade-in-up">
              <SynthesisLogRow timeline={timeline} />
            </li>
          ) : null}
          {error ? (
            <li className="anim-fade-in-up bg-destructive/5 px-4 py-3">
              <div className="flex items-start gap-2 text-xs text-destructive">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                <span className="leading-relaxed">{error}</span>
              </div>
            </li>
          ) : null}
        </ol>
      ) : null}
    </div>
  );
}

function AgentLogRow({ agent }: { agent: AgentRow }) {
  const elapsed =
    agent.startedAt !== null ? (agent.finishedAt ?? Date.now()) - agent.startedAt : null;

  return (
    <div className="px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <AgentStatusGlyph status={agent.status} />
          <span className="font-mono text-sm text-foreground">{agent.displayName}</span>
          {agent.status === "thinking" ? (
            <span className="text-[11px] italic text-muted-foreground">thinking…</span>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-2 font-mono text-[10px] tabular-nums text-muted-foreground">
          {elapsed !== null ? <span>{formatElapsed(elapsed)}</span> : null}
          {agent.costUsd ? <span>${agent.costUsd.toFixed(4)}</span> : null}
          {agent.outputTokens ? <span>{agent.outputTokens}↑</span> : null}
        </div>
      </div>
      {agent.toolCalls.length > 0 ? (
        <ul className="mt-2 flex flex-wrap gap-1.5 pl-7">
          {agent.toolCalls.map((tc, i) => {
            const Icon = iconForTool(tc.toolName);
            return (
              <li
                key={`${tc.toolName}-${tc.iteration}-${i}`}
                className="anim-fade-in-up inline-flex items-center gap-1 rounded-md border border-border bg-background px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                title={tc.inputSummary ?? tc.toolName}
              >
                <Icon size={10} className="text-primary" />
                <span className="text-foreground">{tc.toolName}</span>
                {tc.inputSummary ? (
                  <span className="hidden max-w-[20ch] truncate text-muted-foreground sm:inline">
                    · {tc.inputSummary}
                  </span>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

function SynthesisLogRow({ timeline }: { timeline: RunTimeline }) {
  const { synthesis, status } = timeline;
  if (!synthesis) return null;
  const isLive = status === "running" && !synthesis.verdict;
  return (
    <div className="bg-[rgb(var(--ce-green-500))]/5 px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {isLive ? (
            <Loader size={14} className="anim-spin-slow text-[rgb(var(--ce-green-500))]" />
          ) : (
            <Sparkles size={14} className="text-[rgb(var(--ce-green-500))]" />
          )}
          <span className="font-mono text-sm text-[rgb(var(--ce-green-500))]">synthesis</span>
          {isLive ? (
            <span className="text-[11px] italic text-muted-foreground">composing…</span>
          ) : null}
        </div>
        {synthesis.verdict ? (
          <div className="flex items-center gap-2 font-mono text-[10px] tabular-nums text-muted-foreground">
            {typeof synthesis.verdict.overall === "number" ? (
              <span title="Judge overall score">{synthesis.verdict.overall.toFixed(2)}</span>
            ) : null}
            {synthesis.verdict.recommendation ? (
              <span
                className={[
                  "rounded-full border px-1.5 py-0.5 text-[9px] uppercase tracking-wider",
                  synthesis.verdict.recommendation === "accept"
                    ? "border-[rgb(var(--ce-green-500))]/40 bg-[rgb(var(--ce-green-500))]/10 text-[rgb(var(--ce-green-500))]"
                    : "border-[rgb(var(--ce-yellow-500))]/40 bg-[rgb(var(--ce-yellow-500))]/10 text-[rgb(var(--ce-yellow-500))]",
                ].join(" ")}
              >
                {synthesis.verdict.recommendation}
              </span>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function AgentStatusGlyph({ status }: { status: AgentRow["status"] }) {
  if (status === "thinking") {
    return (
      <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center text-primary">
        <Loader size={12} className="anim-spin-slow" />
      </span>
    );
  }
  if (status === "done") {
    return (
      <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[rgb(var(--ce-green-500))]/15 text-[rgb(var(--ce-green-500))]">
        <Check size={12} strokeWidth={3} />
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-destructive/15 text-destructive">
        <AlertTriangle size={12} strokeWidth={2.5} />
      </span>
    );
  }
  return <span className="inline-block h-5 w-5 shrink-0 rounded-full border border-border" />;
}
