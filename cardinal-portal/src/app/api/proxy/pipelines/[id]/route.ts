// Proxy: /api/proxy/pipelines/[id] -> Railway /api/pipelines/{id}. GET + DELETE.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

async function proxy(_req: NextRequest, method: string, id: string) {
  const upstream = await proxyToRailway(`/api/pipelines/${id}`, {
    method,
    headers: { "Content-Type": "application/json" },
  });

  if (method === "DELETE" && upstream.status === 204) {
    return new Response(null, { status: 204 });
  }

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  return proxy(req, "GET", id);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  return proxy(req, "DELETE", id);
}
