import { auth } from "@clerk/nextjs/server";
import { OrganizationSwitcher, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { fetchRuns, type Run } from "@/lib/api";

export default async function RunsPage() {
  const { orgSlug } = await auth();

  let runs: Run[] = [];
  let apiError: string | null = null;
  try {
    runs = await fetchRuns(100);
  } catch (e: unknown) {
    apiError = e instanceof Error ? e.message : String(e);
  }

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">All runs</h1>
            <p className="text-sm text-slate-400 mt-1">
              Tenant: <span className="text-slate-200 font-mono">{orgSlug ?? "(no org)"}</span>
              <span className="ml-3 text-slate-500">{runs.length} runs</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/run"
              className="rounded-md bg-fuchsia-600 px-3 py-1.5 text-xs font-medium hover:bg-fuchsia-500 transition"
            >
              + New run
            </Link>
            <OrganizationSwitcher hidePersonal />
            <UserButton />
          </div>
        </header>

        {apiError ? (
          <div className="rounded-lg border border-rose-700/40 bg-rose-950/20 p-4 text-sm text-rose-200">
            <strong>Railway API unreachable.</strong>
            <div className="text-rose-300/70 text-xs mt-1 font-mono">{apiError}</div>
          </div>
        ) : runs.length === 0 ? (
          <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-8 text-center">
            <p className="text-slate-400">No runs yet for this tenant.</p>
            <Link href="/run" className="inline-block mt-3 text-fuchsia-400 hover:text-fuchsia-300 text-sm">
              Run your first protocol &rarr;
            </Link>
          </div>
        ) : (
          <div className="rounded-lg border border-slate-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-900/60 text-xs uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="text-left px-4 py-3">Question</th>
                  <th className="text-left px-4 py-3">Protocol</th>
                  <th className="text-left px-4 py-3">Started</th>
                  <th className="text-left px-4 py-3">Cost</th>
                  <th className="text-left px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id} className="border-t border-slate-800 hover:bg-slate-900/40">
                    <td className="px-4 py-3 max-w-md">
                      <Link href={`/runs/${r.id}`} className="hover:text-fuchsia-300 truncate block">
                        {r.question}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-xs font-mono text-slate-400">{r.protocol_key}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {r.started_at ? new Date(r.started_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs tabular-nums text-slate-400">
                      {r.cost_usd != null ? `$${r.cost_usd.toFixed(4)}` : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <StatusPill status={r.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}

function StatusPill({ status }: { status: Run["status"] }) {
  const styles: Record<Run["status"], string> = {
    running: "bg-blue-500/15 text-blue-300 border-blue-500/30",
    completed: "bg-green-500/15 text-green-300 border-green-500/30",
    failed: "bg-rose-500/15 text-rose-300 border-rose-500/30",
    cancelled: "bg-slate-500/15 text-slate-300 border-slate-500/30",
  };
  return (
    <span className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded-full border ${styles[status]}`}>
      {status}
    </span>
  );
}
