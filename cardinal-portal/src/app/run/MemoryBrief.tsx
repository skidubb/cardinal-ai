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

  if (!preview || !preview.available) {
    if (question.trim().length >= 10 && preview?.reason) {
      return (
        <div className="text-xs text-slate-500 italic">
          Memory brief unavailable: {preview.reason}
        </div>
      );
    }
    return null;
  }

  const s = preview.summary ?? { corrections: 0, decisions: 0, lessons: 0 };
  const total = s.corrections + s.decisions + s.lessons;
  if (total === 0) {
    return (
      <div className="text-xs text-slate-500">
        The graph doesn&apos;t yet have context on this question. Every run you ship enriches this.
      </div>
    );
  }

  return (
    <details className="rounded-lg border border-violet-700/30 bg-gradient-to-br from-violet-950/20 to-fuchsia-950/10 p-3" open>
      <summary className="cursor-pointer text-xs text-violet-200 flex items-center gap-2">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
        <strong>Memory brief:</strong> your C-Suite already knows&hellip;
        <span className="text-slate-400">
          {s.corrections} corrections &middot; {s.decisions} decisions &middot; {s.lessons} lessons
        </span>
        {loading ? <span className="text-slate-500 text-[10px] ml-2">(refreshing)</span> : null}
      </summary>
      <div className="mt-3 space-y-3 text-xs">
        {preview.detected?.clients?.length || preview.detected?.engagements?.length ? (
          <div className="text-slate-300">
            <span className="text-slate-500">Detected:</span>{" "}
            {preview.detected?.clients?.map((c) => (
              <span key={c} className="inline-block bg-slate-800 px-2 py-0.5 rounded mr-1 font-mono">{c}</span>
            ))}
            {preview.detected?.vertical ? (
              <span className="text-slate-500 ml-2">vertical: {preview.detected.vertical}</span>
            ) : null}
          </div>
        ) : null}

        {preview.applicable_corrections?.length ? (
          <div>
            <div className="text-slate-500 uppercase tracking-wider text-[10px] mb-1">
              Corrections that will apply
            </div>
            <ul className="space-y-1">
              {preview.applicable_corrections.slice(0, 4).map((c, i) => (
                <li key={i} className="text-slate-200">
                  <span className="text-amber-300 mr-2">[{c.scope}{c.target_id ? `:${c.target_id}` : ""}]</span>
                  {c.text}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {preview.recent_decisions?.length ? (
          <div>
            <div className="text-slate-500 uppercase tracking-wider text-[10px] mb-1">
              Prior related decisions
            </div>
            <ul className="space-y-1">
              {preview.recent_decisions.slice(0, 3).map((d, i) => (
                <li key={i} className="text-slate-300 truncate">
                  <span className="text-fuchsia-300 font-mono mr-2">{d.protocol_code}</span>
                  {d.summary}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {preview.lessons?.length ? (
          <div>
            <div className="text-slate-500 uppercase tracking-wider text-[10px] mb-1">
              Lessons
            </div>
            <ul className="space-y-1">
              {preview.lessons.slice(0, 3).map((l, i) => (
                <li key={i} className="text-slate-300">{l.statement}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </details>
  );
}
