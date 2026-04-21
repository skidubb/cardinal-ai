"use client";

import { useEffect, useState } from "react";

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
};

export function ProtocolDiagram({
  protocolKey,
  initialData,
  activeStageKey = null,
  completedStageKeys = [],
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

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <div className="ce-label">How this protocol runs</div>
          <div className="mt-0.5 text-xs text-muted-foreground">
            {stages.length} stage{stages.length === 1 ? "" : "s"} · {sourceLabel}
            {isLive ? " · live" : ""}
          </div>
        </div>
      </div>
      <ol className="space-y-2">
        {stages.map((s, i) => {
          const key = s.key ?? `stage-${i}`;
          const state = isLive
            ? activeStageKey === key
              ? "active"
              : completedStageKeys.includes(key)
                ? "done"
                : "pending"
            : "idle";
          return <StageRow key={key} stage={s} index={i} state={state} />;
        })}
      </ol>
    </div>
  );
}

type StageState = "idle" | "pending" | "active" | "done";

function StageRow({
  stage,
  index,
  state,
}: {
  stage: Stage;
  index: number;
  state: StageState;
}) {
  const [open, setOpen] = useState(false);
  const typeStyle =
    stage.stage_type === "agent"
      ? "border-primary/40 bg-primary/5 text-primary"
      : stage.stage_type === "synthesis"
        ? "border-[rgb(var(--ce-green-500))]/40 bg-[rgb(var(--ce-green-500))]/5 text-[rgb(var(--ce-green-500))]"
        : "border-border bg-secondary text-muted-foreground";
  const stateStyle =
    state === "active"
      ? "ring-2 ring-primary ring-offset-2 ring-offset-card"
      : state === "done"
        ? "opacity-60"
        : "";

  return (
    <li className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`group flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-all ${typeStyle} ${stateStyle}`}
        aria-expanded={open}
      >
        <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-background font-mono text-[11px] font-semibold text-foreground">
          {index + 1}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-foreground">{stage.name}</span>
            <span className="shrink-0 text-[10px] uppercase tracking-wider text-muted-foreground">
              {stage.stage_type}
              {state === "active" ? " · running" : state === "done" ? " · done" : ""}
            </span>
          </div>
          {stage.description ? (
            <p
              className={`mt-1 text-xs leading-relaxed text-muted-foreground ${open ? "" : "line-clamp-1"}`}
            >
              {stage.description}
            </p>
          ) : null}
        </div>
      </button>
      {index < 99 ? (
        <div className="ml-[22px] h-2 w-px bg-border" aria-hidden="true" />
      ) : null}
    </li>
  );
}
