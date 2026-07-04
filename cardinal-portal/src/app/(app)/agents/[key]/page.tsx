import Link from "next/link";
import { notFound } from "next/navigation";
import {
  fetchAgentDetail,
  fetchToolCatalog,
  fetchNamespaces,
} from "@/lib/api";
import { AgentForm } from "@/components/agents/AgentForm";

export default async function AgentDetailPage({
  params,
}: {
  params: Promise<{ key: string }>;
}) {
  const { key } = await params;

  const [agentR, catalogR, nsR] = await Promise.allSettled([
    fetchAgentDetail(key),
    fetchToolCatalog(),
    fetchNamespaces(),
  ]);

  if (agentR.status === "rejected") {
    const msg = String(agentR.reason);
    if (msg.includes("404")) {
      notFound();
    }
    return (
      <div className="mx-auto max-w-4xl px-8 py-10">
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Cannot load agent.</strong>
          <div className="mt-1 font-mono text-xs text-destructive/70">{msg.slice(0, 300)}</div>
        </div>
      </div>
    );
  }

  const agent = agentR.value;
  const catalog =
    catalogR.status === "fulfilled" ? catalogR.value : { tools: {}, mcp_servers: {} };
  const namespaces = nsR.status === "fulfilled" ? nsR.value : [];

  return (
    <div className="mx-auto max-w-4xl px-8 py-10 space-y-6">
      <header>
        <Link
          href="/agents"
          className="text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          &larr; Agents
        </Link>
        <div className="mt-2 flex items-center gap-3">
          <span className="ce-eyebrow">Build</span>
          {agent.is_builtin ? (
            <span className="rounded-full border border-border bg-secondary px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              built-in
            </span>
          ) : (
            <span className="rounded-full border border-[rgb(var(--ce-yellow-500))]/40 bg-[rgb(var(--ce-yellow-500))]/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-[rgb(var(--ce-yellow-500))]">
              custom
            </span>
          )}
        </div>
        <h1 className="mt-1 text-3xl font-bold tracking-tight">
          {agent.name}{" "}
          <span className="ml-2 font-mono text-base font-normal text-muted-foreground">
            {agent.key}
          </span>
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {agent.category} · {agent.model || "no model configured"}
        </p>
      </header>

      <AgentForm mode="edit" catalog={catalog} namespaces={namespaces} initial={agent} />
    </div>
  );
}
