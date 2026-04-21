"use client";

import { useState } from "react";

// Client-safe types mirroring the server's lib/api.ts. We can't import from
// "@/lib/api" here because that module uses @clerk/nextjs/server which only
// works in Server Components / route handlers.
type ConnectorMode = "direct_api" | "mcp_driven";
export type ConnectorStatus = {
  name: string;
  mode: ConnectorMode;
  enabled: boolean;
  auth: string;
  notes?: string | null;
};
type BackfillResponse = {
  mode: "direct_api" | "mcp_runbook";
  connector: string;
  tenant_slug: string;
  status: "queued" | "runbook_only";
  message: string;
  runbook?: string | null;
};

export default function BackfillControls({ connector }: { connector: ConnectorStatus }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<BackfillResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(dry: boolean) {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const resp = await fetch("/api/proxy/connectors/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ connector: connector.name, dry_run: dry }),
      });
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}: ${(await resp.text()).slice(0, 200)}`);
      }
      setResult((await resp.json()) as BackfillResponse);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <button
          onClick={() => run(true)}
          disabled={busy}
          className="text-xs rounded border border-slate-700 px-2 py-1 hover:bg-slate-800 transition disabled:opacity-50"
        >
          Dry-run
        </button>
        <button
          onClick={() => run(false)}
          disabled={busy}
          className="text-xs rounded border border-fuchsia-700/40 bg-fuchsia-950/20 text-fuchsia-200 px-2 py-1 hover:bg-fuchsia-950/40 transition disabled:opacity-50"
        >
          {busy ? "Starting..." : "Start backfill"}
        </button>
      </div>

      {error ? (
        <div className="text-xs text-rose-300 font-mono break-all">{error}</div>
      ) : null}

      {result ? (
        <div className="rounded bg-slate-950/60 border border-slate-800 p-2 text-xs">
          <div className={result.status === "queued" ? "text-green-300" : "text-amber-300"}>
            {result.message}
          </div>
          {result.runbook ? (
            <pre className="mt-2 text-[10px] text-slate-400 whitespace-pre-wrap font-mono leading-relaxed">
              {result.runbook}
            </pre>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
