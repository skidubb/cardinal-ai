// Proxy: /api/proxy/runs/[id] -> Railway /api/runs/{id}. GET only.
// Used by the portal to reconcile against authoritative run state when the
// SSE stream drops mid-run.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

export async function GET(_req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;

  const upstream = await proxyToRailway(`/api/runs/${id}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
