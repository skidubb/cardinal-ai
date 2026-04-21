import { auth } from "@clerk/nextjs/server";
import { OrganizationSwitcher, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import NewCorrectionForm from "./NewCorrectionForm";
import CorrectionsList, { type Correction } from "./CorrectionsList";

const API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

async function loadCorrections(): Promise<{ corrections: Correction[]; error: string | null }> {
  try {
    const { getToken } = await auth();
    const token = await getToken({ template: "ce-railway" }).catch(() => null);
    const resp = await fetch(`${API_BASE}/api/corrections?active_only=true`, {
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

  // Group by scope
  const byScope: Record<string, Correction[]> = {};
  for (const c of corrections) {
    const scope = c.scope || "global";
    if (!byScope[scope]) byScope[scope] = [];
    byScope[scope].push(c);
  }
  const scopeOrder = ["global", "client", "engagement", "protocol", "agent", "decision"];

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <Link href="/dashboard" className="text-xs text-slate-500 hover:text-slate-300">
              &larr; Dashboard
            </Link>
            <h1 className="text-2xl font-semibold tracking-tight mt-1">
              Corrections{" "}
              <span className="text-slate-500 text-base font-normal">
                ({corrections.length} active)
              </span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Rules-of-the-road for your C-Suite. Every active correction is surfaced to the agents
              as institutional memory before every relevant run. Tenant:{" "}
              <span className="font-mono text-slate-200">{orgSlug ?? "(no org)"}</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <OrganizationSwitcher hidePersonal />
            <UserButton />
          </div>
        </header>

        <NewCorrectionForm />

        {error ? (
          <div className="rounded-lg border border-rose-700/40 bg-rose-950/20 p-4 text-sm text-rose-200">
            <strong>Railway API unreachable.</strong>
            <div className="text-rose-300/70 text-xs mt-1 font-mono">{error}</div>
          </div>
        ) : corrections.length === 0 ? (
          <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-6 text-center">
            <p className="text-slate-400">No corrections yet. Create one above.</p>
          </div>
        ) : (
          <CorrectionsList byScope={byScope} scopeOrder={scopeOrder} />
        )}
      </div>
    </main>
  );
}
