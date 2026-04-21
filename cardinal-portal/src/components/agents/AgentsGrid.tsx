"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import type { Agent } from "@/lib/api";

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

export function AgentsGrid({ agents }: { agents: Agent[] }) {
  const [q, setQ] = useState("");
  const [showCustomOnly, setShowCustomOnly] = useState(false);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return agents.filter((a) => {
      if (showCustomOnly && a.is_builtin !== false) return false;
      if (!needle) return true;
      const hay = [
        a.key,
        a.name ?? "",
        a.title ?? "",
        a.description ?? "",
        a.category ?? "",
      ]
        .join(" ")
        .toLowerCase();
      return hay.includes(needle);
    });
  }, [agents, q, showCustomOnly]);

  const grouped = useMemo(() => {
    const out: Record<string, Agent[]> = {};
    for (const a of filtered) {
      const cat = a.category ?? a.layer ?? "other";
      if (!out[cat]) out[cat] = [];
      out[cat].push(a);
    }
    return out;
  }, [filtered]);

  const ordered = useMemo(() => {
    const present = Object.keys(grouped);
    return [
      ...CATEGORY_ORDER.filter((c) => present.includes(c)),
      ...present.filter((c) => !CATEGORY_ORDER.includes(c)),
    ];
  }, [grouped]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search agents — key, name, role…"
            className="w-full rounded-md border border-input bg-background py-2 pl-9 pr-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={showCustomOnly}
            onChange={(e) => setShowCustomOnly(e.target.checked)}
            className="h-4 w-4 rounded border-input accent-[rgb(var(--ce-indigo-600))]"
          />
          Custom agents only
        </label>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
          No agents match.
        </div>
      ) : null}

      {ordered.map((cat) => (
        <section key={cat} className="space-y-3">
          <div className="border-b border-border pb-2">
            <h2 className="text-base font-bold tracking-tight">
              {CATEGORY_LABELS[cat] ?? cat}{" "}
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                {grouped[cat].length}
              </span>
            </h2>
          </div>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {grouped[cat].map((a) => (
              <AgentCard key={a.key} agent={a} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function AgentCard({ agent }: { agent: Agent }) {
  const display = agent.name ?? agent.title ?? agent.key;
  const toolCount = (agent.tools?.length ?? 0) + (agent.mcp_servers?.length ?? 0);
  return (
    <Link
      href={`/agents/${encodeURIComponent(agent.key)}`}
      className="group block rounded-xl border border-border bg-card p-4 transition-all duration-300 hover:border-primary/50"
    >
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-xs text-primary">{agent.key}</span>
        {agent.is_builtin === false ? (
          <span className="text-[9px] uppercase tracking-wider text-[rgb(var(--ce-yellow-500))]">
            custom
          </span>
        ) : null}
      </div>
      <div className="mt-1 font-medium text-foreground group-hover:text-primary transition-colors">
        {display}
      </div>
      {agent.description ? (
        <div className="mt-2 line-clamp-3 text-xs text-muted-foreground text-pretty">
          {agent.description}
        </div>
      ) : null}
      <div className="mt-3 space-y-0.5 font-mono text-[10px] text-muted-foreground">
        {agent.model ? <div>{agent.model}</div> : null}
        {toolCount > 0 ? <div>{toolCount} tools / mcp</div> : null}
      </div>
    </Link>
  );
}
