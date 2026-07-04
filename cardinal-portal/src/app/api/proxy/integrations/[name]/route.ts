// Proxy: /api/proxy/integrations/[name] -> Railway /api/integrations/{name}. PUT + DELETE.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

async function proxy(req: NextRequest, method: string, name: string) {
  const body = method === "DELETE" ? undefined : await req.text();

  const upstream = await proxyToRailway(`/api/integrations/${encodeURIComponent(name)}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body,
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

export async function PUT(req: NextRequest, ctx: { params: Promise<{ name: string }> }) {
  const { name } = await ctx.params;
  return proxy(req, "PUT", name);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ name: string }> }) {
  const { name } = await ctx.params;
  return proxy(req, "DELETE", name);
}
