"use client";

import { useState } from "react";
import { X, Info } from "lucide-react";

type Tab = "mcp" | "api";

export function AddIntegrationModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [tab, setTab] = useState<Tab>("mcp");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [url, setUrl] = useState("");
  const [transport, setTransport] = useState("http");

  if (!open) return null;

  function reset() {
    setName("");
    setDescription("");
    setUrl("");
    setTransport("http");
    setError(null);
  }

  async function submit() {
    setError(null);
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }
    setBusy(true);
    try {
      const body =
        tab === "mcp"
          ? {
              name: name.trim(),
              description: description.trim(),
              url: url.trim(),
              transport,
            }
          : {
              // API endpoints use the same McpServerCreate shape on the backend
              // (Integration model is flexible). Backend marks as non-builtin.
              name: name.trim(),
              description: `[API] ${description.trim()}`,
              url: url.trim(),
              transport: "http-api",
            };

      const resp = await fetch("/api/proxy/integrations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(`${resp.status}: ${text.slice(0, 200)}`);
      }
      reset();
      onCreated();
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/20 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-border bg-background shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border p-5">
          <div>
            <span className="ce-eyebrow">Connect</span>
            <h2 className="mt-1 text-lg font-bold tracking-tight">Add integration</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          >
            <X size={16} />
          </button>
        </div>

        <div className="border-b border-border px-5">
          <div className="flex gap-1">
            <TabBtn active={tab === "mcp"} onClick={() => setTab("mcp")}>
              MCP server
            </TabBtn>
            <TabBtn active={tab === "api"} onClick={() => setTab("api")}>
              API endpoint
            </TabBtn>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {tab === "api" ? (
            <div className="flex items-start gap-2 rounded-md border border-[rgb(var(--ce-yellow-500))]/30 bg-[rgb(var(--ce-yellow-500))]/10 p-3 text-xs">
              <Info size={13} className="mt-0.5 shrink-0 text-[rgb(var(--ce-yellow-500))]" />
              <div className="text-muted-foreground">
                API endpoints are captured as metadata. Execution for custom HTTP tools is
                scoped for a future release — agents can&apos;t invoke them yet.
              </div>
            </div>
          ) : null}

          <Field label="Name" required>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={tab === "mcp" ? "e.g. clay" : "e.g. internal-pricing-api"}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            />
          </Field>

          <Field label="Description">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder={
                tab === "mcp"
                  ? "Clay MCP server — enrichment + prospect data"
                  : "Internal REST API for custom pricing logic"
              }
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            />
          </Field>

          <Field label="URL" hint={tab === "mcp" ? "MCP server endpoint (stdio commands or HTTP URL)" : "API base URL"}>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder={tab === "mcp" ? "https://clay.com/mcp" : "https://api.example.com"}
              className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            />
          </Field>

          {tab === "mcp" ? (
            <Field label="Transport">
              <select
                value={transport}
                onChange={(e) => setTransport(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
              >
                <option value="http">http (recommended for remote)</option>
                <option value="stdio">stdio (local command)</option>
                <option value="sse">sse (Server-Sent Events)</option>
              </select>
            </Field>
          ) : null}

          {error ? (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
              {error}
            </div>
          ) : null}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-border p-5">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-border px-4 py-2 text-sm transition-colors hover:bg-secondary"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={busy || !name.trim()}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-indigo)] transition-colors hover:bg-[rgb(var(--ce-indigo-500))] disabled:opacity-40 disabled:hover:bg-primary"
          >
            {busy ? "Adding…" : "Add integration"}
          </button>
        </div>
      </div>
    </div>
  );
}

function TabBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "relative px-4 py-3 text-sm font-medium transition-colors",
        active ? "text-primary" : "text-muted-foreground hover:text-foreground",
      ].join(" ")}
    >
      {children}
      {active ? (
        <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
      ) : null}
    </button>
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
