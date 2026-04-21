import { auth } from "@clerk/nextjs/server";
import { OrganizationSwitcher, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { fetchProtocols, type Protocol } from "@/lib/api";

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  "Meta-Protocols": "Routing, gating, escalation -- decide which other protocol to run.",
  "Baselines": "Single-round patterns -- parallel synthesis, debate, constraint negotiation.",
  "Liberating Structures": "Curated participatory methods -- TRIZ, Wicked Questions, 1-2-4-All, Min Specs, etc.",
  "Intelligence Analysis": "Adversarial reasoning -- Analysis of Competing Hypotheses, Red/Blue/White Team, Delphi.",
  "Game Theory": "Auction and voting protocols -- Vickrey, Borda, interest-based negotiation.",
  "Org Theory": "Sequential pipeline + Cynefin probe-sense-respond.",
  "Systems Thinking": "Causal loop mapping, system archetype detection.",
  "Design Thinking": "Crazy Eights, affinity mapping.",
  "Wave 2 Research": "Six Hats, Tetlock, Klein Premortem, Popper falsification, Whitehead weights, walks, etc.",
};

function groupByCategory(protocols: Protocol[]): Record<string, Protocol[]> {
  const out: Record<string, Protocol[]> = {};
  for (const p of protocols) {
    const cat = p.category || "Other";
    if (!out[cat]) out[cat] = [];
    out[cat].push(p);
  }
  return out;
}

export default async function ProtocolsPage() {
  const { orgSlug } = await auth();

  let protocols: Protocol[] = [];
  let error: string | null = null;
  try {
    protocols = await fetchProtocols();
  } catch (e: unknown) {
    error = e instanceof Error ? e.message : String(e);
  }

  const grouped = groupByCategory(protocols);
  const categoryNames = Object.keys(grouped).sort();

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <Link href="/dashboard" className="text-xs text-slate-500 hover:text-slate-300">
              &larr; Dashboard
            </Link>
            <h1 className="text-2xl font-semibold tracking-tight mt-1">
              Protocol library{" "}
              <span className="text-slate-500 text-base font-normal">
                ({protocols.length} research-backed methodologies)
              </span>
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

        {categoryNames.map((cat) => (
          <section key={cat} className="space-y-3">
            <div className="border-b border-slate-800 pb-2">
              <h2 className="text-base font-semibold">
                {cat} <span className="text-xs text-slate-500 ml-2">{grouped[cat].length}</span>
              </h2>
              {CATEGORY_DESCRIPTIONS[cat] ? (
                <p className="text-xs text-slate-400 mt-1">{CATEGORY_DESCRIPTIONS[cat]}</p>
              ) : null}
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
              {grouped[cat].map((p) => (
                <ProtocolCard key={p.key} protocol={p} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}

function ProtocolCard({ protocol }: { protocol: Protocol }) {
  const code = protocol.protocol_id ?? protocol.code ?? protocol.key.split("_")[0].toUpperCase();
  const tier = protocol.cost_tier;
  return (
    <Link
      href={`/run?protocol=${protocol.key}`}
      className="group block rounded-lg border border-slate-800 bg-slate-900/40 p-4 hover:border-fuchsia-700/40 hover:bg-slate-900/60 transition"
    >
      <div className="flex items-baseline justify-between mb-1">
        <span className="font-mono text-xs text-fuchsia-300">{code}</span>
        {tier ? (
          <span className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded border ${
            tier === "low" ? "border-green-700/40 text-green-300" :
            tier === "medium" ? "border-amber-700/40 text-amber-300" :
            "border-rose-700/40 text-rose-300"
          }`}>
            {tier}
          </span>
        ) : null}
      </div>
      <div className="font-medium text-slate-100 group-hover:text-fuchsia-200 transition">
        {protocol.name}
      </div>
      {protocol.description ? (
        <div className="text-xs text-slate-400 mt-2 line-clamp-2">{protocol.description}</div>
      ) : null}
      {(protocol.min_agents || protocol.max_agents) ? (
        <div className="text-[10px] text-slate-500 mt-2 font-mono">
          {protocol.min_agents ?? "?"}-{protocol.max_agents ?? "?"} agents
          {protocol.supports_rounds ? " · multi-round" : ""}
        </div>
      ) : null}
    </Link>
  );
}
