import Link from "next/link";
import { fetchToolCatalog, fetchNamespaces } from "@/lib/api";
import { AgentForm } from "@/components/agents/AgentForm";

export default async function NewAgentPage() {
  const [catalogR, nsR] = await Promise.allSettled([fetchToolCatalog(), fetchNamespaces()]);
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
        <span className="ce-eyebrow mt-2 block">Build</span>
        <h1 className="mt-1 text-3xl font-bold tracking-tight">New agent</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Define system prompt, tool access, and knowledge scope. Available immediately after save.
        </p>
      </header>

      <AgentForm mode="create" catalog={catalog} namespaces={namespaces} />
    </div>
  );
}
