// Proxy: /api/proxy/runs/[id] -> Railway /api/runs/{id}. GET only.
// Used by the portal to reconcile against authoritative run state when the
// SSE stream drops mid-run.

import { auth } from "@clerk/nextjs/server";
import type { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

export async function GET(_req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const { getToken } = await auth();
  const token = await getToken({ template: "ce-railway" }).catch(() => null);

  const upstream = await fetch(`${API_BASE}/api/runs/${id}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
