import { auth } from "@clerk/nextjs/server";
import { OrganizationSwitcher, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { fetchProtocols, fetchAgents } from "@/lib/api";
import RunForm from "./RunForm";

export default async function RunPage() {
  const { orgSlug } = await auth();

  const [protocolsResult, agentsResult] = await Promise.allSettled([
    fetchProtocols(),
    fetchAgents(),
  ]);

  const protocols = protocolsResult.status === "fulfilled" ? protocolsResult.value : [];
  const agents = agentsResult.status === "fulfilled" ? agentsResult.value : [];
  const setupError =
    protocolsResult.status === "rejected"
      ? String(protocolsResult.reason).slice(0, 300)
      : agentsResult.status === "rejected"
        ? String(agentsResult.reason).slice(0, 300)
        : null;

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <Link href="/dashboard" className="text-xs text-slate-500 hover:text-slate-300">
              &larr; Dashboard
            </Link>
            <h1 className="text-2xl font-semibold tracking-tight mt-1">Ask your C-Suite</h1>
            <p className="text-sm text-slate-400 mt-1">
              Tenant: <span className="font-mono text-slate-200">{orgSlug ?? "(no org)"}</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <OrganizationSwitcher hidePersonal />
            <UserButton />
          </div>
        </header>

        {setupError ? (
          <div className="rounded-lg border border-rose-700/40 bg-rose-950/20 p-4 text-sm text-rose-200">
            <strong>Cannot reach Railway.</strong>
            <div className="text-rose-300/70 text-xs mt-1 font-mono">{setupError}</div>
            <div className="text-rose-300/70 text-xs mt-2">
              Start the orchestration backend (uvicorn api.server:app --port 8000) and refresh.
            </div>
          </div>
        ) : protocols.length === 0 || agents.length === 0 ? (
          <div className="rounded-lg border border-amber-700/40 bg-amber-950/20 p-4 text-sm text-amber-200">
            Protocol or agent registry returned empty. Verify the orchestration backend is running.
          </div>
        ) : (
          <RunForm protocols={protocols} agents={agents} />
        )}
      </div>
    </main>
  );
}
