"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

const SCOPES = ["global", "client", "engagement", "protocol", "agent", "decision"] as const;

type Scope = typeof SCOPES[number];

export default function NewCorrectionForm({
  initialScope = "global",
  initialTarget = "",
  compact = false,
}: {
  initialScope?: Scope;
  initialTarget?: string;
  compact?: boolean;
}) {
  const router = useRouter();
  const [text, setText] = useState("");
  const [scope, setScope] = useState<Scope>(initialScope);
  const [targetId, setTargetId] = useState(initialTarget);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [justSaved, setJustSaved] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    if (scope !== "global" && !targetId.trim()) {
      setError(`Scope "${scope}" requires a target.`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const resp = await fetch("/api/proxy/corrections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text.trim(),
          scope,
          target_id: scope === "global" ? null : targetId.trim(),
          reason: reason.trim() || null,
        }),
      });
      if (!resp.ok) {
        throw new Error(`${resp.status}: ${(await resp.text()).slice(0, 200)}`);
      }
      setText("");
      setReason("");
      if (scope !== "global") setTargetId("");
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 2500);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className={`rounded-xl border border-amber-700/30 bg-amber-950/10 p-4 space-y-3 ${compact ? "" : ""}`}>
      {!compact && (
        <div>
          <div className="text-sm font-semibold">Add a correction</div>
          <div className="text-xs text-slate-400 mt-1">
            Once written, every future run that matches the scope loads this as institutional memory.
            Say it once — the system remembers forever.
          </div>
        </div>
      )}
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={'e.g. "Don\'t pitch Acme aggressive sales tactics. Their founder hates it."'}
        rows={2}
        className="w-full bg-slate-950/60 border border-slate-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-amber-500"
        disabled={busy}
      />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        <select
          value={scope}
          onChange={(e) => setScope(e.target.value as Scope)}
          disabled={busy}
          className="bg-slate-950/60 border border-slate-700 rounded-md px-2 py-1.5 text-xs"
        >
          {SCOPES.map((s) => (
            <option key={s} value={s}>Scope: {s}</option>
          ))}
        </select>
        <input
          type="text"
          value={targetId}
          onChange={(e) => setTargetId(e.target.value)}
          placeholder={scope === "global" ? "(no target needed)" : `target ${scope}`}
          disabled={busy || scope === "global"}
          className="bg-slate-950/60 border border-slate-700 rounded-md px-2 py-1.5 text-xs disabled:opacity-40"
        />
        <input
          type="text"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="optional: why"
          disabled={busy}
          className="bg-slate-950/60 border border-slate-700 rounded-md px-2 py-1.5 text-xs"
        />
      </div>
      <div className="flex items-center justify-between">
        <div className="text-xs">
          {error ? <span className="text-rose-300">{error}</span> : null}
          {justSaved ? <span className="text-green-300">Saved ✓</span> : null}
        </div>
        <button
          type="submit"
          disabled={busy || !text.trim()}
          className="rounded-md bg-amber-600 px-3 py-1.5 text-xs font-medium hover:bg-amber-500 transition disabled:opacity-40"
        >
          {busy ? "Saving..." : "Save correction"}
        </button>
      </div>
    </form>
  );
}
