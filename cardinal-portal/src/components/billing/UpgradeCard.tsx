"use client";

import Link from "next/link";

export type UpgradeDetail = {
  code: string;
  message: string;
  plan?: string;
  used?: number;
  limit?: number;
  feature?: string;
};

export function UpgradeCard({ code, message, plan, used, limit, feature }: UpgradeDetail) {
  const title = code === "feature_required" ? "Feature not available on your plan" : "Plan limit reached";

  return (
    <div className="rounded-xl border border-primary/40 bg-primary/5 p-5">
      <div className="ce-eyebrow">
        {plan ? `${plan.charAt(0).toUpperCase()}${plan.slice(1)} plan` : "Upgrade required"}
      </div>
      <h3 className="mt-1 text-lg font-semibold tracking-tight text-foreground">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground text-pretty">{message}</p>
      {feature ? (
        <p className="mt-1 font-mono text-xs text-muted-foreground">feature: {feature}</p>
      ) : null}
      {used != null && limit != null ? (
        <p className="mt-1 text-xs text-muted-foreground">
          {used} of {limit} used
        </p>
      ) : null}
      <Link
        href="/billing"
        className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-indigo)] transition-colors hover:bg-[rgb(var(--ce-indigo-500))]"
      >
        View plans
      </Link>
    </div>
  );
}
