import type { Usage } from "@/lib/api";

export function UsageMeter({ usage }: { usage: Usage }) {
  const unlimited = usage.runs_limit == null;
  const used = usage.period_runs;
  const pct = unlimited ? 0 : Math.min(100, (used / Math.max(usage.runs_limit ?? 1, 1)) * 100);

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-baseline justify-between">
        <span className="ce-label">Usage this period</span>
        <span className="text-xs text-muted-foreground">
          {new Date(usage.period_start).toLocaleDateString()} &ndash;{" "}
          {new Date(usage.period_end).toLocaleDateString()}
        </span>
      </div>

      <div className="mt-3">
        {unlimited ? (
          <p className="text-sm font-medium text-foreground">Unlimited runs</p>
        ) : (
          <>
            <p className="text-sm font-medium text-foreground">
              {used} of {usage.runs_limit} runs used this month
            </p>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
          </>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground">
        <span>Cost this period: ${usage.period_cost_usd.toFixed(2)}</span>
        {usage.run_cost_cap_usd != null ? (
          <span>Per-run cost cap: ${usage.run_cost_cap_usd.toFixed(2)}</span>
        ) : null}
      </div>
    </div>
  );
}
