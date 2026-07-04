import Link from "next/link";
import { notFound } from "next/navigation";
import { auth } from "@clerk/nextjs/server";
import { fetchAgents, type Team } from "@/lib/api";
import { TeamForm } from "@/components/teams/TeamForm";
import { DeleteTeamButton } from "@/components/teams/DeleteTeamButton";

async function loadTeam(id: string): Promise<Team | null> {
  const { getToken } = await auth();
  const token = await getToken({ template: "ce-railway" }).catch(() => null);
  const API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";
  const resp = await fetch(`${API_BASE}/api/teams/${id}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });
  if (resp.status === 404) return null;
  if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
  return (await resp.json()) as Team;
}

export default async function TeamDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let team: Team | null = null;
  let error: string | null = null;
  try {
    team = await loadTeam(id);
  } catch (e: unknown) {
    error = e instanceof Error ? e.message : String(e);
  }

  if (!team && !error) notFound();

  let agents: Awaited<ReturnType<typeof fetchAgents>> = [];
  try {
    agents = await fetchAgents();
  } catch {
    // ignore — still show the form with empty agent list
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
        <div className="mt-2 flex items-end justify-between gap-4">
          <div>
            <span className="ce-eyebrow">Build</span>
            <h1 className="mt-1 text-3xl font-bold tracking-tight">{team?.name ?? "Team"}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {team?.agent_keys.length ?? 0} agents · created{" "}
              {team?.created_at ? new Date(team.created_at).toLocaleDateString() : "—"}
            </p>
          </div>
          {team ? <DeleteTeamButton id={team.id} /> : null}
        </div>
      </header>

      {error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Cannot load team.</strong>
          <div className="mt-1 font-mono text-xs text-destructive/70">{error}</div>
        </div>
      ) : team ? (
        <TeamForm mode="edit" agents={agents} initial={team} />
      ) : null}
    </div>
  );
}
