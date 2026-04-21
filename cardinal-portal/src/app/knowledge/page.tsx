import { auth } from "@clerk/nextjs/server";
import { OrganizationSwitcher, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { fetchGraphStats, fetchConnectorsStatus, type ConnectorStatus } from "@/lib/api";
import BackfillControls from "./BackfillControls";

export default async function KnowledgePage() {
  const { orgSlug } = await auth();

  const [graphResult, connectorsResult] = await Promise.allSettled([
    fetchGraphStats(),
    fetchConnectorsStatus(),
  ]);

  const graph = graphResult.status === "fulfilled" ? graphResult.value : null;
  const connectors: ConnectorStatus[] = connectorsResult.status === "fulfilled" ? connectorsResult.value.connectors : [];
  const graphError = graphResult.status === "rejected" ? String(graphResult.reason).slice(0, 200) : null;

  const directApi = connectors.filter((c) => c.mode === "direct_api");
  const mcpDriven = connectors.filter((c) => c.mode === "mcp_driven");

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <Link href="/dashboard" className="text-xs text-slate-500 hover:text-slate-300">
              &larr; Dashboard
            </Link>
            <h1 className="text-2xl font-semibold tracking-tight mt-1">Knowledge</h1>
            <p className="text-sm text-slate-400 mt-1">
              Your business&apos;s institutional memory — the fuel behind every protocol run.{" "}
              Tenant: <span className="font-mono text-slate-200">{orgSlug ?? "(no org)"}</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <OrganizationSwitcher hidePersonal />
            <UserButton />
          </div>
        </header>

        {/* Graph stats */}
        <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
          <div className="flex items-baseline justify-between mb-3">
            <h2 className="text-sm uppercase tracking-wider text-slate-400">Graph</h2>
            {graph ? (
              <span className="text-xs text-slate-500 font-mono">{graph.graph_name}</span>
            ) : null}
          </div>
          {graphError ? (
            <div className="text-sm text-rose-300">
              <strong>ce-graph unreachable:</strong>{" "}
              <span className="font-mono text-xs">{graphError}</span>
              <div className="text-rose-300/70 text-xs mt-1">
                Start FalkorDB: <code className="bg-slate-950/60 px-1 rounded">docker compose up -d</code> in <code>ce-graph/</code>
              </div>
            </div>
          ) : graph ? (
            <>
              <div className="text-4xl font-semibold tabular-nums">
                {graph.total_nodes}
                <span className="text-sm text-slate-500 ml-2">total nodes</span>
              </div>
              {Object.keys(graph.counts).length > 0 ? (
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2 mt-4">
                  {Object.entries(graph.counts).map(([label, n]) => (
                    <div key={label} className="rounded border border-slate-800 bg-slate-950/40 px-3 py-2">
                      <div className="text-lg font-semibold tabular-nums">{n}</div>
                      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-slate-500 mt-2">
                  Graph is empty. Run a connector backfill below to populate it.
                </div>
              )}
            </>
          ) : null}
        </section>

        {/* Connectors */}
        <section className="space-y-4">
          <h2 className="text-sm uppercase tracking-wider text-slate-400">Data Connectors</h2>

          {/* Direct API */}
          {directApi.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-2">
                Direct-API connectors — triggered server-side with stored credentials
              </div>
              <div className="grid md:grid-cols-2 gap-3">
                {directApi.map((c) => (
                  <ConnectorCard key={c.name} connector={c} />
                ))}
              </div>
            </div>
          )}

          {/* MCP-driven */}
          {mcpDriven.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-2">
                MCP-driven connectors — run via the <code>ce-graph-backfill</code> agent inside Claude Code
              </div>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
                {mcpDriven.map((c) => (
                  <ConnectorCard key={c.name} connector={c} />
                ))}
              </div>
            </div>
          )}
        </section>

        {/* What to ingest runbook */}
        <section className="rounded-xl border border-fuchsia-700/30 bg-gradient-to-br from-fuchsia-950/10 to-violet-950/5 p-5">
          <h3 className="text-sm font-semibold">What belongs in the graph</h3>
          <ul className="text-sm text-slate-300 mt-2 space-y-1 list-disc list-inside">
            <li><strong>Yes</strong> — Client / Engagement / Decision / Correction / Lesson entities; structured facts</li>
            <li><strong>No</strong> — every email, every meeting transcript verbatim, every Slack message. That&apos;s a data lake, not a knowledge graph.</li>
          </ul>
          <p className="text-xs text-slate-500 mt-3">
            Healthy customer graphs sit at 500–5,000 nodes. More is usually noise.
          </p>
        </section>
      </div>
    </main>
  );
}

function ConnectorCard({ connector }: { connector: ConnectorStatus }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="font-medium text-slate-100 capitalize">{connector.name.replace("_", " ")}</div>
        <span
          className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border ${
            connector.enabled
              ? "bg-green-500/15 text-green-300 border-green-500/30"
              : "bg-slate-700/30 text-slate-400 border-slate-700"
          }`}
        >
          {connector.enabled ? "enabled" : "disabled"}
        </span>
      </div>
      <div className="text-[10px] text-slate-500 font-mono mb-3">
        {connector.mode === "direct_api" ? "direct api" : "mcp driven"} · auth: {connector.auth}
      </div>
      <BackfillControls connector={connector} />
    </div>
  );
}
