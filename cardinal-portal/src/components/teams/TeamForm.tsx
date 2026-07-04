"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Search } from "lucide-react";
import type { Agent, Team } from "@/lib/api";

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

type Props = {
  mode: "create" | "edit";
  agents: Agent[];
  initial?: Partial<Team>;
};

export function TeamForm({ mode, agents, initial }: Props) {
  const router = useRouter();

  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [agentKeys, setAgentKeys] = useState<string[]>(initial?.agent_keys ?? []);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return agents;
    return agents.filter((a) => {
      const hay = [a.key, a.name ?? "", a.title ?? "", a.category ?? ""].join(" ").toLowerCase();
      return hay.includes(needle);
    });
  }, [agents, q]);

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

  function toggle(key: string) {
    setAgentKeys((curr) => (curr.includes(key) ? curr.filter((x) => x !== key) : [...curr, key]));
  }

  async function save() {
    setError(null);
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }
    if (agentKeys.length === 0) {
      setError("Pick at least one agent.");
      return;
    }
    setBusy(true);
    try {
      const body = {
        name: name.trim(),
        description: description.trim(),
        agent_keys: agentKeys,
      };
      const path =
        mode === "create" ? "/api/proxy/teams" : `/api/proxy/teams/${initial?.id}`;
      const method = mode === "create" ? "POST" : "PUT";
      const resp = await fetch(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(`${resp.status}: ${text.slice(0, 300)}`);
      }
      const created = (await resp.json()) as Team;
      router.push(`/teams/${created.id}`);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Identity */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <div>
          <span className="ce-eyebrow">Identity</span>
          <h2 className="mt-1 text-base font-bold tracking-tight">Team info</h2>
        </div>
        <Field label="Name" required>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. GTM war room"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          />
        </Field>
        <Field label="Description" hint="When would you use this team?">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            placeholder="Sales, marketing, and CS leadership for revenue-inflection decisions."
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          />
        </Field>
      </section>

      {/* Agent picker */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-3">
        <div className="flex items-start justify-between">
          <div>
            <span className="ce-eyebrow">Roster</span>
            <h2 className="mt-1 text-base font-bold tracking-tight">
              Agents{" "}
              <span className="text-sm font-normal text-muted-foreground">
                ({agentKeys.length} selected · {agents.length} total)
              </span>
            </h2>
          </div>
          <div className="relative max-w-xs flex-1">
            <Search
              size={13}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
            />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Filter…"
              className="w-full rounded-md border border-input bg-background py-1.5 pl-8 pr-3 text-xs text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            />
          </div>
        </div>

        {agentKeys.length > 0 ? (
          <div className="flex flex-wrap gap-1.5 rounded-md bg-primary/5 p-2">
            {agentKeys.map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => toggle(k)}
                className="inline-flex items-center gap-1.5 rounded-full border border-primary/40 bg-primary/15 px-2 py-0.5 font-mono text-[10px] text-primary transition-colors hover:bg-primary/25"
              >
                {k}
                <span className="text-muted-foreground">×</span>
              </button>
            ))}
          </div>
        ) : null}

        <div className="max-h-96 space-y-3 overflow-y-auto pr-1">
          {ordered.map((cat) => (
            <div key={cat}>
              <div className="ce-label mb-1.5">{CATEGORY_LABELS[cat] ?? cat}</div>
              <div className="flex flex-wrap gap-1.5">
                {grouped[cat].map((a) => {
                  const active = agentKeys.includes(a.key);
                  return (
                    <button
                      key={a.key}
                      type="button"
                      onClick={() => toggle(a.key)}
                      title={a.description ?? a.name ?? a.key}
                      className={`rounded border px-2 py-1 font-mono text-xs transition-colors ${
                        active
                          ? "border-primary/40 bg-primary/15 text-primary"
                          : "border-border bg-background text-foreground hover:border-primary/50"
                      }`}
                    >
                      {a.key}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="flex items-center justify-between border-t border-border pt-5">
        <div className="text-xs">
          {error ? <span className="text-destructive">{error}</span> : null}
        </div>
        <button
          type="button"
          onClick={save}
          disabled={busy || !name.trim() || agentKeys.length === 0}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-indigo)] transition-colors hover:bg-[rgb(var(--ce-indigo-500))] disabled:opacity-40 disabled:hover:bg-primary"
        >
          {busy ? "Saving…" : mode === "create" ? "Create team" : "Save changes"}
          {!busy ? <ArrowRight size={14} /> : null}
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  required,
  hint,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="ce-label block">
        {label} {required ? <span className="text-destructive">*</span> : null}
      </label>
      {children}
      {hint ? <div className="text-[10px] leading-relaxed text-muted-foreground">{hint}</div> : null}
    </div>
  );
}
