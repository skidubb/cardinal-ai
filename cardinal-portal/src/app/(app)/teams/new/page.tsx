import Link from "next/link";
import { fetchAgents } from "@/lib/api";
import { TeamForm } from "@/components/teams/TeamForm";

export default async function NewTeamPage() {
  let agents: Awaited<ReturnType<typeof fetchAgents>> = [];
  let error: string | null = null;
  try {
    agents = await fetchAgents();
  } catch (e: unknown) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="mx-auto max-w-4xl px-8 py-10 space-y-6">
      <header>
        <Link
          href="/teams"
          className="text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          &larr; Teams
        </Link>
        <span className="ce-eyebrow mt-2 block">Build</span>
        <h1 className="mt-1 text-3xl font-bold tracking-tight">New team</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Pick a name and the agents that should run together.
        </p>
      </header>

      {error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Cannot load agents.</strong>
          <div className="mt-1 font-mono text-xs text-destructive/70">{error}</div>
        </div>
      ) : (
        <TeamForm mode="create" agents={agents} />
      )}
    </div>
  );
}
