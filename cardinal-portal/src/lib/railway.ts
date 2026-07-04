// Shared helper for proxying browser calls to the Railway FastAPI backend.
// Centralizes token acquisition (Clerk's default v2 session token — no
// template) and the SSE passthrough pattern used by streaming proxy routes.

import { auth } from "@clerk/nextjs/server";

export const RAILWAY_API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

export async function getRailwayToken(): Promise<string | null> {
  const { getToken } = await auth();
  return getToken().catch(() => null);
}

export async function proxyToRailway(
  path: string,
  init?: RequestInit & { sse?: boolean },
): Promise<Response> {
  const { sse, ...rest } = init ?? {};
  const token = await getRailwayToken();

  const headers = new Headers(rest.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (sse) headers.set("Accept", "text/event-stream");

  const upstream = await fetch(`${RAILWAY_API_BASE}${path}`, {
    ...rest,
    headers,
    cache: "no-store",
  });

  if (!sse) return upstream;

  if (!upstream.ok || !upstream.body) {
    const errBody = await upstream.text().catch(() => "");
    return new Response(errBody || `Upstream ${upstream.status}`, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("content-type") ?? "application/json" },
    });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
