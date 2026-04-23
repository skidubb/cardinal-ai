import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { fetchProtocols, type Protocol } from "@/lib/api";
import { PatternIcon } from "@/components/run/PatternIcon";
import type { OrchestrationPattern } from "@/components/run/orchestrationPattern";
import { PatternFilter } from "./PatternFilter";
import { patternsFromSearchParams } from "./patternParams";

const ROUTER_CATEGORY = "Meta-Protocols";

const PROBLEM_TYPE_DESCRIPTIONS: Record<string, string> = {
  Diagnostic: "Figure out what's actually going on — root causes, mechanisms, evidence.",
  Adversarial: "Stress-test a plan — red-team, falsify, find what could kill it.",
  Exploration: "Open up the solution space — ideation, combinatorial search, divergent thinking.",
  "Multi-Stakeholder": "Reconcile competing interests — negotiation, voting, coalition-building.",
  Prioritization: "Rank and choose — score options, allocate scarce attention.",
  "Systems Analysis": "Map structure — feedback loops, archetypes, cause-effect chains.",
  "Constraint Definition": "Define the envelope — must-haves vs. nice-to-haves.",
  Estimation: "Forecast and quantify — calibrated probabilities, ranges, confidence.",
  "Divergent Ideation": "Generate many candidates fast — creativity-first patterns.",
  "General Analysis": "Generalist baselines that adapt to most problem types.",
  "Factual Lookup": "Retrieve known facts — no reasoning needed.",
  Mechanical: "Deterministic transformations — no LLM reasoning.",
  "Role Expertise": "Leverage a specific professional viewpoint.",
  Research: "Deep investigation across sources.",
  "Portfolio Management": "Cross-initiative coordination and allocation.",
};

function groupByProblemType(
  protocols: Protocol[],
): { name: string; protocols: Protocol[] }[] {
  const buckets = new Map<string, Protocol[]>();
  for (const p of protocols) {
    const types = p.problem_types && p.problem_types.length > 0 ? p.problem_types : ["Uncategorized"];
    for (const t of types) {
      if (!buckets.has(t)) buckets.set(t, []);
      buckets.get(t)!.push(p);
    }
  }
  // Sort buckets by size desc (popular problem types surface first), name asc for ties.
  return Array.from(buckets.entries())
    .map(([name, protocols]) => ({ name, protocols: protocols.sort((a, b) => a.name.localeCompare(b.name)) }))
    .sort((a, b) => b.protocols.length - a.protocols.length || a.name.localeCompare(b.name));
}

export default async function ProtocolsPage({
  searchParams,
}: {
  searchParams: Promise<{ patterns?: string | string[] }>;
}) {
  const { orgSlug } = await auth();
  const { patterns: rawPatterns } = await searchParams;

  let protocols: Protocol[] = [];
  let error: string | null = null;
  try {
    protocols = await fetchProtocols();
  } catch (e: unknown) {
    error = e instanceof Error ? e.message : String(e);
  }

  // Count protocols per orchestration pattern BEFORE filtering so the chip
  // counts always reflect the full catalog (not a post-filter subset).
  const counts: Record<OrchestrationPattern, number> = {
    single_agent: 0,
    sequence: 0,
    parallel: 0,
    hub_and_spoke: 0,
    hybrid_matrix: 0,
    decentralized: 0,
  };
  for (const p of protocols) {
    const pat = p.orchestration_pattern as OrchestrationPattern | undefined;
    if (pat && pat in counts) counts[pat] += 1;
  }

  // Apply pattern filter from ?patterns= URL param (empty set = show all).
  const selectedPatterns = patternsFromSearchParams(rawPatterns);
  const filtered =
    selectedPatterns.size === 0
      ? protocols
      : protocols.filter((p) => {
          const pat = p.orchestration_pattern as OrchestrationPattern | undefined;
          return !!pat && selectedPatterns.has(pat);
        });

  // Routers (pinned at top) — the 4 meta-protocols that dispatch to others.
  const routers = filtered.filter((p) => p.category === ROUTER_CATEGORY);
  const nonRouters = filtered.filter((p) => p.category !== ROUTER_CATEGORY);
  const problemGroups = groupByProblemType(nonRouters);

  return (
    <div className="mx-auto max-w-6xl px-8 py-10 space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <span className="ce-eyebrow">Connect</span>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">
            Protocol library{" "}
            <span className="text-muted-foreground text-base font-normal">
              ({protocols.length})
            </span>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Organized by problem type — {orgSlug ? <span className="font-mono">{orgSlug}</span> : "(no org)"}
          </p>
        </div>
        <Link
          href="/run"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-[rgb(var(--ce-indigo-500))]"
        >
          + New run
        </Link>
      </header>

      {error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Cannot reach Railway.</strong>
          <div className="text-destructive/70 text-xs mt-1 font-mono">{error}</div>
        </div>
      ) : null}

      <PatternFilter counts={counts} />

      {selectedPatterns.size > 0 && filtered.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center">
          <p className="text-muted-foreground">
            No protocols match {Array.from(selectedPatterns).join(" + ")}.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Clear the filter to see all {protocols.length} protocols.
          </p>
        </div>
      ) : null}

      {routers.length > 0 ? (
        <section className="space-y-3">
          <div className="border-b border-border pb-2">
            <h2 className="text-base font-bold tracking-tight flex items-center gap-2">
              Routers
              <span className="text-xs text-muted-foreground">{routers.length}</span>
              <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded border border-primary/40 text-primary font-mono">
                Internal
              </span>
            </h2>
            <p className="text-xs text-muted-foreground mt-1">
              Meta-protocols that classify a question and dispatch it to the right method. Invoked automatically via Smart Route on Ask — not selectable as a standalone run.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
            {routers.map((p) => (
              <ProtocolCard key={p.key} protocol={p} isRouter />
            ))}
          </div>
        </section>
      ) : null}

      {problemGroups.map(({ name, protocols: bucket }) => {
        const desc = PROBLEM_TYPE_DESCRIPTIONS[name];
        return (
          <section key={name} className="space-y-3">
            <div className="border-b border-border pb-2">
              <h2 className="text-base font-bold tracking-tight flex items-center gap-2">
                {name}
                <span className="text-xs text-muted-foreground">{bucket.length}</span>
              </h2>
              {desc ? (
                <p className="text-xs text-muted-foreground mt-1">{desc}</p>
              ) : null}
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
              {bucket.map((p) => (
                <ProtocolCard key={`${name}-${p.key}`} protocol={p} />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function ProtocolCard({ protocol, isRouter = false }: { protocol: Protocol; isRouter?: boolean }) {
  const code = protocol.protocol_id ?? protocol.code ?? protocol.key.split("_")[0].toUpperCase();
  const tier = protocol.cost_tier;
  const pattern = protocol.orchestration_pattern as OrchestrationPattern | undefined;
  const href = isRouter ? "/run?mode=smart" : `/protocols/${protocol.key}`;
  return (
    <Link
      href={href}
      className={`group block rounded-xl border p-4 transition-all duration-300 ${
        isRouter
          ? "border-primary/30 bg-primary/5 hover:border-primary/60"
          : "border-border bg-card hover:border-primary/50"
      }`}
    >
      <div className="flex items-baseline justify-between mb-1 gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          {pattern ? <PatternIcon pattern={pattern} size={14} /> : null}
          <span className="font-mono text-xs text-primary">{code}</span>
          {isRouter ? (
            <span className="text-[8px] uppercase tracking-wider px-1 py-0.5 rounded bg-primary/20 text-primary font-mono shrink-0">
              Router
            </span>
          ) : null}
        </div>
        {tier ? (
          <span className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded border shrink-0 ${
            tier === "low" ? "border-[rgb(var(--ce-green-500))]/40 text-[rgb(var(--ce-green-500))]" :
            tier === "medium" ? "border-[rgb(var(--ce-yellow-500))]/40 text-[rgb(var(--ce-yellow-500))]" :
            "border-destructive/40 text-destructive"
          }`}>
            {tier}
          </span>
        ) : null}
      </div>
      <div className="font-medium text-foreground group-hover:text-primary transition-colors">
        {protocol.name}
      </div>
      {protocol.description ? (
        <div className="text-xs text-muted-foreground mt-2 line-clamp-2 text-pretty">{protocol.description}</div>
      ) : null}
      <div className="mt-3 flex items-center justify-between text-[10px] text-muted-foreground">
        {isRouter ? (
          <span className="italic text-primary/80">Invoked via Smart Route on Ask</span>
        ) : (protocol.min_agents || protocol.max_agents) ? (
          <span className="font-mono">
            {protocol.min_agents ?? "?"}-{protocol.max_agents ?? "?"} agents
            {protocol.supports_rounds ? " · multi-round" : ""}
          </span>
        ) : <span />}
        {!isRouter && protocol.category ? (
          <span className="font-mono uppercase tracking-wider text-[9px] text-muted-foreground/70">
            {protocol.category}
          </span>
        ) : null}
      </div>
    </Link>
  );
}
