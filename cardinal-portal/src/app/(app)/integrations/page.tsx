import {
  fetchToolCatalog,
  fetchIntegrations,
  fetchConnectorsStatus,
} from "@/lib/api";
import { IntegrationsGrid } from "@/components/integrations/IntegrationsGrid";

export default async function IntegrationsPage() {
  const [catalogR, integrationsR, connectorsR] = await Promise.allSettled([
    fetchToolCatalog(),
    fetchIntegrations(),
    fetchConnectorsStatus(),
  ]);

  const catalog =
    catalogR.status === "fulfilled"
      ? catalogR.value
      : { tools: {}, mcp_servers: {} };
  const integrations =
    integrationsR.status === "fulfilled" ? integrationsR.value : [];
  const connectors =
    connectorsR.status === "fulfilled" ? connectorsR.value.connectors : [];

  const toolCount = Object.keys(catalog.tools).length;
  const mcpCount = Object.keys(catalog.mcp_servers).length;
  const customCount = integrations.filter(
    (i) => !i.is_builtin && i.type !== "tool_domain",
  ).length;
  const enabledCount = integrations.filter((i) => i.enabled).length;

  return (
    <div className="mx-auto max-w-6xl px-8 py-10 space-y-8">
      <header>
        <span className="ce-eyebrow">Connect</span>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Integrations</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground text-pretty">
          Tools, connectors, and MCP servers your agents can use. Add your favorite platforms —
          input tools feed context, output tools produce artifacts.
        </p>
        <div className="mt-3 flex flex-wrap gap-4 text-xs text-muted-foreground">
          <Stat label="Built-in tools" value={toolCount} />
          <Stat label="MCP servers" value={mcpCount} />
          <Stat label="Connectors" value={connectors.length} />
          <Stat label="Custom additions" value={customCount} />
          <Stat label="Enabled" value={enabledCount} />
        </div>
      </header>

      <IntegrationsGrid
        catalog={catalog}
        integrations={integrations}
        connectors={connectors}
      />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="font-mono text-sm font-semibold tabular-nums text-foreground">{value}</span>
      <span>{label}</span>
    </span>
  );
}
