// Proxy: /api/proxy/integrations/[name] -> Railway /api/integrations/{name}. PUT + DELETE.

import { auth } from "@clerk/nextjs/server";
import type { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

async function proxy(req: NextRequest, method: string, name: string) {
  const { getToken } = await auth();
  const token = await getToken({ template: "ce-railway" }).catch(() => null);
  const body = method === "DELETE" ? undefined : await req.text();

  const upstream = await fetch(
    `${API_BASE}/api/integrations/${encodeURIComponent(name)}`,
    {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body,
    },
  );

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
