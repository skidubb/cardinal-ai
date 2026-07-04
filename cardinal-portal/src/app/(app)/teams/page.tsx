import Link from "next/link";
import { Plus, Users } from "lucide-react";
import { fetchTeams } from "@/lib/api";

export default async function TeamsPage() {
  let teams: Awaited<ReturnType<typeof fetchTeams>> = [];
  let error: string | null = null;
  try {
    teams = await fetchTeams();
  } catch (e: unknown) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="mx-auto max-w-6xl px-8 py-10 space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <span className="ce-eyebrow">Build</span>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">
            Teams{" "}
            <span className="text-base font-normal text-muted-foreground">({teams.length})</span>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground text-pretty">
            Save reusable agent groups. Apply them in one click from Ask or Pipelines.
          </p>
        </div>
        <Link
          href="/teams/new"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-indigo)] transition-colors hover:bg-[rgb(var(--ce-indigo-500))]"
        >
          <Plus size={14} /> New team
        </Link>
      </header>

      {error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Cannot reach Railway.</strong>
          <div className="mt-1 font-mono text-xs text-destructive/70">{error}</div>
        </div>
      ) : teams.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-10 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Users size={20} />
          </div>
          <p className="mt-4 text-sm text-muted-foreground text-pretty">
            No teams yet. Build a team by name and picking agents, or save one from the{" "}
            <Link href="/run" className="text-primary underline-offset-4 hover:underline">
              Ask
            </Link>{" "}
            page after picking an agent set.
          </p>
          <Link
            href="/teams/new"
            className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-[rgb(var(--ce-indigo-500))]"
          >
            <Plus size={14} /> Build your first team
          </Link>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {teams.map((t) => (
            <TeamCard key={t.id} team={t} />
          ))}
        </div>
      )}
    </div>
  );
}

function TeamCard({ team }: { team: Awaited<ReturnType<typeof fetchTeams>>[number] }) {
  return (
    <Link
      href={`/teams/${team.id}`}
      className="group block rounded-xl border border-border bg-card p-4 transition-all duration-300 hover:border-primary/50"
    >
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10px] uppercase tracking-wider text-primary">
          {team.agent_keys.length} AGENTS
        </span>
        {team.last_used_at ? (
          <span className="font-mono text-[9px] text-muted-foreground">
            last {new Date(team.last_used_at).toLocaleDateString()}
          </span>
        ) : null}
      </div>
      <div className="mt-1 font-semibold tracking-tight text-foreground group-hover:text-primary transition-colors">
        {team.name}
      </div>
      {team.description ? (
        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted-foreground text-pretty">
          {team.description}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-1 font-mono text-[10px]">
        {team.agent_keys.slice(0, 5).map((k) => (
          <span key={k} className="rounded bg-secondary px-1.5 py-0.5 text-muted-foreground">
            {k}
          </span>
        ))}
        {team.agent_keys.length > 5 ? (
          <span className="text-muted-foreground">+{team.agent_keys.length - 5}</span>
        ) : null}
      </div>
    </Link>
  );
}
