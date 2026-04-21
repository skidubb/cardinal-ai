"use client";

import { Sparkles } from "lucide-react";
import type { RouterDecision } from "@/lib/api";

const tierStyles: Record<RouterDecision["tier"], string> = {
  high: "bg-[rgb(var(--ce-green-500))]/15 text-[rgb(var(--ce-green-500))] border-[rgb(var(--ce-green-500))]/30",
  medium:
    "bg-[rgb(var(--ce-yellow-500))]/15 text-[rgb(var(--ce-yellow-500))] border-[rgb(var(--ce-yellow-500))]/30",
  low: "bg-destructive/15 text-destructive border-destructive/30",
};

export function RouterDecisionCard({
  decision,
  loading,
}: {
  decision: RouterDecision | null;
  loading: boolean;
}) {
  if (!decision && !loading) return null;

  if (loading && !decision) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-primary/30 bg-primary/5 p-4">
        <Sparkles size={16} className="animate-pulse text-primary" />
        <span className="text-sm text-muted-foreground">Router is classifying your question…</span>
      </div>
    );
  }

  if (!decision) return null;

  const { problem_type, confidence, tier, reasoning, plan, adjustments } = decision;

  return (
    <div className="rounded-xl border border-primary/30 bg-primary/5 p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-primary" />
          <span className="ce-eyebrow">Router decision</span>
          {loading ? (
            <span className="text-[10px] text-muted-foreground">(refining…)</span>
          ) : null}
        </div>
        <span
          className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${tierStyles[tier]}`}
        >
          {tier} · {confidence}/100
        </span>
      </div>

      {plan ? (
        <div>
          <div className="text-base font-bold tracking-tight text-foreground">
            {plan.name}{" "}
            <span className="ml-2 font-mono text-xs font-normal text-muted-foreground">
              {plan.protocol_id}
            </span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
            <span className="ce-label">Agents</span>
            {plan.agent_keys.map((a) => (
              <span key={a} className="rounded-full bg-secondary px-2 py-0.5 font-mono text-[10px]">
                {a}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-sm text-destructive">
          Router couldn&apos;t find a routable protocol for this question.
        </div>
      )}

      <div className="grid gap-1 text-xs text-muted-foreground md:grid-cols-2">
        <div>
          <span className="ce-label">Problem type</span>
          <div className="mt-0.5 font-mono text-foreground">{problem_type}</div>
        </div>
        {adjustments?.length ? (
          <div>
            <span className="ce-label">Adjustments</span>
            <div className="mt-0.5 text-foreground">{adjustments.join(" · ")}</div>
          </div>
        ) : null}
      </div>

      {reasoning ? (
        <details className="text-xs">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
            Why this protocol
          </summary>
          <p className="mt-2 leading-relaxed text-foreground text-pretty">{reasoning}</p>
        </details>
      ) : null}
    </div>
  );
}
