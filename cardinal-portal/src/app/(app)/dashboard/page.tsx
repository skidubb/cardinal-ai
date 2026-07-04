import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { ArrowRight, Sparkles, Users, Plug } from "lucide-react";
import {
  fetchRuns,
  fetchProtocols,
  fetchAgents,
  fetchUsage,
  fetchGraphStats,
  type Run,
} from "@/lib/api";

export default async function DashboardPage() {
  const { orgSlug, orgRole } = await auth();

  const [runsResult, protocolsResult, agentsResult, usageResult, graphResult] =
    await Promise.allSettled([
      fetchRuns(6),
      fetchProtocols(),
      fetchAgents(),
      fetchUsage(),
      fetchGraphStats(),
    ]);

  const runs: Run[] = runsResult.status === "fulfilled" ? runsResult.value : [];
  const protocolCount =
    protocolsResult.status === "fulfilled" ? protocolsResult.value.length : null;
  const agentCount =
    agentsResult.status === "fulfilled" ? agentsResult.value.length : null;
  const usage = usageResult.status === "fulfilled" ? usageResult.value : null;
  const graph = graphResult.status === "fulfilled" ? graphResult.value : null;
  const apiError =
    runsResult.status === "rejected"
      ? String(runsResult.reason).slice(0, 200)
      : null;

  return (
    <div className="mx-auto max-w-7xl px-8 py-10 space-y-10">
      <header>
        <span className="ce-eyebrow">Workspace</span>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">
          {orgSlug ? `${orgSlug}` : "Your workspace"}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ask a question · Build an agent · Connect a tool · Chain a pipeline
          {orgRole ? <span className="ml-2 ce-label">· {orgRole}</span> : null}
        </p>
      </header>

      {!orgSlug ? (
        <div className="rounded-xl border border-[rgb(var(--ce-yellow-500))]/40 bg-[rgb(var(--ce-yellow-500))]/10 p-4">
          <p className="text-[rgb(var(--ce-yellow-500))]">
            Pick or create an organization to provision your workspace.
          </p>
        </div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-3">
        <EntryCard
          href="/run"
          icon={<Sparkles size={20} />}
          eyebrow="01"
          title="Ask a question"
          body="Let the router pick a protocol, or choose one yourself. Stream agent responses live."
          primary
        />
        <EntryCard
          href="/agents"
          icon={<Users size={20} />}
          eyebrow="02"
          title="Build an agent"
          body="Custom system prompts, tool access, and knowledge scopes. Reuse across every run."
        />
        <EntryCard
          href="/integrations"
          icon={<Plug size={20} />}
          eyebrow="03"
          title="Connect a tool"
          body="26 tools across 10 domains — search, CRM, docs, data — plus MCP servers."
        />
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold tracking-tight text-foreground">
          Workspace health
        </h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <Stat label="Agents" value={agentCount ?? "—"} hint="built-in + custom" href="/agents" />
          <Stat
            label="Protocols"
            value={protocolCount ?? "—"}
            hint="research-backed"
            href="/protocols"
          />
          <Stat
            label="Runs"
            value={usage?.total_runs ?? runs.length}
            hint={
              usage?.last_run_at
                ? `last ${new Date(usage.last_run_at).toLocaleDateString()}`
                : "this tenant"
            }
            href="/runs"
          />
          <Stat
            label="Graph"
            value={graph?.total_nodes ?? "—"}
            hint={graph?.graph_name ? "nodes" : "fuel layer"}
            href="/knowledge"
          />
          <Stat
            label="Cost"
            value={
              usage?.total_cost_usd != null
                ? `$${usage.total_cost_usd.toFixed(2)}`
                : "—"
            }
            hint={
              usage?.completed_runs != null
                ? `${usage.completed_runs} completed`
                : "to date"
            }
          />
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold tracking-tight text-foreground">
            Recent runs
          </h2>
          <Link
            href="/runs"
            className="text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            View all &rarr;
          </Link>
        </div>
        {apiError ? (
          <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
            <strong>Railway API unreachable.</strong>
            <div className="mt-1 font-mono text-xs text-destructive/70">{apiError}</div>
          </div>
        ) : runs.length === 0 ? (
          <div className="rounded-xl border border-border bg-card p-6 text-center">
            <p className="text-muted-foreground">No runs yet for this tenant.</p>
            <Link
              href="/run"
              className="mt-3 inline-block text-sm text-primary underline-offset-4 hover:underline"
            >
              Run your first protocol &rarr;
            </Link>
          </div>
        ) : (
          <ul className="space-y-2">
            {runs.map((r) => (
              <li
                key={r.id}
                className="flex items-center justify-between rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/50"
              >
                <div className="min-w-0 flex-1">
                  <Link
                    href={`/runs/${r.id}`}
                    className="block truncate font-medium transition-colors hover:text-primary"
                  >
                    {r.question}
                  </Link>
                  <div className="mt-1 font-mono text-xs text-muted-foreground">
                    {r.protocol_key} · {r.agent_keys?.join(", ")}
                  </div>
                </div>
                <StatusPill status={r.status} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function EntryCard({
  href,
  icon,
  eyebrow,
  title,
  body,
  primary,
}: {
  href: string;
  icon: React.ReactNode;
  eyebrow: string;
  title: string;
  body: string;
  primary?: boolean;
}) {
  return (
    <Link
      href={href}
      className={[
        "group relative flex flex-col gap-3 rounded-xl border p-6 transition-all duration-300",
        primary
          ? "border-primary/30 bg-primary/5 hover:border-primary/60 hover:shadow-[var(--shadow-indigo)]"
          : "border-border bg-card hover:border-primary/50",
      ].join(" ")}
    >
      <div
        className={[
          "flex h-10 w-10 items-center justify-center rounded-lg transition-colors",
          primary
            ? "bg-primary text-primary-foreground"
            : "bg-secondary text-primary group-hover:bg-primary/10",
        ].join(" ")}
      >
        {icon}
      </div>
      <div className="flex-1">
        <div className="font-mono text-[11px] font-medium uppercase tracking-[0.12em] text-primary">
          {eyebrow}
        </div>
        <h3 className="mt-1 text-lg font-bold tracking-tight text-foreground">{title}</h3>
        <p className="mt-1 text-sm leading-relaxed text-muted-foreground text-pretty">{body}</p>
      </div>
      <div className="flex items-center gap-2 text-sm font-medium text-primary">
        Open <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
      </div>
    </Link>
  );
}

function Stat({
  label,
  value,
  hint,
  href,
}: {
  label: string;
  value: number | string;
  hint: string;
  href?: string;
}) {
  const inner = (
    <div
      className={[
        "rounded-xl border border-border bg-card p-4 transition-colors",
        href ? "hover:border-primary/50" : "",
      ].join(" ")}
    >
      <div className="text-2xl font-bold tracking-tight tabular-nums text-foreground">{value}</div>
      <div className="ce-label mt-1">{label}</div>
      <div className="mt-0.5 text-[10px] text-muted-foreground">{hint}</div>
    </div>
  );
  if (href) {
    return (
      <Link href={href} className="block">
        {inner}
      </Link>
    );
  }
  return inner;
}

function StatusPill({ status }: { status: Run["status"] }) {
  const styles: Record<Run["status"], string> = {
    running:
      "bg-[rgb(var(--ce-blue-500))]/15 text-[rgb(var(--ce-blue-500))] border-[rgb(var(--ce-blue-500))]/30",
    completed:
      "bg-[rgb(var(--ce-green-500))]/15 text-[rgb(var(--ce-green-500))] border-[rgb(var(--ce-green-500))]/30",
    failed: "bg-destructive/15 text-destructive border-destructive/30",
    cancelled: "bg-secondary text-muted-foreground border-border",
  };
  return (
    <span
      className={`rounded-full border px-2 py-1 text-[10px] font-medium uppercase tracking-wider ${styles[status]}`}
    >
      {status}
    </span>
  );
}
