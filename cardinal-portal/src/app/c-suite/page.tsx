import { auth } from "@clerk/nextjs/server";
import { OrganizationSwitcher, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { fetchAgents, type Agent } from "@/lib/api";

const CATEGORY_LABELS: Record<string, string> = {
  executive: "C-Suite Executives",
  c_suite: "C-Suite Executives",
  "cfo-team": "CFO Direct Reports",
  "cto-team": "CTO Direct Reports",
  "cmo-team": "CMO Direct Reports",
  "coo-team": "COO Direct Reports",
  "cpo-team": "CPO Direct Reports",
  "cro-team": "CRO Direct Reports",
  "gtm-sales": "GTM — Sales",
  "gtm-marketing": "GTM — Marketing",
  "gtm-success": "GTM — Customer Success",
  "gtm-revops": "GTM — RevOps",
  "gtm-partnerships": "GTM — Partnerships",
  direct_report: "Direct Reports",
  functional: "Functional",
  other: "Other",
};

const CATEGORY_ORDER = [
  "executive",
  "c_suite",
  "cfo-team",
  "cto-team",
  "cmo-team",
  "coo-team",
  "cpo-team",
  "cro-team",
  "gtm-sales",
  "gtm-marketing",
  "gtm-success",
  "gtm-revops",
  "gtm-partnerships",
  "direct_report",
  "functional",
  "other",
];

function groupByCategory(agents: Agent[]): Record<string, Agent[]> {
  const out: Record<string, Agent[]> = {};
  for (const a of agents) {
    const cat = a.category ?? a.layer ?? "other";
    if (!out[cat]) out[cat] = [];
    out[cat].push(a);
  }
  return out;
}

export default async function CSuitePage() {
  const { orgSlug } = await auth();

  let agents: Agent[] = [];
  let error: string | null = null;
  try {
    agents = await fetchAgents();
  } catch (e: unknown) {
    error = e instanceof Error ? e.message : String(e);
  }

  const grouped = groupByCategory(agents);
  const categoriesPresent = Object.keys(grouped);
  const ordered = [
    ...CATEGORY_ORDER.filter((c) => categoriesPresent.includes(c)),
    ...categoriesPresent.filter((c) => !CATEGORY_ORDER.includes(c)),
  ];

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <Link href="/dashboard" className="text-xs text-slate-500 hover:text-slate-300">
              &larr; Dashboard
            </Link>
            <h1 className="text-2xl font-semibold tracking-tight mt-1">
              Your C-Suite{" "}
              <span className="text-slate-500 text-base font-normal">({agents.length} agent roles)</span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Tenant: <span className="font-mono text-slate-200">{orgSlug ?? "(no org)"}</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/run"
              className="rounded-md bg-fuchsia-600 px-3 py-1.5 text-xs font-medium hover:bg-fuchsia-500 transition"
            >
              + New run
            </Link>
            <OrganizationSwitcher hidePersonal />
            <UserButton />
          </div>
        </header>

        {error ? (
          <div className="rounded-lg border border-rose-700/40 bg-rose-950/20 p-4 text-sm text-rose-200">
            <strong>Cannot reach Railway.</strong>
            <div className="text-rose-300/70 text-xs mt-1 font-mono">{error}</div>
          </div>
        ) : null}

        {ordered.map((cat) => (
          <section key={cat} className="space-y-3">
            <div className="border-b border-slate-800 pb-2">
              <h2 className="text-base font-semibold">
                {CATEGORY_LABELS[cat] ?? cat}{" "}
                <span className="text-xs text-slate-500 ml-2">{grouped[cat].length}</span>
              </h2>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
              {grouped[cat].map((a) => (
                <AgentCard key={a.key} agent={a} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}

function AgentCard({ agent }: { agent: Agent }) {
  const display = agent.name ?? agent.title ?? agent.key;
  const toolCount = (agent.tools?.length ?? 0) + (agent.mcp_servers?.length ?? 0);
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 hover:border-slate-700 transition">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-xs text-fuchsia-300">{agent.key}</span>
        {agent.is_builtin === false ? (
          <span className="text-[9px] uppercase tracking-wider text-amber-400">custom</span>
        ) : null}
      </div>
      <div className="font-medium text-slate-100 mt-1">{display}</div>
      {agent.description ? (
        <div className="text-xs text-slate-400 mt-2 line-clamp-3">{agent.description}</div>
      ) : null}
      <div className="text-[10px] text-slate-500 mt-3 font-mono space-y-0.5">
        {agent.model ? <div>{agent.model}</div> : null}
        {toolCount > 0 ? <div>{toolCount} tools / mcp servers</div> : null}
      </div>
    </div>
  );
}
