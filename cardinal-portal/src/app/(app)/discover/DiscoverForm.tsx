"use client";

import Link from "next/link";
import { useRef, useState } from "react";

type Severity = "high" | "medium" | "low";

type DiscoveredQuestion = {
  text: string;
  category: string;
  severity: Severity;
  rationale: string;
  suggested_protocol: string;
  suggested_protocol_name?: string | null;
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

export function DiscoverForm() {
  const [files, setFiles] = useState<File[]>([]);
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DiscoverResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function onSubmit() {
    if (files.length === 0) {
      setError("Pick at least one file.");
      return;
    }
    setStatus("uploading");
    setError(null);
    setResult(null);

    const fd = new FormData();
    for (const f of files) fd.append("files", f);

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

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-primary/30 bg-primary/5 p-6">
        <label className="ce-label mb-2 block">Document</label>
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
            disabled={status === "uploading" || files.length === 0}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-[rgb(var(--ce-indigo-500))] disabled:opacity-40"
          >
            {status === "uploading" ? "Analyzing…" : "Discover questions"}
          </button>
        </div>

        {files.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {files.map((f, i) => (
              <span
                key={`${f.name}-${i}`}
                className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 font-mono text-[11px] text-primary"
                title={`${(f.size / 1024).toFixed(1)} KB`}
              >
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
          </div>
        ) : null}

        {status === "uploading" ? (
          <p className="mt-3 text-xs text-muted-foreground">
            Parsing and analyzing. A 50-page PDF typically takes 20–40 seconds.
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
                <div className="space-y-2">
                  {byCategory[cat].map((q, i) => (
                    <QuestionCard key={`${cat}-${i}`} q={q} />
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

function QuestionCard({ q }: { q: DiscoveredQuestion }) {
  const href = `/run?question=${encodeURIComponent(q.text)}&protocol=${encodeURIComponent(q.suggested_protocol)}`;
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-4">
        <p className="text-sm leading-relaxed text-foreground">{q.text}</p>
        <SeverityBadge severity={q.severity} />
      </div>
      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{q.rationale}</p>
      <div className="mt-3 flex items-center justify-between">
        <span className="text-[11px] text-muted-foreground">
          <span className="ce-label mr-1.5">Protocol:</span>
          <span className="font-mono text-foreground">{q.suggested_protocol}</span>
          {q.suggested_protocol_name ? (
            <span className="ml-2 text-muted-foreground">— {q.suggested_protocol_name}</span>
          ) : null}
        </span>
        <Link
          href={href}
          className="rounded-md border border-primary/40 px-3 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/10"
        >
          Run this →
        </Link>
      </div>
    </div>
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
