import { auth } from "@clerk/nextjs/server";
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
    <div className="mx-auto max-w-6xl px-8 py-10 space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <span className="ce-eyebrow">History</span>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">All runs</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {orgSlug ? <span className="font-mono">{orgSlug}</span> : "(no org)"}
              <span className="ml-3">· {runs.length} runs</span>
            </p>
          </div>
          <Link
            href="/run"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-[rgb(var(--ce-indigo-500))]"
          >
            + New run
          </Link>
        </header>

        {apiError ? (
          <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
            <strong>Railway API unreachable.</strong>
            <div className="text-destructive/70 text-xs mt-1 font-mono">{apiError}</div>
          </div>
        ) : runs.length === 0 ? (
          <div className="rounded-xl border border-border bg-card p-8 text-center">
            <p className="text-muted-foreground">No runs yet for this tenant.</p>
            <Link href="/run" className="inline-block mt-3 text-primary hover:underline underline-offset-4 text-sm">
              Run your first protocol &rarr;
            </Link>
          </div>
        ) : (
          <div className="rounded-xl border border-border overflow-hidden bg-card">
            <table className="w-full text-sm">
              <thead className="bg-secondary ce-label">
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
                  <tr key={r.id} className="border-t border-border hover:bg-secondary transition-colors">
                    <td className="px-4 py-3 max-w-md">
                      <Link href={`/runs/${r.id}`} className="hover:text-primary truncate block transition-colors">
                        {r.question}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-xs font-mono text-muted-foreground">{r.protocol_key}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {r.started_at ? new Date(r.started_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs tabular-nums text-muted-foreground">
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
  );
}

function StatusPill({ status }: { status: Run["status"] }) {
  const styles: Record<Run["status"], string> = {
    running: "bg-[rgb(var(--ce-blue-500))]/15 text-[rgb(var(--ce-blue-500))] border-[rgb(var(--ce-blue-500))]/30",
    completed: "bg-[rgb(var(--ce-green-500))]/15 text-[rgb(var(--ce-green-500))] border-[rgb(var(--ce-green-500))]/30",
    failed: "bg-destructive/15 text-destructive border-destructive/30",
    cancelled: "bg-secondary text-muted-foreground border-border",
  };
  return (
    <span className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded-full border font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}
