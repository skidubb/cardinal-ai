// Proxy: /api/proxy/agents/[key] -> Railway /api/agents/{key}. GET + PUT.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

async function proxy(req: NextRequest, method: string, key: string) {
  const body = method === "GET" ? undefined : await req.text();

  const upstream = await proxyToRailway(`/api/agents/${encodeURIComponent(key)}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body,
  });

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ key: string }> }) {
  const { key } = await ctx.params;
  return proxy(req, "GET", key);
}

export async function PUT(req: NextRequest, ctx: { params: Promise<{ key: string }> }) {
  const { key } = await ctx.params;
  return proxy(req, "PUT", key);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ key: string }> }) {
  const { key } = await ctx.params;
  return proxy(req, "DELETE", key);
}
