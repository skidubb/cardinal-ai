"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export type Correction = {
  id: string;
  text: string;
  scope: string;
  target_id: string | null;
  reason: string | null;
  given_by: string;
  given_at: number | null;
  valid_to: number | null;
};

export default function CorrectionsList({
  byScope,
  scopeOrder,
}: {
  byScope: Record<string, Correction[]>;
  scopeOrder: string[];
}) {
  const router = useRouter();
  const [retiring, setRetiring] = useState<string | null>(null);

  async function retire(id: string) {
    if (!confirm("Retire this correction? It'll no longer apply to future runs.")) return;
    setRetiring(id);
    try {
      await fetch(`/api/proxy/corrections/${id}`, { method: "DELETE" });
      router.refresh();
    } finally {
      setRetiring(null);
    }
  }

  const present = scopeOrder.filter((s) => byScope[s]?.length);

  return (
    <div className="space-y-5">
      {present.map((scope) => (
        <section key={scope} className="space-y-2">
          <h3 className="ce-label">
            {scope}{" "}
            <span className="text-muted-foreground ml-1">({byScope[scope].length})</span>
          </h3>
          <ul className="space-y-2">
            {byScope[scope].map((c) => (
              <li
                key={c.id}
                className="rounded-xl border border-border bg-card p-3 flex items-start justify-between gap-3 transition-colors hover:border-primary/50"
              >
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-foreground text-pretty">{c.text}</div>
                  <div className="text-[10px] text-muted-foreground mt-1 font-mono">
                    {c.target_id ? <span>target: {c.target_id}</span> : null}
                    {c.reason ? <span className="ml-3">why: {c.reason}</span> : null}
                    {c.given_by ? <span className="ml-3">by {c.given_by}</span> : null}
                  </div>
                </div>
                <button
                  onClick={() => retire(c.id)}
                  disabled={retiring === c.id}
                  className="text-[10px] uppercase tracking-wider px-2 py-1 rounded border border-border text-muted-foreground transition-colors hover:text-destructive hover:border-destructive/40 disabled:opacity-40"
                >
                  {retiring === c.id ? "…" : "retire"}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
