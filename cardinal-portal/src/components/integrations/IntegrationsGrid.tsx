"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Search } from "lucide-react";
import type {
  ConnectorStatus,
  Integration,
  MCPServerDef,
  ToolCatalog,
  ToolDef,
  ToolDirection,
} from "@/lib/api";
import { ToolCard } from "./ToolCard";
import { AddIntegrationModal } from "./AddIntegrationModal";

type Props = {
  catalog: ToolCatalog;
  integrations: Integration[];
  connectors: ConnectorStatus[];
};

export function IntegrationsGrid({ catalog, integrations, connectors }: Props) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [enabledOnly, setEnabledOnly] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  // Index integrations by name (the source of truth for enabled/configured state)
  const integrationByName = useMemo(() => {
    const m = new Map<string, Integration>();
    for (const i of integrations) m.set(i.name, i);
    return m;
  }, [integrations]);

  // Build four buckets
  const tools = Object.values(catalog.tools);
  const mcps = Object.entries(catalog.mcp_servers).map(([key, def]) => ({ key, ...def }));

  const input = tools.filter((t) => t.direction === "input");
  const output = tools.filter((t) => t.direction === "output");
  const internal = tools.filter((t) => t.direction === "internal");

  // Custom integrations (created via Add flow) live in the integrations table, not the catalogs
  const customAdds = integrations.filter(
    (i) => !i.is_builtin && i.type !== "tool_domain",
  );

  function matches(hay: string) {
    if (!q.trim()) return true;
    return hay.toLowerCase().includes(q.trim().toLowerCase());
  }

  function passesEnabled(integrationName?: string) {
    if (!enabledOnly) return true;
    if (!integrationName) return false;
    return integrationByName.get(integrationName)?.enabled === true;
  }

  function passesConnectorEnabled(enabled: boolean) {
    if (!enabledOnly) return true;
    return enabled;
  }

  async function toggleIntegration(name: string, next: boolean) {
    await fetch(`/api/proxy/integrations/${encodeURIComponent(name)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: next }),
    });
    router.refresh();
  }

  async function deleteIntegration(name: string) {
    if (!confirm(`Delete integration "${name}"?`)) return;
    await fetch(`/api/proxy/integrations/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
    router.refresh();
  }

  // Helper: find the integration for a tool via its domain (tool_domain entries)
  function integrationForDomain(domain: string) {
    return integrationByName.get(domain);
  }

  return (
    <div className="space-y-8">
      {/* Controls */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative max-w-md flex-1">
          <Search
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search integrations…"
            className="w-full rounded-md border border-input bg-background py-2 pl-9 pr-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          />
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={enabledOnly}
              onChange={(e) => setEnabledOnly(e.target.checked)}
              className="h-4 w-4 rounded border-input accent-[rgb(var(--ce-indigo-600))]"
            />
            Enabled only
          </label>
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-indigo)] transition-colors hover:bg-[rgb(var(--ce-indigo-500))]"
          >
            <Plus size={14} /> Add custom…
          </button>
        </div>
      </div>

      <AddIntegrationModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={() => router.refresh()}
      />

      {/* 1. Context Sources */}
      <Section
        eyebrow="01. Context Sources"
        title="What can my agents know?"
        subtitle="Input tools that read or fetch data — web, docs, filings, code, databases."
      >
        <Grid
          items={input.filter((t) => matches(t.name + t.description))}
          render={(t) => renderToolCard(t, integrationForDomain(t.domain), toggleIntegration)}
          skipIf={(t) => !passesEnabled(t.domain)}
        />
      </Section>

      {/* 2. Output Tools */}
      <Section
        eyebrow="02. Output Tools"
        title="What can my agents produce?"
        subtitle="Tools that write, generate, or export — deliverables, PDFs, images, calculations."
      >
        <Grid
          items={output.filter((t) => matches(t.name + t.description))}
          render={(t) => renderToolCard(t, integrationForDomain(t.domain), toggleIntegration)}
          skipIf={(t) => !passesEnabled(t.domain)}
        />
      </Section>

      {/* 3. Data Connectors */}
      <Section
        eyebrow="03. Data Connectors"
        title="What feeds institutional memory?"
        subtitle="Per-tenant ingestion into the knowledge graph — backfills Notion, Drive, HubSpot, Slack, etc."
      >
        {connectors.length === 0 ? (
          <EmptyNote>No connectors configured for this tenant yet.</EmptyNote>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {connectors
              .filter((c) => matches(c.name))
              .filter((c) => passesConnectorEnabled(c.enabled))
              .map((c) => (
                <ToolCard
                  key={c.name}
                  name={c.name}
                  title={c.name.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase())}
                  description={
                    c.notes ?? `${c.mode === "direct_api" ? "Direct API" : "MCP-driven"} · auth: ${c.auth}`
                  }
                  domain={c.mode}
                  brand={c.name.replace(/_/g, "")}
                  enabled={c.enabled}
                  onConfigure={() => alert(`Configure ${c.name} — key vault coming soon.`)}
                />
              ))}
          </div>
        )}
      </Section>

      {/* 4. MCP Servers */}
      <Section
        eyebrow="04. MCP Servers"
        title="External services agents can invoke"
        subtitle="Model Context Protocol servers — add your favorite platforms."
      >
        <Grid
          items={mcps.filter((m) => matches(m.name + m.description))}
          render={(mcp) => {
            const integration = integrationByName.get(mcp.key);
            return (
              <ToolCard
                key={mcp.key}
                name={mcp.key}
                title={mcp.name}
                description={mcp.description}
                domain={mcp.transport}
                brand={mcp.brand}
                integrationName={mcp.key}
                enabled={integration?.enabled ?? false}
                apiKeyConfigured={integration?.api_key_configured ?? true}
                onToggle={(n) => toggleIntegration(mcp.key, n)}
                onConfigure={() => alert(`Configure ${mcp.name} — key vault coming soon.`)}
              />
            );
          }}
          skipIf={(mcp) => !passesEnabled(mcp.key)}
        />

        {customAdds.length > 0 ? (
          <div className="mt-4 space-y-3">
            <div className="ce-label">Custom additions</div>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {customAdds
                .filter((i) => matches(i.name + i.description))
                .filter((i) => passesEnabled(i.name))
                .map((i) => (
                  <ToolCard
                    key={i.name}
                    name={i.name}
                    description={i.description || "(no description)"}
                    domain={i.type}
                    brand={undefined}
                    integrationName={i.name}
                    enabled={i.enabled}
                    apiKeyConfigured={i.api_key_configured}
                    deletable
                    onToggle={(n) => toggleIntegration(i.name, n)}
                    onDelete={() => deleteIntegration(i.name)}
                    onConfigure={() => alert(`Configure ${i.name} — key vault coming soon.`)}
                  />
                ))}
            </div>
          </div>
        ) : null}
      </Section>

      {/* 5. Internal (small section, collapsed feel) */}
      {internal.length > 0 ? (
        <Section
          eyebrow="Internal"
          title="System tools"
          subtitle="Internal validation and QA — not directly exposed to end users."
          dim
        >
          <Grid
            items={internal.filter((t) => matches(t.name + t.description))}
            render={(t) => renderToolCard(t, integrationForDomain(t.domain), toggleIntegration)}
            skipIf={() => enabledOnly}
          />
        </Section>
      ) : null}
    </div>
  );
}

function renderToolCard(
  t: ToolDef,
  integration: Integration | undefined,
  toggle: (name: string, next: boolean) => Promise<void>,
) {
  return (
    <ToolCard
      key={t.name}
      name={t.name}
      title={t.name.replace(/_/g, " ")}
      description={t.description}
      domain={t.domain}
      brand={t.brand}
      direction={t.direction}
      integrationName={integration ? integration.name : undefined}
      enabled={integration?.enabled ?? false}
      apiKeyConfigured={integration?.api_key_configured ?? true}
      onToggle={integration ? (n) => toggle(integration.name, n) : undefined}
      onConfigure={integration ? () => alert(`Configure ${integration.name} — key vault coming soon.`) : undefined}
    />
  );
}

function Section({
  eyebrow,
  title,
  subtitle,
  dim,
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  dim?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className={dim ? "opacity-80" : ""}>
      <div className="mb-4 border-b border-border pb-3">
        <span className="ce-eyebrow">{eyebrow}</span>
        <h2 className="mt-1 text-lg font-bold tracking-tight">{title}</h2>
        <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
      </div>
      {children}
    </section>
  );
}

function Grid<T>({
  items,
  render,
  skipIf,
}: {
  items: T[];
  render: (item: T) => React.ReactNode;
  skipIf?: (item: T) => boolean;
}) {
  const visible = skipIf ? items.filter((x) => !skipIf(x)) : items;
  if (visible.length === 0) return <EmptyNote>No items match.</EmptyNote>;
  return <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">{visible.map(render)}</div>;
}

function EmptyNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-card p-6 text-center text-xs text-muted-foreground">
      {children}
    </div>
  );
}
