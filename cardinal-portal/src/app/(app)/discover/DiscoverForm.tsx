"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileText, Link2, Sparkles, Users } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import type {
  Agent,
  Protocol,
  SuggestedAgentPick,
  SuggestedNewAgent,
  SuggestedTeam,
} from "@/lib/api";
import { SuggestedAgentCard } from "@/components/agents/SuggestedAgentCard";

type Severity = "high" | "medium" | "low";

type ProtocolMatch = {
  key: string;
  name?: string | null;
  score: number;
  rationale: string;
};

type DiscoveredQuestion = {
  text: string;
  category: string;
  severity: Severity;
  rationale: string;
  suggested_protocol: string;
  suggested_protocol_name?: string | null;
  suggested_protocols?: ProtocolMatch[];
  suggested_agents?: SuggestedAgentPick[];
  suggested_new_agents?: SuggestedNewAgent[];
  suggested_team?: SuggestedTeam | null;
};

type DiscoverResult = {
  document_summary: string;
  questions: DiscoveredQuestion[];
  source_filename: string;
  token_count: number;
  was_truncated: boolean;
};

const CATEGORY_ORDER = [
  "strategic",
  "financial",
  "operational",
  "competitive",
  "legal",
  "technical",
  "market",
  "people",
];

const SEVERITY_RANK: Record<Severity, number> = { high: 0, medium: 1, low: 2 };

const FALLBACK_AGENTS = ["ceo", "cfo", "cto"];

export function DiscoverForm({
  protocols,
  agents,
}: {
  protocols: Protocol[];
  agents: Agent[];
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [urls, setUrls] = useState<string[]>([]);
  const [urlDraft, setUrlDraft] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DiscoverResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function addUrl() {
    const raw = urlDraft.trim();
    if (!raw) return;
    let normalized = raw;
    if (!/^https?:\/\//i.test(normalized)) {
      normalized = `https://${normalized}`;
    }
    try {
      const u = new URL(normalized);
      if (u.protocol !== "http:" && u.protocol !== "https:") throw new Error("bad-protocol");
    } catch {
      setUrlError("Enter a valid http(s) URL.");
      return;
    }
    if (urls.includes(normalized)) {
      setUrlDraft("");
      setUrlError(null);
      return;
    }
    if (urls.length >= 5) {
      setUrlError("Max 5 URLs per call.");
      return;
    }
    setUrls((curr) => [...curr, normalized]);
    setUrlDraft("");
    setUrlError(null);
  }

  async function onSubmit() {
    if (files.length === 0 && urls.length === 0) {
      setError("Add at least one file or URL.");
      return;
    }
    setStatus("uploading");
    setError(null);
    setResult(null);

    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    for (const u of urls) fd.append("urls", u);

    try {
      const resp = await fetch("/api/proxy/discover-questions", {
        method: "POST",
        body: fd,
      });
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(`${resp.status}: ${detail.slice(0, 400)}`);
      }
      const data = (await resp.json()) as DiscoverResult;
      setResult(data);
      setStatus("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  }

  const questions = result?.questions ?? [];
  const byCategory = groupByCategory(questions);
  const protocolByKey = useMemo(() => {
    const map = new Map<string, Protocol>();
    for (const p of protocols) map.set(p.key, p);
    return map;
  }, [protocols]);

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-primary/30 bg-primary/5 p-6 space-y-4">
        <div>
          <label className="ce-label mb-2 block">Source</label>
          <p className="text-xs text-muted-foreground">
            Upload PDF, DOCX, TXT, or MD — or paste a URL (article, 10-K filing, blog post, PDF link).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={status === "uploading"}
            className="rounded-md border border-border bg-background px-3 py-2 text-sm transition-colors hover:border-primary/50 disabled:opacity-50"
          >
            Choose file{files.length > 1 ? "s" : ""}
          </button>
          <input
            ref={inputRef}
            type="file"
            hidden
            multiple
            accept=".pdf,.docx,.txt,.md,.markdown"
            onChange={(e) => {
              const chosen = Array.from(e.target.files ?? []);
              if (chosen.length) setFiles((curr) => [...curr, ...chosen]);
              e.target.value = "";
            }}
          />
          <button
            type="button"
            onClick={onSubmit}
            disabled={status === "uploading" || (files.length === 0 && urls.length === 0)}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-[rgb(var(--ce-indigo-500))] disabled:opacity-40"
          >
            {status === "uploading" ? "Analyzing…" : "Discover questions"}
          </button>
        </div>

        <div>
          <label className="ce-label mb-1.5 block text-[11px]">Or paste a URL</label>
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="url"
              value={urlDraft}
              onChange={(e) => {
                setUrlDraft(e.target.value);
                if (urlError) setUrlError(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addUrl();
                }
              }}
              disabled={status === "uploading"}
              placeholder="https://example.com/article"
              className="min-w-[260px] flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:opacity-50"
            />
            <button
              type="button"
              onClick={addUrl}
              disabled={status === "uploading" || !urlDraft.trim()}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm transition-colors hover:border-primary/50 disabled:opacity-50"
            >
              Add URL
            </button>
          </div>
          {urlError ? (
            <div className="mt-1 text-[11px] text-destructive">{urlError}</div>
          ) : null}
        </div>

        {(files.length > 0 || urls.length > 0) ? (
          <div className="flex flex-wrap gap-1.5">
            {files.map((f, i) => (
              <span
                key={`file-${f.name}-${i}`}
                className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 font-mono text-[11px] text-primary"
                title={`${(f.size / 1024).toFixed(1)} KB`}
              >
                <FileText size={11} />
                {f.name}
                <button
                  type="button"
                  onClick={() => setFiles((curr) => curr.filter((_, idx) => idx !== i))}
                  disabled={status === "uploading"}
                  className="ml-1 text-muted-foreground transition-colors hover:text-destructive"
                  aria-label={`Remove ${f.name}`}
                >
                  ×
                </button>
              </span>
            ))}
            {urls.map((u, i) => (
              <span
                key={`url-${u}-${i}`}
                className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 font-mono text-[11px] text-primary max-w-[420px]"
                title={u}
              >
                <Link2 size={11} className="shrink-0" />
                <span className="truncate">{u.replace(/^https?:\/\//, "")}</span>
                <button
                  type="button"
                  onClick={() => setUrls((curr) => curr.filter((_, idx) => idx !== i))}
                  disabled={status === "uploading"}
                  className="ml-1 shrink-0 text-muted-foreground transition-colors hover:text-destructive"
                  aria-label={`Remove ${u}`}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        ) : null}

        {status === "uploading" ? (
          <p className="text-xs text-muted-foreground">
            Parsing and analyzing. A 50-page PDF typically takes 20–40 seconds. URLs are fetched and cleaned before analysis.
          </p>
        ) : null}
      </section>

      {error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Discovery failed.</strong>
          <div className="mt-1 font-mono text-xs text-destructive/80">{error}</div>
        </div>
      ) : null}

      {result ? (
        <section className="space-y-5">
          <div className="rounded-xl border border-border bg-card p-5 text-sm">
            <div className="ce-label mb-1">Document summary</div>
            <p className="leading-relaxed text-foreground">{result.document_summary}</p>
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
              <span>
                <span className="ce-label mr-2">Source:</span>
                {result.source_filename}
              </span>
              <span>
                <span className="ce-label mr-2">Tokens:</span>
                {result.token_count.toLocaleString()}
              </span>
              {result.was_truncated ? (
                <span className="text-[rgb(var(--ce-yellow-500))]">
                  Compressed before analysis (doc exceeded inline threshold).
                </span>
              ) : null}
            </div>
          </div>

          <div className="space-y-6">
            {CATEGORY_ORDER.filter((c) => byCategory[c]?.length).map((cat) => (
              <div key={cat} className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="ce-label capitalize">{cat}</h2>
                  <span className="text-xs text-muted-foreground">
                    {byCategory[cat].length} question{byCategory[cat].length === 1 ? "" : "s"}
                  </span>
                </div>
                <div className="space-y-3">
                  {byCategory[cat].map((q, i) => (
                    <QuestionCard
                      key={`${cat}-${i}`}
                      q={q}
                      protocols={protocols}
                      protocolByKey={protocolByKey}
                      agents={agents}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function groupByCategory(qs: DiscoveredQuestion[]): Record<string, DiscoveredQuestion[]> {
  const out: Record<string, DiscoveredQuestion[]> = {};
  for (const q of qs) {
    if (!out[q.category]) out[q.category] = [];
    out[q.category].push(q);
  }
  for (const k of Object.keys(out)) {
    out[k].sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]);
  }
  return out;
}

function rankedMatches(q: DiscoveredQuestion): ProtocolMatch[] {
  if (q.suggested_protocols && q.suggested_protocols.length > 0) {
    return q.suggested_protocols;
  }
  return [
    {
      key: q.suggested_protocol,
      name: q.suggested_protocol_name ?? null,
      score: 1.0,
      rationale: "",
    },
  ];
}

function defaultAgentsFor(p: Protocol | undefined): string[] {
  if (!p) return FALLBACK_AGENTS;
  if (p.recommended_agents && p.recommended_agents.length > 0) return p.recommended_agents;
  if (p.max_agents === 1) return ["ceo"];
  return FALLBACK_AGENTS;
}

function QuestionCard({
  q,
  protocols,
  protocolByKey,
  agents,
}: {
  q: DiscoveredQuestion;
  protocols: Protocol[];
  protocolByKey: Map<string, Protocol>;
  agents: Agent[];
}) {
  const matches = rankedMatches(q);
  const [selectedKey, setSelectedKey] = useState(matches[0]?.key ?? "");
  const selectedProtocol = protocolByKey.get(selectedKey);
  const [agentKeys, setAgentKeys] = useState<string[]>(() => {
    const suggested = (q.suggested_agents ?? []).map((a) => a.key);
    return suggested.length > 0 ? suggested : defaultAgentsFor(selectedProtocol);
  });
  const [userEdited, setUserEdited] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [creatingTeam, setCreatingTeam] = useState(false);
  const router = useRouter();

  function pickProtocol(key: string) {
    setSelectedKey(key);
    if (!userEdited) {
      const p = protocolByKey.get(key);
      setAgentKeys(defaultAgentsFor(p));
    }
  }

  function toggleAgent(key: string) {
    setUserEdited(true);
    setAgentKeys((curr) =>
      curr.includes(key) ? curr.filter((k) => k !== key) : [...curr, key],
    );
  }

  function onNewAgentCreated(key: string) {
    setUserEdited(true);
    setAgentKeys((curr) => (curr.includes(key) ? curr : [...curr, key]));
  }

  function startRun(withAgentKeys: string[] = agentKeys) {
    if (!selectedKey) {
      setRunError("Pick a protocol first.");
      return;
    }
    if (withAgentKeys.length === 0) {
      setRunError("Pick at least one agent.");
      return;
    }
    setRunError(null);
    const params = new URLSearchParams({
      question: q.text,
      protocol: selectedKey,
      agents: withAgentKeys.join(","),
    });
    router.push(`/run?${params.toString()}`);
  }

  async function createTeamAndRun() {
    const team = q.suggested_team;
    if (!team) return;
    setRunError(null);
    setCreatingTeam(true);
    try {
      const newAgentsByKey = new Map((q.suggested_new_agents ?? []).map((a) => [a.key, a]));
      for (const key of team.agent_keys) {
        const spec = newAgentsByKey.get(key);
        if (!spec) continue;
        const resp = await fetch("/api/proxy/agents", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(spec),
        });
        if (!resp.ok && resp.status !== 409) {
          const text = await resp.text().catch(() => "");
          throw new Error(`Creating ${key} failed: ${resp.status} ${text.slice(0, 200)}`);
        }
      }
      const teamResp = await fetch("/api/proxy/teams", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: team.name,
          description: team.description,
          agent_keys: team.agent_keys,
        }),
      });
      if (!teamResp.ok) {
        const text = await teamResp.text().catch(() => "");
        throw new Error(`Creating team failed: ${teamResp.status} ${text.slice(0, 200)}`);
      }
      startRun(team.agent_keys);
    } catch (e) {
      setRunError(e instanceof Error ? e.message : String(e));
    } finally {
      setCreatingTeam(false);
    }
  }

  // Group agents by category for the picker — same shape as RunForm.
  const agentsByCategory: Record<string, Agent[]> = {};
  for (const a of agents) {
    const cat = (a as Agent & { category?: string }).category ?? a.layer ?? "other";
    if (!agentsByCategory[cat]) agentsByCategory[cat] = [];
    agentsByCategory[cat].push(a);
  }
  const categoryOrder = [
    "executive",
    "c_suite",
    "cfo-team",
    "cto-team",
    "cmo-team",
    "cpo-team",
    "coo-team",
    "cro-team",
    "gtm-sales",
    "gtm-marketing",
    "direct_report",
    "functional",
    "other",
  ];
  const sortedCategories = Object.keys(agentsByCategory).sort(
    (a, b) =>
      (categoryOrder.indexOf(a) >= 0 ? categoryOrder.indexOf(a) : 999) -
      (categoryOrder.indexOf(b) >= 0 ? categoryOrder.indexOf(b) : 999),
  );

  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <p className="text-sm leading-relaxed text-foreground">{q.text}</p>
        <SeverityBadge severity={q.severity} />
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">{q.rationale}</p>

      <div className="space-y-1.5">
        <div className="ce-label text-[10px]">
          Top {matches.length} protocols ranked
        </div>
        <div className="space-y-1">
          {matches.map((m, idx) => {
            const proto = protocolByKey.get(m.key);
            const isSelected = m.key === selectedKey;
            return (
              <button
                key={m.key}
                type="button"
                onClick={() => pickProtocol(m.key)}
                className={`flex w-full items-start gap-3 rounded-lg border p-2.5 text-left text-xs transition-colors ${
                  isSelected
                    ? "border-primary/60 bg-primary/10"
                    : "border-border bg-background hover:border-primary/40"
                }`}
              >
                <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-secondary font-mono text-[10px] font-bold text-muted-foreground">
                  {idx + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline gap-2">
                    <span className="font-mono text-[11px] text-foreground">
                      {proto?.code ?? m.key}
                    </span>
                    <span className="truncate font-medium text-foreground">
                      {m.name ?? proto?.name ?? m.key}
                    </span>
                  </span>
                  {m.rationale ? (
                    <span className="mt-0.5 block text-[11px] leading-relaxed text-muted-foreground text-pretty">
                      {m.rationale}
                    </span>
                  ) : null}
                </span>
                <ScoreBar score={m.score} />
              </button>
            );
          })}
        </div>
      </div>

      <div className="rounded-lg border border-border bg-background p-3 space-y-2">
        <div className="flex items-center justify-between">
          <span className="ce-label text-[10px]">
            Agents ({agentKeys.length} selected)
          </span>
          {!userEdited && selectedProtocol?.recommended_agents?.length ? (
            <span className="inline-flex items-center gap-1 text-[10px] italic text-muted-foreground">
              <Sparkles size={10} /> using {selectedProtocol.protocol_id ?? selectedProtocol.key} default
            </span>
          ) : null}
        </div>
        <div className="max-h-32 space-y-2 overflow-y-auto pr-1">
          {sortedCategories.length === 0 ? (
            <p className="text-[11px] italic text-muted-foreground">
              No agents available — visit{" "}
              <Link href="/agents" className="underline">
                /agents
              </Link>
              .
            </p>
          ) : (
            sortedCategories.map((cat) => (
              <div key={cat}>
                <div className="ce-label mb-1 text-[10px]">{cat}</div>
                <div className="flex flex-wrap gap-1">
                  {agentsByCategory[cat].map((a) => (
                    <button
                      key={a.key}
                      type="button"
                      onClick={() => toggleAgent(a.key)}
                      className={`rounded border px-2 py-0.5 font-mono text-[10px] transition-colors ${
                        agentKeys.includes(a.key)
                          ? "border-primary/40 bg-primary/15 text-primary"
                          : "border-border bg-background text-foreground hover:border-primary/50"
                      }`}
                    >
                      {a.key}
                    </button>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {q.suggested_new_agents && q.suggested_new_agents.length > 0 ? (
        <div className="space-y-2">
          <div className="ce-label text-[10px]">Suggested new specialists</div>
          <div className="space-y-2">
            {q.suggested_new_agents.map((spec) => (
              <SuggestedAgentCard key={spec.key} spec={spec} onCreated={onNewAgentCreated} />
            ))}
          </div>
        </div>
      ) : null}

      {q.suggested_team ? (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 p-2.5">
          <Users size={13} className="shrink-0 text-primary" />
          <span className="text-xs font-medium text-foreground">{q.suggested_team.name}</span>
          <span className="text-[11px] text-muted-foreground">
            {q.suggested_team.agent_keys.join(", ")}
          </span>
          <button
            type="button"
            onClick={createTeamAndRun}
            disabled={creatingTeam}
            className="ml-auto rounded-md border border-primary/40 bg-background px-2.5 py-1 text-[11px] font-medium text-primary transition-colors hover:bg-primary/10 disabled:opacity-50"
          >
            {creatingTeam ? "Creating…" : "Create team & run"}
          </button>
        </div>
      ) : null}

      <div className="flex items-center justify-between gap-3">
        <span className="text-[11px] text-muted-foreground">
          <span className="ce-label mr-1.5">Will run:</span>
          <span className="font-mono text-foreground">{selectedKey}</span>
          <span className="ml-2">with</span>
          <span className="ml-1 font-mono text-foreground">
            {agentKeys.length > 0 ? agentKeys.join(", ") : "(no agents)"}
          </span>
        </span>
        <button
          type="button"
          onClick={() => startRun()}
          disabled={!selectedKey || agentKeys.length === 0}
          className="rounded-md border border-primary/40 bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-[rgb(var(--ce-indigo-500))] disabled:opacity-50"
        >
          Run this →
        </button>
      </div>
      {runError ? (
        <div className="text-[11px] text-destructive">{runError}</div>
      ) : null}
    </div>
  );
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, score)) * 100);
  return (
    <span
      className="inline-flex shrink-0 items-center gap-1 font-mono text-[10px] tabular-nums text-muted-foreground"
      title={`Fit score ${pct}/100`}
    >
      <span className="h-1 w-12 overflow-hidden rounded-full bg-secondary">
        <span
          className="block h-full rounded-full bg-primary"
          style={{ width: `${pct}%` }}
        />
      </span>
      {pct}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: Severity }) {
  const styles: Record<Severity, string> = {
    high: "bg-destructive/15 text-destructive border-destructive/30",
    medium:
      "bg-[rgb(var(--ce-yellow-500))]/15 text-[rgb(var(--ce-yellow-500))] border-[rgb(var(--ce-yellow-500))]/30",
    low: "bg-secondary text-muted-foreground border-border",
  };
  return (
    <span
      className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${styles[severity]}`}
    >
      {severity}
    </span>
  );
}
