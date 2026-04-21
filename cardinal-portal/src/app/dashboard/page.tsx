import { auth } from "@clerk/nextjs/server";
import { OrganizationSwitcher, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { fetchRuns, fetchProtocols, fetchAgents, fetchUsage, fetchGraphStats, type Run } from "@/lib/api";

export default async function DashboardPage() {
  const { orgSlug, orgRole, sessionClaims } = await auth();

  const [runsResult, protocolsResult, agentsResult, usageResult, graphResult] = await Promise.allSettled([
    fetchRuns(10),
    fetchProtocols(),
    fetchAgents(),
    fetchUsage(),
    fetchGraphStats(),
  ]);

  const runs: Run[] = runsResult.status === "fulfilled" ? runsResult.value : [];
  const protocolCount = protocolsResult.status === "fulfilled" ? protocolsResult.value.length : null;
  const agentCount = agentsResult.status === "fulfilled" ? agentsResult.value.length : null;
  const usage = usageResult.status === "fulfilled" ? usageResult.value : null;
  const graph = graphResult.status === "fulfilled" ? graphResult.value : null;
  const apiError =
    runsResult.status === "rejected" ? String(runsResult.reason).slice(0, 200) : null;

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Your C-Suite</h1>
            <p className="text-sm text-slate-400 mt-1">
              Tenant: <span className="text-slate-200 font-mono">{orgSlug ?? "(no org)"}</span>
              {orgRole ? <span className="ml-2 text-xs uppercase tracking-wider text-slate-500">{orgRole}</span> : null}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <OrganizationSwitcher hidePersonal />
            <UserButton />
          </div>
        </header>

        {!orgSlug ? (
          <div className="rounded-lg border border-amber-700/40 bg-amber-950/20 p-4">
            <p className="text-amber-200">Pick or create an organization to provision your C-Suite.</p>
          </div>
        ) : null}

        {/* Primary CTA -- the product is "ask your C-Suite a question" */}
        <section className="rounded-xl border border-fuchsia-700/30 bg-gradient-to-br from-fuchsia-950/30 to-violet-950/20 p-6">
          <h2 className="text-xl font-semibold">Ask your C-Suite a strategic question</h2>
          <p className="text-slate-300 mt-2 text-sm">
            53 research-backed protocols. 95 expert agent roles. The adaptive router picks the right protocol;
            your agents execute it; you get a structured deliverable.
          </p>
          <Link
            href="/run"
            className="inline-block mt-4 rounded-md bg-fuchsia-600 px-4 py-2 text-sm font-medium hover:bg-fuchsia-500 transition"
          >
            Start a run &rarr;
          </Link>
        </section>

        {/* Nav row to the four product surfaces */}
        <nav className="flex flex-wrap gap-2 text-sm">
          <Link href="/run" className="rounded-md border border-fuchsia-700/40 bg-fuchsia-950/20 px-3 py-1.5 text-fuchsia-200 hover:bg-fuchsia-950/40 transition">
            Run a protocol →
          </Link>
          <Link href="/runs" className="rounded-md border border-slate-700 px-3 py-1.5 hover:bg-slate-900 transition">
            All runs
          </Link>
          <Link href="/protocols" className="rounded-md border border-slate-700 px-3 py-1.5 hover:bg-slate-900 transition">
            Protocol library
          </Link>
          <Link href="/c-suite" className="rounded-md border border-slate-700 px-3 py-1.5 hover:bg-slate-900 transition">
            Your C-Suite
          </Link>
          <Link href="/knowledge" className="rounded-md border border-slate-700 px-3 py-1.5 hover:bg-slate-900 transition">
            Knowledge
          </Link>
        </nav>

        {/* Stat row -- protocols, agents, runs, cost, graph size */}
        <section className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <Stat label="Protocols" value={protocolCount ?? "—"} hint="research-backed methodologies" />
          <Stat label="Agent roles" value={agentCount ?? "—"} hint="C-Suite + functional" />
          <Stat
            label="Runs to date"
            value={usage?.total_runs ?? runs.length}
            hint={usage?.last_run_at ? `last ${new Date(usage.last_run_at).toLocaleDateString()}` : "this tenant"}
          />
          <Stat
            label="Cost to date"
            value={usage?.total_cost_usd != null ? `$${usage.total_cost_usd.toFixed(4)}` : "—"}
            hint={usage?.completed_runs != null ? `${usage.completed_runs} completed` : "this tenant"}
          />
          <Stat
            label="Graph nodes"
            value={graph?.total_nodes ?? "—"}
            hint={graph?.graph_name ? graph.graph_name : "fuel layer"}
          />
        </section>

        {/* Recent runs -- the actual work product */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold">Recent runs</h3>
            <Link href="/runs" className="text-sm text-slate-400 hover:text-slate-200">
              View all &rarr;
            </Link>
          </div>
          {apiError ? (
            <div className="rounded-lg border border-rose-700/40 bg-rose-950/20 p-4 text-sm text-rose-200">
              <strong>Railway API unreachable.</strong>
              <div className="text-rose-300/70 text-xs mt-1 font-mono">{apiError}</div>
              <div className="text-rose-300/70 text-xs mt-2">
                Expected before Milestone 1 wires per-tenant auth into the existing /api/runs endpoint.
              </div>
            </div>
          ) : runs.length === 0 ? (
            <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-6 text-center">
              <p className="text-slate-400">No runs yet for this tenant.</p>
              <Link href="/run" className="inline-block mt-3 text-fuchsia-400 hover:text-fuchsia-300 text-sm">
                Run your first protocol &rarr;
              </Link>
            </div>
          ) : (
            <ul className="space-y-2">
              {runs.map((r) => (
                <li
                  key={r.id}
                  className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 flex items-center justify-between"
                >
                  <div className="min-w-0">
                    <Link href={`/runs/${r.id}`} className="font-medium hover:text-fuchsia-300 truncate block">
                      {r.question}
                    </Link>
                    <div className="text-xs text-slate-500 mt-1 font-mono">
                      {r.protocol_key} · {r.agent_keys?.join(", ")}
                    </div>
                  </div>
                  <StatusPill status={r.status} />
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Debug strip — minimal, not the focus */}
        <section className="text-xs text-slate-600 font-mono pt-6 border-t border-slate-900">
          <div>JWT sub: {sessionClaims?.sub ?? "(none)"}</div>
          <div>org_id: {(sessionClaims?.org_id as string | undefined) ?? "(none)"}</div>
        </section>
      </div>
    </main>
  );
}

function Stat({ label, value, hint }: { label: string; value: number | string; hint: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <div className="text-3xl font-semibold tabular-nums">{value}</div>
      <div className="text-xs uppercase tracking-wider text-slate-400 mt-1">{label}</div>
      <div className="text-[10px] text-slate-500 mt-0.5">{hint}</div>
    </div>
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
