import Link from "next/link";
import { ArrowRight, Plug } from "lucide-react";
import { auth } from "@clerk/nextjs/server";
import { fetchGraphStats } from "@/lib/api";

export default async function KnowledgePage() {
  const { orgSlug } = await auth();

  let graph: Awaited<ReturnType<typeof fetchGraphStats>> | null = null;
  let graphError: string | null = null;
  try {
    graph = await fetchGraphStats();
  } catch (e: unknown) {
    graphError = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="mx-auto max-w-6xl px-8 py-10 space-y-6">
      <header>
        <span className="ce-eyebrow">Connect</span>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Graph</h1>
        <p className="mt-1 text-sm text-muted-foreground text-pretty">
          Your business&apos;s institutional memory — the fuel behind every protocol run.
          {orgSlug ? <span className="ml-2 font-mono">· {orgSlug}</span> : null}
        </p>
      </header>

      {/* Graph stats */}
      <section className="rounded-xl border border-border bg-card p-5">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="ce-label">Graph</h2>
          {graph ? (
            <span className="font-mono text-xs text-muted-foreground">{graph.graph_name}</span>
          ) : null}
        </div>
        {graphError ? (
          <div className="text-sm text-destructive">
            <strong>ce-graph unreachable:</strong>{" "}
            <span className="font-mono text-xs">{graphError}</span>
            <div className="mt-1 text-xs text-destructive/70">
              Start FalkorDB: <code className="rounded bg-secondary px-1 font-mono">docker compose up -d</code> in{" "}
              <code className="font-mono">ce-graph/</code>
            </div>
          </div>
        ) : graph ? (
          <>
            <div className="text-4xl font-bold tracking-tight tabular-nums text-foreground">
              {graph.total_nodes}
              <span className="ml-2 text-sm font-normal text-muted-foreground">total nodes</span>
            </div>
            {Object.keys(graph.counts).length > 0 ? (
              <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-6">
                {Object.entries(graph.counts).map(([label, n]) => (
                  <div key={label} className="rounded border border-border bg-muted px-3 py-2">
                    <div className="text-lg font-bold tabular-nums text-foreground">{n}</div>
                    <div className="ce-label">{label}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-2 text-sm text-muted-foreground">
                Graph is empty. Configure connectors in{" "}
                <Link
                  href="/integrations"
                  className="text-primary underline-offset-4 hover:underline"
                >
                  Integrations
                </Link>{" "}
                to populate it.
              </div>
            )}
          </>
        ) : null}
      </section>

      {/* Connectors moved — nudge to Integrations */}
      <section className="rounded-xl border border-primary/30 bg-primary/5 p-5">
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Plug size={18} />
          </div>
          <div className="flex-1">
            <span className="ce-eyebrow">Data sources moved</span>
            <h3 className="mt-1 text-base font-bold tracking-tight">Connectors now live in Integrations</h3>
            <p className="mt-1 text-sm text-muted-foreground text-pretty">
              Notion, Granola, Drive, HubSpot, Slack, Gmail — plus your custom MCP servers and APIs —
              are all managed alongside tools in one marketplace.
            </p>
            <Link
              href="/integrations"
              className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-primary underline-offset-4 hover:underline"
            >
              Open Integrations <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </section>

      {/* What belongs in the graph runbook */}
      <section className="rounded-xl border border-border bg-card p-5">
        <span className="ce-eyebrow">Runbook</span>
        <h3 className="mt-1 text-base font-bold tracking-tight">What belongs in the graph</h3>
        <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-foreground text-pretty">
          <li>
            <strong>Yes</strong> — Client / Engagement / Decision / Correction / Lesson entities;
            structured facts
          </li>
          <li>
            <strong>No</strong> — every email, every meeting transcript verbatim, every Slack
            message. That&apos;s a data lake, not a knowledge graph.
          </li>
        </ul>
        <p className="mt-3 text-xs text-muted-foreground">
          Healthy customer graphs sit at 500–5,000 nodes. More is usually noise.
        </p>
      </section>
    </div>
  );
}
