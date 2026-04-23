"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Info, Trash2 } from "lucide-react";
import type {
  AgentDetail,
  KnowledgeNamespace,
  ToolCatalog,
  ToolDirection,
} from "@/lib/api";
import { BrandIcon } from "@/components/integrations/BrandIcon";
import { DirectionPill } from "@/components/integrations/DirectionPill";

const MODEL_OPTIONS = [
  { value: "claude-opus-4-7", label: "Claude Opus 4.7 (reasoning)" },
  { value: "claude-sonnet-4-6", label: "Claude Sonnet 4.6 (balanced)" },
  { value: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5 (fast/cheap)" },
];

const CATEGORY_OPTIONS = [
  "executive",
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
  catalog: ToolCatalog;
  namespaces: KnowledgeNamespace[];
  initial?: Partial<AgentDetail>;
};

export function AgentForm({ mode, catalog, namespaces, initial }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [key, setKey] = useState(initial?.key ?? "");
  const [name, setName] = useState(initial?.name ?? "");
  const [category, setCategory] = useState(initial?.category ?? "other");
  const [model, setModel] = useState(initial?.model ?? MODEL_OPTIONS[0].value);
  const [temperature, setTemperature] = useState<number>(
    typeof initial?.temperature === "number" ? initial.temperature : 1.0,
  );
  const [systemPrompt, setSystemPrompt] = useState(initial?.system_prompt ?? "");
  const [personality, setPersonality] = useState(initial?.personality ?? "");
  const [tools, setTools] = useState<string[]>(initial?.tools ?? []);
  const [mcpServers, setMcpServers] = useState<string[]>(initial?.mcp_servers ?? []);
  const [kbNamespaces, setKbNamespaces] = useState<string[]>(initial?.kb_namespaces ?? []);
  const [constraintsStr, setConstraintsStr] = useState(
    initial?.constraints && initial.constraints.length > 0
      ? JSON.stringify(initial.constraints, null, 2)
      : "[]",
  );

  const isBuiltin = initial?.is_builtin === true;

  const toolsByDirection = useMemo(() => {
    const groups: Record<
      ToolDirection,
      Array<{ name: string; description: string; brand?: string }>
    > = {
      input: [],
      output: [],
      internal: [],
    };
    for (const [name, def] of Object.entries(catalog.tools)) {
      const d: ToolDirection = def.direction ?? "internal";
      groups[d].push({ name, description: def.description, brand: def.brand });
    }
    return groups;
  }, [catalog.tools]);

  const DIRECTION_LABELS: Record<ToolDirection, { title: string; subtitle: string }> = {
    input: { title: "Context Sources", subtitle: "What this agent can read" },
    output: { title: "Output Tools", subtitle: "What this agent can produce" },
    internal: { title: "Internal", subtitle: "Validation & QA" },
  };

  function toggle(list: string[], setter: (l: string[]) => void, v: string) {
    setter(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
  }

  async function save() {
    setError(null);
    setSaved(false);

    if (!key.trim() || !name.trim()) {
      setError("Key and name are required.");
      return;
    }
    if (mode === "create" && !/^[a-z0-9-]+$/.test(key)) {
      setError("Key must be lowercase alphanumeric with dashes (e.g. 'gtm-vp-data').");
      return;
    }

    let constraints: string[] = [];
    try {
      const parsed = JSON.parse(constraintsStr || "[]");
      if (!Array.isArray(parsed)) throw new Error("Constraints must be a JSON array");
      constraints = parsed.map(String);
    } catch (e) {
      setError(`Invalid constraints JSON: ${e instanceof Error ? e.message : String(e)}`);
      return;
    }

    const body = {
      key: key.trim(),
      name: name.trim(),
      category,
      model,
      temperature,
      system_prompt: systemPrompt,
      personality,
      tools,
      mcp_servers: mcpServers,
      kb_namespaces: kbNamespaces,
      constraints,
    };

    setBusy(true);
    try {
      const path = mode === "create" ? "/api/proxy/agents" : `/api/proxy/agents/${encodeURIComponent(key)}`;
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
      setSaved(true);
      if (mode === "create") {
        router.push(`/agents/${encodeURIComponent(body.key)}`);
      } else {
        router.refresh();
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function confirmDelete() {
    setError(null);
    setShowDeleteConfirm(false);
    setDeleting(true);
    try {
      const resp = await fetch(`/api/proxy/agents/${encodeURIComponent(key)}`, {
        method: "DELETE",
      });
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(`${resp.status}: ${text.slice(0, 300)}`);
      }
      router.push("/agents");
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-6">
      {isBuiltin ? (
        <div className="flex items-start gap-3 rounded-xl border border-[rgb(var(--ce-yellow-500))]/40 bg-[rgb(var(--ce-yellow-500))]/10 p-4 text-sm">
          <Info size={16} className="mt-0.5 shrink-0 text-[rgb(var(--ce-yellow-500))]" />
          <div>
            <div className="font-semibold text-[rgb(var(--ce-yellow-500))]">Built-in agent</div>
            <div className="mt-1 text-muted-foreground text-pretty">
              Changes you save become tenant-specific overrides of this agent. The original built-in prompt is preserved.
            </div>
          </div>
        </div>
      ) : null}

      {/* Identity */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <div>
          <span className="ce-eyebrow">Identity</span>
          <h2 className="mt-1 text-base font-bold tracking-tight">Basics</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Key" required hint="Unique slug (e.g. gtm-vp-data). Lowercase letters, numbers, dashes.">
            <input
              value={key}
              onChange={(e) => setKey(e.target.value.toLowerCase().replace(/\s+/g, "-"))}
              disabled={mode === "edit"}
              className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm text-foreground disabled:opacity-60 focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
              placeholder="gtm-vp-data"
            />
          </Field>
          <Field label="Display name" required>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
              placeholder="VP Data Operations"
            />
          </Field>
          <Field label="Category">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              {CATEGORY_OPTIONS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Model">
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              {MODEL_OPTIONS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field
          label={`Temperature · ${temperature.toFixed(1)}`}
          hint="0.0 = deterministic, 1.0 = default (uses extended thinking), 2.0 = maximum variance. Custom values disable extended thinking."
        >
          <input
            type="range"
            min={0}
            max={2}
            step={0.1}
            value={temperature}
            onChange={(e) => setTemperature(Number(e.target.value))}
            className="w-full accent-[rgb(var(--ce-indigo-500))]"
          />
          <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
            <span>0.0</span>
            <span>1.0 (default)</span>
            <span>2.0</span>
          </div>
        </Field>
      </section>

      {/* System prompt */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-3">
        <div>
          <span className="ce-eyebrow">Behavior</span>
          <h2 className="mt-1 text-base font-bold tracking-tight">System prompt</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            What this agent knows, how it thinks, and what frames it uses.
          </p>
        </div>
        <textarea
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
          rows={14}
          className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          placeholder="You are the VP of Data Operations at Cardinal Element. Your job is…"
        />
        <div className="text-xs text-muted-foreground">{systemPrompt.length} chars</div>
      </section>

      {/* Personality + constraints */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <div>
          <span className="ce-eyebrow">Voice</span>
          <h2 className="mt-1 text-base font-bold tracking-tight">Personality & constraints</h2>
        </div>
        <Field label="Personality" hint="Tone, archetype, speaking style.">
          <textarea
            value={personality}
            onChange={(e) => setPersonality(e.target.value)}
            rows={3}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            placeholder="Blunt, data-forward, skeptical of round numbers. Uses short declarative sentences."
          />
        </Field>
        <Field label="Constraints (JSON array)" hint="Hard rules this agent must never violate.">
          <textarea
            value={constraintsStr}
            onChange={(e) => setConstraintsStr(e.target.value)}
            rows={4}
            className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            placeholder='["Never fabricate metrics", "Flag assumptions explicitly"]'
          />
        </Field>
      </section>

      {/* Tools */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-3">
        <div>
          <span className="ce-eyebrow">Capabilities</span>
          <h2 className="mt-1 text-base font-bold tracking-tight">
            Tools{" "}
            <span className="text-sm font-normal text-muted-foreground">
              ({tools.length} of {Object.keys(catalog.tools).length} selected)
            </span>
          </h2>
        </div>
        <div className="space-y-5">
          {(["input", "output", "internal"] as ToolDirection[]).map((dir) => {
            const items = toolsByDirection[dir];
            if (!items.length) return null;
            const meta = DIRECTION_LABELS[dir];
            return (
              <div key={dir}>
                <div className="mb-2 flex items-center gap-2">
                  <DirectionPill direction={dir} />
                  <span className="text-sm font-semibold tracking-tight">{meta.title}</span>
                  <span className="text-xs text-muted-foreground">· {meta.subtitle}</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {items.map((t) => {
                    const active = tools.includes(t.name);
                    return (
                      <button
                        key={t.name}
                        type="button"
                        onClick={() => toggle(tools, setTools, t.name)}
                        title={t.description}
                        className={`inline-flex items-center gap-1.5 rounded border px-2 py-1 font-mono text-xs transition-colors ${
                          active
                            ? "border-primary/40 bg-primary/15 text-primary"
                            : "border-border bg-background text-foreground hover:border-primary/50"
                        }`}
                      >
                        <BrandIcon slug={t.brand} size={12} colored={active} />
                        {t.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* MCP servers */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-3">
        <div>
          <span className="ce-eyebrow">Capabilities</span>
          <h2 className="mt-1 text-base font-bold tracking-tight">
            MCP servers{" "}
            <span className="text-sm font-normal text-muted-foreground">
              ({mcpServers.length} selected)
            </span>
          </h2>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(catalog.mcp_servers).map(([key, def]) => {
            const active = mcpServers.includes(key);
            return (
              <button
                key={key}
                type="button"
                onClick={() => toggle(mcpServers, setMcpServers, key)}
                title={def.description}
                className={`inline-flex items-center gap-1.5 rounded border px-2 py-1 font-mono text-xs transition-colors ${
                  active
                    ? "border-primary/40 bg-primary/15 text-primary"
                    : "border-border bg-background text-foreground hover:border-primary/50"
                }`}
              >
                <BrandIcon slug={def.brand ?? key} size={12} colored={active} />
                {def.name}
              </button>
            );
          })}
        </div>
      </section>

      {/* KB namespaces */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-3">
        <div>
          <span className="ce-eyebrow">Memory</span>
          <h2 className="mt-1 text-base font-bold tracking-tight">
            Knowledge namespaces{" "}
            <span className="text-sm font-normal text-muted-foreground">
              ({kbNamespaces.length} selected)
            </span>
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Pinecone namespaces this agent can read from during runs.
          </p>
        </div>
        {namespaces.length === 0 ? (
          <div className="text-xs text-muted-foreground">No namespaces configured yet.</div>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {namespaces.map((ns) => {
              const active = kbNamespaces.includes(ns.name);
              return (
                <button
                  key={ns.name}
                  type="button"
                  onClick={() => toggle(kbNamespaces, setKbNamespaces, ns.name)}
                  title={`${ns.assigned_roles.length} roles use this`}
                  className={`rounded border px-2 py-1 font-mono text-xs transition-colors ${
                    active
                      ? "border-primary/40 bg-primary/15 text-primary"
                      : "border-border bg-background text-foreground hover:border-primary/50"
                  }`}
                >
                  {ns.name}
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* Action row */}
      <div className="flex items-center justify-between border-t border-border pt-5">
        <div className="text-xs">
          {error ? <span className="text-destructive">{error}</span> : null}
          {saved ? <span className="text-[rgb(var(--ce-green-500))]">Saved ✓</span> : null}
        </div>
        <div className="flex items-center gap-2">
          {mode === "edit" && !isBuiltin ? (
            <button
              type="button"
              onClick={() => setShowDeleteConfirm(true)}
              disabled={busy || deleting}
              className="inline-flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/20 disabled:opacity-40"
            >
              <Trash2 size={14} />
              {deleting ? "Deleting…" : "Delete agent"}
            </button>
          ) : null}
          <button
            type="button"
            onClick={save}
            disabled={busy || deleting || !key.trim() || !name.trim()}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-indigo)] transition-colors hover:bg-[rgb(var(--ce-indigo-500))] disabled:opacity-40 disabled:hover:bg-primary"
          >
            {busy ? "Saving…" : mode === "create" ? "Create agent" : "Save changes"}
            {!busy ? <ArrowRight size={14} /> : null}
          </button>
        </div>
      </div>

      {showDeleteConfirm ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-agent-title"
        >
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-lg">
            <h2 id="delete-agent-title" className="text-lg font-semibold">
              Delete agent &ldquo;{name || key}&rdquo;?
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              This permanently removes the agent. Teams and pipelines that reference{" "}
              <span className="font-mono text-xs">{key}</span> will lose this member. This cannot be undone.
            </p>
            <div className="mt-5 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(false)}
                className="rounded-md border border-border px-3 py-1.5 text-sm transition-colors hover:bg-secondary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDelete}
                className="rounded-md bg-destructive px-3 py-1.5 text-sm font-medium text-destructive-foreground transition-colors hover:opacity-90"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      ) : null}
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
