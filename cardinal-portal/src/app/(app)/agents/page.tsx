import Link from "next/link";
import { Plus } from "lucide-react";
import { fetchAgents } from "@/lib/api";
import { AgentsGrid } from "@/components/agents/AgentsGrid";

export default async function AgentsPage() {
  let agents: Awaited<ReturnType<typeof fetchAgents>> = [];
  let error: string | null = null;
  try {
    agents = await fetchAgents();
  } catch (e: unknown) {
    error = e instanceof Error ? e.message : String(e);
  }

  const customCount = agents.filter((a) => a.is_builtin === false).length;

  return (
    <div className="mx-auto max-w-6xl px-8 py-10 space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <span className="ce-eyebrow">Build</span>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">
            Agents{" "}
            <span className="text-base font-normal text-muted-foreground">({agents.length})</span>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {customCount} custom · {agents.length - customCount} built-in. Each agent has its own
            system prompt, tool access, and knowledge scope.
          </p>
        </div>
        <Link
          href="/agents/new"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-indigo)] transition-colors hover:bg-[rgb(var(--ce-indigo-500))]"
        >
          <Plus size={14} /> New agent
        </Link>
      </header>

      {error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Cannot reach Railway.</strong>
          <div className="mt-1 font-mono text-xs text-destructive/70">{error}</div>
        </div>
      ) : (
        <AgentsGrid agents={agents} />
      )}
    </div>
  );
}
