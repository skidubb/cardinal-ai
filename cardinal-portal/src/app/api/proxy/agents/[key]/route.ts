// Proxy: /api/proxy/agents/[key] -> Railway /api/agents/{key}. GET + PUT.

import { auth } from "@clerk/nextjs/server";
import type { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

async function proxy(req: NextRequest, method: string, key: string) {
  const { getToken } = await auth();
  const token = await getToken({ template: "ce-railway" }).catch(() => null);
  const body = method === "GET" ? undefined : await req.text();

  const upstream = await fetch(`${API_BASE}/api/agents/${encodeURIComponent(key)}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
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
