// Proxy: POST /api/proxy/router/run -> Railway POST /api/router/run.
// SSE stream, first event is `router_decision`, then normal protocol events.

import { auth } from "@clerk/nextjs/server";
import type { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const { getToken } = await auth();
  const token = await getToken({ template: "ce-railway" }).catch(() => null);
  const body = await req.text();

  const upstream = await fetch(`${API_BASE}/api/router/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body,
    // @ts-expect-error duplex is valid
    duplex: "half",
  });

  if (!upstream.ok || !upstream.body) {
    const errBody = await upstream.text().catch(() => "");
    return new Response(errBody || `Upstream ${upstream.status}`, { status: upstream.status });
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
