"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo, useTransition } from "react";
import { PatternIcon } from "@/components/run/PatternIcon";
import {
  PATTERN_DESC,
  PATTERN_LABEL,
  type OrchestrationPattern,
} from "@/components/run/orchestrationPattern";

const ORDER: OrchestrationPattern[] = [
  "single_agent",
  "sequence",
  "parallel",
  "hub_and_spoke",
  "hybrid_matrix",
  "decentralized",
];

const PARAM = "patterns";

export function patternsFromSearchParams(
  raw: string | string[] | undefined,
): Set<OrchestrationPattern> {
  const value = Array.isArray(raw) ? raw.join(",") : raw ?? "";
  const tokens = value
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean) as OrchestrationPattern[];
  return new Set(tokens.filter((t) => ORDER.includes(t)));
}

export function PatternFilter({ counts }: { counts: Record<OrchestrationPattern, number> }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [pending, startTransition] = useTransition();

  const selected = useMemo(
    () => patternsFromSearchParams(searchParams.get(PARAM) ?? undefined),
    [searchParams],
  );

  const total = useMemo(() => Object.values(counts).reduce((a, b) => a + b, 0), [counts]);

  const applyNext = useCallback(
    (next: Set<OrchestrationPattern>) => {
      const params = new URLSearchParams(searchParams.toString());
      if (next.size === 0) {
        params.delete(PARAM);
      } else {
        params.set(PARAM, ORDER.filter((p) => next.has(p)).join(","));
      }
      const qs = params.toString();
      startTransition(() => {
        router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
      });
    },
    [pathname, router, searchParams],
  );

  const toggle = useCallback(
    (p: OrchestrationPattern) => {
      const next = new Set(selected);
      if (next.has(p)) next.delete(p);
      else next.add(p);
      applyNext(next);
    },
    [selected, applyNext],
  );

  const clear = useCallback(() => applyNext(new Set()), [applyNext]);

  const allActive = selected.size === 0; // no filter == show all

  return (
    <div
      className={`flex flex-wrap items-center gap-2 rounded-xl border border-border bg-card/60 p-3 ${
        pending ? "opacity-70" : ""
      }`}
      aria-label="Filter protocols by orchestration pattern"
    >
      <span className="ce-label text-xs mr-1">Filter by pattern</span>

      <button
        type="button"
        onClick={clear}
        disabled={allActive}
        className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors border ${
          allActive
            ? "border-primary/60 bg-primary/10 text-primary cursor-default"
            : "border-border bg-transparent text-muted-foreground hover:border-primary/50 hover:text-foreground"
        }`}
        title={`All ${total} protocols`}
      >
        All
        <span className="text-[10px] font-mono opacity-70">{total}</span>
      </button>

      {ORDER.map((p) => {
        const n = counts[p] ?? 0;
        const active = selected.has(p);
        const disabled = n === 0;
        return (
          <button
            key={p}
            type="button"
            onClick={() => toggle(p)}
            disabled={disabled}
            aria-pressed={active}
            title={PATTERN_DESC[p]}
            className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors border ${
              disabled
                ? "border-border/40 text-muted-foreground/40 cursor-not-allowed"
                : active
                  ? "border-primary/60 bg-primary/10 text-primary"
                  : "border-border bg-transparent text-muted-foreground hover:border-primary/50 hover:text-foreground"
            }`}
          >
            <PatternIcon pattern={p} size={13} />
            <span>{PATTERN_LABEL[p]}</span>
            <span className="text-[10px] font-mono opacity-70">{n}</span>
          </button>
        );
      })}

      {selected.size > 0 ? (
        <button
          type="button"
          onClick={clear}
          className="text-[11px] text-muted-foreground hover:text-foreground underline underline-offset-4 ml-auto"
        >
          Clear ({selected.size})
        </button>
      ) : null}
    </div>
  );
}
