"use client";

import { useEffect, useState } from "react";

type Preview = {
  available: boolean;
  reason?: string;
  detected?: { clients: string[]; engagements: string[]; vertical: string | null };
  summary?: { corrections: number; decisions: number; lessons: number };
  applicable_corrections?: Array<{ text: string; scope: string; target_id?: string }>;
  recent_decisions?: Array<{ summary: string; protocol_code?: string; eval_score?: number }>;
  lessons?: Array<{ statement: string; confidence?: number }>;
};

export default function MemoryBrief({ question }: { question: string }) {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const text = question.trim();
    if (text.length < 10) {
      setPreview(null);
      return;
    }
    const handle = setTimeout(async () => {
      setLoading(true);
      try {
        const resp = await fetch("/api/proxy/context-preview", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: text }),
        });
        if (resp.ok) {
          setPreview(await resp.json());
        }
      } catch {
        // silent — preview is decorative
      } finally {
        setLoading(false);
      }
    }, 600);
    return () => clearTimeout(handle);
  }, [question]);

  // Memory brief is decorative. When the graph is unreachable / not
  // provisioned, render nothing rather than a noisy error — the /knowledge
  // and /knowledge/graph pages are the right surface for graph health.
  if (!preview || !preview.available) {
    return null;
  }

  const s = preview.summary ?? { corrections: 0, decisions: 0, lessons: 0 };
  const total = s.corrections + s.decisions + s.lessons;
  if (total === 0) {
    return (
      <div className="text-xs text-muted-foreground">
        The graph doesn&apos;t yet have context on this question. Every run you ship enriches this.
      </div>
    );
  }

  return (
    <details className="rounded-xl border border-[rgb(var(--ce-purple-500))]/30 bg-[rgb(var(--ce-purple-500))]/5 p-3" open>
      <summary className="cursor-pointer text-xs text-[rgb(var(--ce-purple-400))] flex items-center gap-2">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-[rgb(var(--ce-purple-400))] animate-pulse" />
        <strong>Memory brief:</strong> your C-Suite already knows&hellip;
        <span className="text-muted-foreground">
          {s.corrections} corrections &middot; {s.decisions} decisions &middot; {s.lessons} lessons
        </span>
        {loading ? <span className="text-muted-foreground text-[10px] ml-2">(refreshing)</span> : null}
      </summary>
      <div className="mt-3 space-y-3 text-xs">
        {preview.detected?.clients?.length || preview.detected?.engagements?.length ? (
          <div className="text-foreground">
            <span className="ce-label">Detected:</span>{" "}
            {preview.detected?.clients?.map((c) => (
              <span key={c} className="inline-block bg-secondary text-secondary-foreground px-2 py-0.5 rounded mr-1 font-mono">{c}</span>
            ))}
            {preview.detected?.vertical ? (
              <span className="text-muted-foreground ml-2">vertical: {preview.detected.vertical}</span>
            ) : null}
          </div>
        ) : null}

        {preview.applicable_corrections?.length ? (
          <div>
            <div className="ce-label mb-1">Corrections that will apply</div>
            <ul className="space-y-1">
              {preview.applicable_corrections.slice(0, 4).map((c, i) => (
                <li key={i} className="text-foreground">
                  <span className="text-[rgb(var(--ce-yellow-500))] mr-2">[{c.scope}{c.target_id ? `:${c.target_id}` : ""}]</span>
                  {c.text}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {preview.recent_decisions?.length ? (
          <div>
            <div className="ce-label mb-1">Prior related decisions</div>
            <ul className="space-y-1">
              {preview.recent_decisions.slice(0, 3).map((d, i) => (
                <li key={i} className="text-foreground truncate">
                  <span className="text-primary font-mono mr-2">{d.protocol_code}</span>
                  {d.summary}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {preview.lessons?.length ? (
          <div>
            <div className="ce-label mb-1">Lessons</div>
            <ul className="space-y-1">
              {preview.lessons.slice(0, 3).map((l, i) => (
                <li key={i} className="text-foreground">{l.statement}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </details>
  );
}
