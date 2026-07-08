import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { fetchGraphSubgraph } from "@/lib/api";
import { parseUpgradeDetail, type UpgradeDetail } from "@/lib/upgrade";
import { UpgradeCard } from "@/components/billing/UpgradeCard";
import { GraphMap } from "./GraphMap";

export default async function GraphMapPage() {
  const { orgSlug } = await auth();

  let data: Awaited<ReturnType<typeof fetchGraphSubgraph>> | null = null;
  let apiError: string | null = null;
  let upgrade: UpgradeDetail | null = null;
  try {
    data = await fetchGraphSubgraph(500);
  } catch (e: unknown) {
    apiError = e instanceof Error ? e.message : String(e);
    upgrade = parseUpgradeDetail(apiError);
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-8 py-10 space-y-4">
      <header className="flex items-end justify-between">
        <div>
          <Link
            href="/knowledge"
            className="text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            &larr; Stats view
          </Link>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">Graph map</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Force-directed view of this tenant&apos;s knowledge graph.
            {orgSlug ? <span className="ml-2 font-mono">· {orgSlug}</span> : null}
          </p>
        </div>
        {data ? (
          <span className="text-xs text-muted-foreground">
            <span className="font-mono">{data.graph_name}</span> · {data.node_count} nodes ·{" "}
            {data.edge_count} edges
          </span>
        ) : null}
      </header>

      {upgrade ? (
        <UpgradeCard {...upgrade} />
      ) : apiError ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Cannot load graph.</strong>
          <div className="mt-1 font-mono text-xs text-destructive/80">{apiError}</div>
          <div className="mt-2 text-xs text-destructive/70">
            Verify FalkorDB is reachable and the tenant has been provisioned (
            <code className="font-mono">cegraph init --tenant &lt;slug&gt;</code>
            ). Then trigger a backfill from{" "}
            <Link href="/knowledge" className="underline">
              /knowledge
            </Link>
            .
          </div>
        </div>
      ) : data && data.node_count === 0 ? (
        <div className="rounded-xl border border-[rgb(var(--ce-yellow-500))]/40 bg-[rgb(var(--ce-yellow-500))]/10 p-4 text-sm text-[rgb(var(--ce-yellow-500))]">
          <strong>Graph is empty.</strong> Run a protocol or trigger a backfill to populate this
          tenant&apos;s graph. Visit{" "}
          <Link href="/knowledge" className="underline">
            /knowledge
          </Link>{" "}
          to start a backfill.
        </div>
      ) : data ? (
        <GraphMap nodes={data.nodes} edges={data.edges} />
      ) : null}
    </div>
  );
}
