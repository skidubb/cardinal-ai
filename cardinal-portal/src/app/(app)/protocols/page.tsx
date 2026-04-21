import { auth } from "@clerk/nextjs/server";
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
              Research-backed methodologies — {orgSlug ? <span className="font-mono">{orgSlug}</span> : "(no org)"}
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

        {categoryNames.map((cat) => (
          <section key={cat} className="space-y-3">
            <div className="border-b border-border pb-2">
              <h2 className="text-base font-bold tracking-tight">
                {cat} <span className="text-xs text-muted-foreground ml-2">{grouped[cat].length}</span>
              </h2>
              {CATEGORY_DESCRIPTIONS[cat] ? (
                <p className="text-xs text-muted-foreground mt-1">{CATEGORY_DESCRIPTIONS[cat]}</p>
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
  );
}

function ProtocolCard({ protocol }: { protocol: Protocol }) {
  const code = protocol.protocol_id ?? protocol.code ?? protocol.key.split("_")[0].toUpperCase();
  const tier = protocol.cost_tier;
  return (
    <Link
      href={`/run?protocol=${protocol.key}`}
      className="group block rounded-xl border border-border bg-card p-4 transition-all duration-300 hover:border-primary/50"
    >
      <div className="flex items-baseline justify-between mb-1">
        <span className="font-mono text-xs text-primary">{code}</span>
        {tier ? (
          <span className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded border ${
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
      {(protocol.min_agents || protocol.max_agents) ? (
        <div className="text-[10px] text-muted-foreground mt-2 font-mono">
          {protocol.min_agents ?? "?"}-{protocol.max_agents ?? "?"} agents
          {protocol.supports_rounds ? " · multi-round" : ""}
        </div>
      ) : null}
    </Link>
  );
}
