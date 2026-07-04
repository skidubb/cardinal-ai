import { auth } from "@clerk/nextjs/server";
import {
  fetchProtocols,
  fetchAgents,
  fetchPipelines,
  fetchTeams,
  fetchModels,
  type ModelsResponse,
} from "@/lib/api";
import RunForm from "./RunForm";

export default async function RunPage({
  searchParams,
}: {
  searchParams: Promise<{ question?: string; protocol?: string; agents?: string }>;
}) {
  const { orgSlug, has } = await auth();
  const hasPremium = has({ feature: "premium_protocols" });
  const sp = await searchParams;
  const initialQuestion = typeof sp.question === "string" ? sp.question : "";
  const initialProtocol = typeof sp.protocol === "string" ? sp.protocol : "";
  const initialAgents =
    typeof sp.agents === "string" && sp.agents.trim().length > 0
      ? sp.agents.split(",").map((s) => s.trim()).filter(Boolean)
      : [];

  const [protocolsR, agentsR, pipelinesR, teamsR, modelsR] = await Promise.allSettled([
    fetchProtocols(),
    fetchAgents(),
    fetchPipelines(),
    fetchTeams(),
    fetchModels(),
  ]);

  const protocols = protocolsR.status === "fulfilled" ? protocolsR.value : [];
  const agents = agentsR.status === "fulfilled" ? agentsR.value : [];
  const pipelines = pipelinesR.status === "fulfilled" ? pipelinesR.value : [];
  const teams = teamsR.status === "fulfilled" ? teamsR.value : [];
  const models: ModelsResponse | null = modelsR.status === "fulfilled" ? modelsR.value : null;

  const setupError =
    protocolsR.status === "rejected"
      ? String(protocolsR.reason).slice(0, 300)
      : agentsR.status === "rejected"
        ? String(agentsR.reason).slice(0, 300)
        : null;

  return (
    <div className="mx-auto max-w-5xl px-8 py-10 space-y-6">
      <header>
        <span className="ce-eyebrow">Work</span>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Ask</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Smart routing, a single protocol, or a saved pipeline.
          {orgSlug ? <span className="ml-2 font-mono">· {orgSlug}</span> : null}
        </p>
      </header>

      {setupError ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Cannot reach Railway.</strong>
          <div className="text-destructive/70 text-xs mt-1 font-mono">{setupError}</div>
          <div className="text-destructive/70 text-xs mt-2">
            Start the orchestration backend (uvicorn api.server:app --port 8000) and refresh.
          </div>
        </div>
      ) : protocols.length === 0 || agents.length === 0 ? (
        <div className="rounded-xl border border-[rgb(var(--ce-yellow-500))]/40 bg-[rgb(var(--ce-yellow-500))]/10 p-4 text-sm text-[rgb(var(--ce-yellow-500))]">
          Protocol or agent registry returned empty. Verify the orchestration backend is running.
        </div>
      ) : (
        <RunForm
          protocols={protocols}
          agents={agents}
          pipelines={pipelines}
          teams={teams}
          models={models}
          initialQuestion={initialQuestion}
          initialProtocol={initialProtocol}
          initialAgents={initialAgents}
          hasPremium={hasPremium}
        />
      )}
    </div>
  );
}
