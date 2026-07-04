import { auth } from "@clerk/nextjs/server";
import { getRailwayToken, RAILWAY_API_BASE } from "@/lib/railway";
import NewCorrectionForm from "./NewCorrectionForm";
import CorrectionsList, { type Correction } from "./CorrectionsList";

async function loadCorrections(): Promise<{ corrections: Correction[]; error: string | null }> {
  try {
    const token = await getRailwayToken();
    const resp = await fetch(`${RAILWAY_API_BASE}/api/corrections?active_only=true`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    });
    if (!resp.ok) {
      return { corrections: [], error: `${resp.status} ${resp.statusText}` };
    }
    const data = await resp.json();
    return { corrections: data.corrections ?? [], error: null };
  } catch (e: unknown) {
    return { corrections: [], error: e instanceof Error ? e.message : String(e) };
  }
}

export default async function CorrectionsPage() {
  const { orgSlug } = await auth();
  const { corrections, error } = await loadCorrections();

  const byScope: Record<string, Correction[]> = {};
  for (const c of corrections) {
    const scope = c.scope || "global";
    if (!byScope[scope]) byScope[scope] = [];
    byScope[scope].push(c);
  }
  const scopeOrder = ["global", "client", "engagement", "protocol", "agent", "decision"];

  return (
    <div className="mx-auto max-w-5xl px-8 py-10 space-y-6">
      <header>
        <span className="ce-eyebrow">Learn</span>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">
          Corrections{" "}
          <span className="text-muted-foreground text-base font-normal">
            ({corrections.length} active)
          </span>
        </h1>
        <p className="mt-1 text-sm text-muted-foreground text-pretty">
          Rules-of-the-road for your C-Suite. Every active correction is surfaced to the agents
          as institutional memory before every relevant run.
          {orgSlug ? <span className="ml-2 font-mono">· {orgSlug}</span> : null}
        </p>
      </header>

      <NewCorrectionForm />

      {error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Railway API unreachable.</strong>
          <div className="text-destructive/70 text-xs mt-1 font-mono">{error}</div>
        </div>
      ) : corrections.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-6 text-center">
          <p className="text-muted-foreground">No corrections yet. Create one above.</p>
        </div>
      ) : (
        <CorrectionsList byScope={byScope} scopeOrder={scopeOrder} />
      )}
    </div>
  );
}
