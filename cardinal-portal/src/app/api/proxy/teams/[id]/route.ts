// Proxy: /api/proxy/teams/[id] -> Railway /api/teams/{id}. GET/PUT/DELETE.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

async function proxy(req: NextRequest, method: string, id: string) {
  const body = method === "GET" || method === "DELETE" ? undefined : await req.text();

  const upstream = await proxyToRailway(`/api/teams/${id}`, {
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

export async function GET(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  return proxy(req, "GET", id);
}

export async function PUT(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  return proxy(req, "PUT", id);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  return proxy(req, "DELETE", id);
}
