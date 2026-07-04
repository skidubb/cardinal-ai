"use client";

import { useState } from "react";
import { Check, ChevronDown, ChevronUp } from "lucide-react";
import type { SuggestedNewAgent } from "@/lib/api";
import { Pill } from "@/components/ui/pill";

type Props = {
  spec: SuggestedNewAgent;
  onCreated: (key: string) => void;
  disabled?: boolean;
};

export function SuggestedAgentCard({ spec, onCreated, disabled = false }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function createAndUse() {
    setBusy(true);
    setError(null);
    try {
      const resp = await fetch("/api/proxy/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(spec),
      });
      if (!resp.ok && resp.status !== 409) {
        const text = await resp.text().catch(() => "");
        throw new Error(`${resp.status}: ${text.slice(0, 300)}`);
      }
      setCreated(true);
      onCreated(spec.key);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const promptPreview = spec.system_prompt.slice(0, 160);
  const hasMore = spec.system_prompt.length > promptPreview.length;

  return (
    <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-semibold text-foreground">{spec.name}</span>
            <Pill tone="muted">{spec.category}</Pill>
            <Pill tone="light">{spec.model}</Pill>
          </div>
          <span className="mt-0.5 block font-mono text-[11px] text-muted-foreground">
            {spec.key}
          </span>
        </div>
        <button
          type="button"
          onClick={createAndUse}
          disabled={disabled || busy || created}
          className={`inline-flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 ${
            created
              ? "border border-[rgb(var(--ce-green-500))]/40 bg-[rgb(var(--ce-green-500))]/10 text-[rgb(var(--ce-green-500))]"
              : "bg-primary text-primary-foreground hover:bg-[rgb(var(--ce-indigo-500))]"
          }`}
        >
          {created ? (
            <>
              <Check size={12} /> Added
            </>
          ) : busy ? (
            "Creating…"
          ) : (
            "Create & use"
          )}
        </button>
      </div>

      {spec.tools.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {spec.tools.map((t) => (
            <span
              key={t}
              className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
            >
              {t}
            </span>
          ))}
        </div>
      ) : null}

      <p className="text-xs leading-relaxed text-muted-foreground text-pretty">
        {spec.rationale}
      </p>

      <div>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
        >
          {expanded ? (
            <>
              <ChevronUp size={11} /> Hide prompt
            </>
          ) : (
            <>
              <ChevronDown size={11} /> Show prompt
            </>
          )}
        </button>
        {expanded ? (
          <p className="mt-1.5 whitespace-pre-wrap rounded-md border border-border bg-background p-2.5 font-mono text-[11px] leading-relaxed text-foreground">
            {spec.system_prompt}
          </p>
        ) : hasMore ? (
          <p className="mt-1 font-mono text-[11px] text-muted-foreground">
            {promptPreview}…
          </p>
        ) : null}
      </div>

      {error ? <div className="text-[11px] text-destructive">{error}</div> : null}
    </div>
  );
}
